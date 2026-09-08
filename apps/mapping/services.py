"""
Business Services for Data Mapping & Standard Data Model Ingestion.
Coordinates field discovery, mapping profile lifecycle, safe transformation preview,
and transactional canonical domain persistence.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple, Sequence
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.audit.services import log_action
from apps.workspaces.models import Workspace
from apps.integration.models import DataSource, ImportJob, RawImportRecord
from apps.mapping.models import (
    MappingProfile,
    MappingRule,
    RuleType,
    AIConfirmationStatus,
    ValidationStatus,
)
from apps.mapping.canonical import get_canonical_model
from apps.mapping.engine.transformer import transform_single_record
from apps.mapping.validators import validate_canonical_record

# Domain Model Imports
from apps.retail.models import Customer, Product, Category, Branch, Order, OrderItem, OrderStatus, PaymentMethod, CustomerSegment
from apps.service_ops.models import (
    Employee,
    Service,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    LaborEntry,
    SLA,
)


def discover_source_fields(
    import_job: Optional[ImportJob] = None,
    data_source: Optional[DataSource] = None,
    sample_limit: int = 50,
) -> Dict[str, Any]:
    """
    Discovers columns, data samples, inferred datatypes, and null ratios from raw staged records.
    Powers the interactive Mapping Studio UI.
    """
    raw_records_qs = None
    if import_job:
        raw_records_qs = import_job.raw_records.all()
    elif data_source:
        last_job = data_source.import_jobs.order_by("-created_at").first()
        if last_job:
            raw_records_qs = last_job.raw_records.all()

    if not raw_records_qs or not raw_records_qs.exists():
        return {
            "columns": [],
            "sample_records": [],
            "column_stats": {},
            "total_staged_rows": 0,
        }

    sample_records = [r.raw_data for r in raw_records_qs[:sample_limit]]
    total_staged = raw_records_qs.count()

    # Aggregate union of all column names
    col_set = []
    for rec in sample_records:
        for k in rec.keys():
            if k not in col_set:
                col_set.append(k)

    column_stats: Dict[str, Dict[str, Any]] = {}
    for col in col_set:
        values = [r.get(col) for r in sample_records]
        non_null_vals = [v for v in values if v is not None and str(v).strip() != ""]
        null_count = len(values) - len(non_null_vals)
        null_ratio = round(null_count / max(1, len(values)), 2)

        # Inferred type
        inferred = "STRING"
        if non_null_vals:
            # Check integer
            if all(isinstance(v, int) or (isinstance(v, str) and v.isdigit()) for v in non_null_vals[:10]):
                inferred = "INTEGER"
            # Check decimal
            elif all(any(c.isdigit() for c in str(v)) and any(s in str(v) for s in ("đ", "VND", "$", ".", ",")) for v in non_null_vals[:10]):
                inferred = "DECIMAL"
            # Check boolean
            elif all(str(v).lower() in ("true", "false", "1", "0", "có", "không", "yes", "no") for v in non_null_vals[:10]):
                inferred = "BOOLEAN"
            # Check date
            elif all(any(sep in str(v) for sep in ("/", "-", "T")) for v in non_null_vals[:10]):
                inferred = "DATE"

        column_stats[col] = {
            "name": col,
            "inferred_type": inferred,
            "null_ratio": null_ratio,
            "sample_values": non_null_vals[:5],
        }

    return {
        "columns": col_set,
        "sample_records": sample_records[:5],
        "column_stats": column_stats,
        "total_staged_rows": total_staged,
    }


def create_mapping_profile(
    workspace: Workspace,
    user,
    name: str,
    target_entity: str,
    data_source: Optional[DataSource] = None,
    description: str = "",
) -> MappingProfile:
    """Creates a new workspace-scoped MappingProfile."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Mapping profile name cannot be empty.")

    if MappingProfile.objects.for_workspace(workspace).filter(name__iexact=clean_name).exists():
        raise ValueError(f"Mapping profile with name '{clean_name}' already exists in this workspace.")

    profile = MappingProfile.objects.create(
        workspace=workspace,
        name=clean_name,
        target_entity=target_entity,
        data_source=data_source,
        description=description.strip(),
        created_by=user,
    )

    log_action(
        workspace=workspace,
        actor_user=user,
        action="MAPPING_PROFILE_CREATED",
        entity_type="MappingProfile",
        entity_id=str(profile.id),
        changes={"name": clean_name, "target_entity": target_entity},
    )
    return profile


def add_mapping_rule(
    profile: MappingProfile,
    user,
    source_field: str,
    target_field: str,
    rule_type: str = RuleType.FIELD_MAPPING,
    transformation_config: Optional[Dict[str, Any]] = None,
    confidence_score: float = 1.0,
    ai_status: str = AIConfirmationStatus.ACCEPTED,
    order: int = 0,
) -> MappingRule:
    """Adds a mapping rule to an existing profile."""
    rule = MappingRule.objects.create(
        workspace=profile.workspace,
        profile=profile,
        source_field=source_field.strip(),
        target_field=target_field.strip(),
        rule_type=rule_type,
        transformation_config=transformation_config or {},
        confidence_score=confidence_score,
        ai_status=ai_status,
        order=order,
        created_by=user,
    )

    log_action(
        workspace=profile.workspace,
        actor_user=user,
        action="MAPPING_RULE_ADDED",
        entity_type="MappingRule",
        entity_id=str(rule.id),
        changes={
            "profile_id": str(profile.id),
            "source_field": rule.source_field,
            "target_field": rule.target_field,
            "rule_type": rule_type,
            "ai_status": ai_status,
        },
    )
    return rule


def accept_ai_mapping_rule(rule: MappingRule, user) -> MappingRule:
    """Human-in-the-loop: Accepts an AI-recommended mapping rule."""
    rule.ai_status = AIConfirmationStatus.ACCEPTED
    rule.is_active = True
    rule.save(update_fields=["ai_status", "is_active", "updated_at"])

    log_action(
        workspace=rule.workspace,
        actor_user=user,
        action="MAPPING_RULE_APPROVED",
        entity_type="MappingRule",
        entity_id=str(rule.id),
        changes={"ai_status": "ACCEPTED", "target_field": rule.target_field},
    )
    return rule


def reject_ai_mapping_rule(rule: MappingRule, user) -> MappingRule:
    """Human-in-the-loop: Rejects an AI-recommended mapping rule."""
    rule.ai_status = AIConfirmationStatus.REJECTED
    rule.is_active = False
    rule.save(update_fields=["ai_status", "is_active", "updated_at"])

    log_action(
        workspace=rule.workspace,
        actor_user=user,
        action="MAPPING_RULE_REJECTED",
        entity_type="MappingRule",
        entity_id=str(rule.id),
        changes={"ai_status": "REJECTED", "target_field": rule.target_field},
    )
    return rule


def generate_mapping_preview(
    workspace: Workspace,
    profile: MappingProfile,
    import_job: Optional[ImportJob] = None,
    raw_records_data: Optional[List[Dict[str, Any]]] = None,
    sample_count: int = 5,
) -> Dict[str, Any]:
    """
    Read-only simulation preview. Transforms records and validates them without writing to the database.
    """
    if raw_records_data is not None:
        sample_raw = raw_records_data[:sample_count]
    elif import_job:
        sample_raw = [r.raw_data for r in import_job.raw_records.all()[:sample_count]]
    else:
        # Check if profile has an associated data source
        ds = profile.data_source
        if ds and ds.import_jobs.exists():
            last_job = ds.import_jobs.order_by("-created_at").first()
            sample_raw = [r.raw_data for r in last_job.raw_records.all()[:sample_count]]
        else:
            sample_raw = []

    active_rules = list(profile.rules.filter(is_active=True))

    transformed_samples = []
    all_errors = []
    valid_count = 0
    invalid_count = 0

    for idx, raw in enumerate(sample_raw, start=1):
        canonical_dict, transform_errs = transform_single_record(
            raw_data=raw,
            rules=active_rules,
            target_entity=profile.target_entity,
        )

        validation_errs = validate_canonical_record(
            canonical_data=canonical_dict,
            target_entity=profile.target_entity,
            workspace=workspace,
            check_foreign_keys=True,
        )

        row_errors = transform_errs + validation_errs
        is_row_valid = len(row_errors) == 0

        if is_row_valid:
            valid_count += 1
        else:
            invalid_count += 1
            all_errors.extend([{"row": idx, **e} for e in row_errors])

        transformed_samples.append({
            "row_number": idx,
            "raw_input": raw,
            "canonical_output": canonical_dict,
            "is_valid": is_row_valid,
            "errors": row_errors,
        })

    return {
        "profile_id": str(profile.id),
        "profile_name": profile.name,
        "target_entity": profile.target_entity,
        "sample_count": len(sample_raw),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_valid": invalid_count == 0,
        "transformed_samples": transformed_samples,
        "errors": all_errors,
    }


def apply_mapping_to_domain(
    workspace: Workspace,
    user,
    profile: MappingProfile,
    import_job: ImportJob,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Executes the canonical domain import:
    1. Loads raw staged records from ImportJob.
    2. Transforms each record using active, accepted MappingRules.
    3. Validates canonical records against the Standard Data Model.
    4. Atomically persists records into Retail or Service domain tables.
    5. Writes an immutable AuditLog entry.
    """
    raw_records_qs = import_job.raw_records.all().order_by("row_number")
    total_records = raw_records_qs.count()

    if total_records == 0:
        return {
            "status": "FAILED",
            "message": "Import job contains zero raw staged records.",
            "inserted_count": 0,
            "failed_count": 0,
            "errors": [],
        }

    active_rules = list(profile.rules.filter(is_active=True))
    if not active_rules:
        return {
            "status": "FAILED",
            "message": "Mapping profile contains no active rules.",
            "inserted_count": 0,
            "failed_count": 0,
            "errors": [],
        }

    target_entity = profile.target_entity
    valid_payloads = []
    import_errors = []

    # Phase 1: Transform and Validate in memory
    for raw_rec in raw_records_qs:
        row_num = raw_rec.row_number
        canonical_dict, transform_errs = transform_single_record(
            raw_data=raw_rec.raw_data,
            rules=active_rules,
            target_entity=target_entity,
        )

        validation_errs = validate_canonical_record(
            canonical_data=canonical_dict,
            target_entity=target_entity,
            workspace=workspace,
            check_foreign_keys=True,
        )

        row_errors = transform_errs + validation_errs
        if row_errors:
            import_errors.append({"row": row_num, "errors": row_errors, "raw": raw_rec.raw_data})
            if strict:
                return {
                    "status": "FAILED",
                    "message": f"Strict mode enabled: Row {row_num} failed validation.",
                    "inserted_count": 0,
                    "failed_count": len(import_errors),
                    "errors": import_errors,
                }
        else:
            valid_payloads.append((row_num, canonical_dict))

    # Phase 2: Transactional Persistence into Domain Models
    inserted_count = 0
    persisted_ids = []

    try:
        with transaction.atomic():
            now = timezone.now()

            if target_entity == "Customer":
                for row_num, data in valid_payloads:
                    loc = None
                    if data.get("latitude") is not None and data.get("longitude") is not None:
                        loc = Point(float(data["longitude"]), float(data["latitude"]), srid=4326)

                    cust, created = Customer.objects.update_or_create(
                        workspace=workspace,
                        code=str(data["customer_id"]).strip(),
                        defaults={
                            "name": str(data["name"]).strip(),
                            "phone": data.get("phone", "") or "",
                            "email": data.get("email") or None,
                            "address": data.get("address", "") or "",
                            "location": loc,
                            "customer_segment": data.get("segment", CustomerSegment.STANDARD),
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(cust.id)

            elif target_entity == "Product":
                # Find default or specified category
                default_category = Category.objects.for_workspace(workspace).first()
                for row_num, data in valid_payloads:
                    cat = default_category
                    cat_code = data.get("category_code")
                    if cat_code:
                        found_cat = Category.objects.for_workspace(workspace).filter(code=cat_code).first()
                        if found_cat:
                            cat = found_cat

                    prod, created = Product.objects.update_or_create(
                        workspace=workspace,
                        sku=str(data["sku"]).strip(),
                        defaults={
                            "name": str(data["name"]).strip(),
                            "category": cat,
                            "unit": data.get("unit", "cái"),
                            "unit_price": Decimal(str(data["unit_price"])),
                            "cost_price": Decimal(str(data.get("cost_price", "0.00"))),
                            "is_active": bool(data.get("is_active", True)),
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(prod.id)

            elif target_entity == "Branch":
                for row_num, data in valid_payloads:
                    loc = None
                    if data.get("latitude") is not None and data.get("longitude") is not None:
                        loc = Point(float(data["longitude"]), float(data["latitude"]), srid=4326)

                    branch, created = Branch.objects.update_or_create(
                        workspace=workspace,
                        code=str(data["branch_code"]).strip(),
                        defaults={
                            "name": str(data["name"]).strip(),
                            "region": data.get("region", "") or "",
                            "address": data.get("address", "") or "",
                            "phone": data.get("phone", "") or "",
                            "location": loc,
                            "is_active": bool(data.get("is_active", True)),
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(branch.id)

            elif target_entity == "Order":
                for row_num, data in valid_payloads:
                    cust = Customer.objects.for_workspace(workspace).filter(code=data["customer_id"]).first()
                    branch = None
                    if data.get("branch_code"):
                        branch = Branch.objects.for_workspace(workspace).filter(code=data["branch_code"]).first()

                    order_ts = data.get("order_timestamp") or timezone.now()
                    amt = Decimal(str(data.get("total_amount") if data.get("total_amount") is not None else data.get("revenue", "0.00")))
                    order, created = Order.objects.update_or_create(
                        workspace=workspace,
                        order_number=str(data["order_number"]).strip(),
                        defaults={
                            "customer": cust,
                            "branch": branch,
                            "order_date": data["order_date"],
                            "order_timestamp": order_ts,
                            "total_amount": amt,
                            "subtotal_amount": amt,
                            "discount_amount": Decimal(str(data.get("discount_amount", "0.00"))),
                            "tax_amount": Decimal(str(data.get("tax_amount", "0.00"))),
                            "status": data.get("status", OrderStatus.COMPLETED),
                            "payment_method": data.get("payment_method", PaymentMethod.CASH),
                            "notes": data.get("notes", "") or "",
                            "created_by": user,
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(order.id)

            elif target_entity == "OrderItem":
                for row_num, data in valid_payloads:
                    order = Order.objects.for_workspace(workspace).filter(order_number=data["order_number"]).first()
                    product = Product.objects.for_workspace(workspace).filter(sku=data["sku"]).first()
                    if order and product:
                        item = OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=int(data["quantity"]),
                            unit_price=Decimal(str(data["unit_price"])),
                            discount=Decimal(str(data.get("discount", "0.00"))),
                        )
                        inserted_count += 1
                        persisted_ids.append(item.id)

            elif target_entity == "Service":
                for row_num, data in valid_payloads:
                    svc, created = Service.objects.update_or_create(
                        workspace=workspace,
                        code=str(data["code"]).strip(),
                        defaults={
                            "name": str(data["name"]).strip(),
                            "category": data.get("category", ServiceCategory.INSTALLATION),
                            "standard_duration_minutes": int(data.get("standard_duration_minutes", 60)),
                            "base_fee": Decimal(str(data.get("base_fee", "0.00"))),
                            "is_active": bool(data.get("is_active", True)),
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(svc.id)

            elif target_entity == "Employee":
                for row_num, data in valid_payloads:
                    loc = None
                    if data.get("latitude") is not None and data.get("longitude") is not None:
                        loc = Point(float(data["longitude"]), float(data["latitude"]), srid=4326)

                    emp, created = Employee.objects.update_or_create(
                        workspace=workspace,
                        code=str(data["employee_code"]).strip(),
                        defaults={
                            "full_name": str(data["full_name"]).strip(),
                            "phone": data.get("phone", "") or "",
                            "email": data.get("email") or None,
                            "skills": data.get("skills", []),
                            "hourly_labor_rate": Decimal(str(data.get("hourly_labor_rate", "150000.00"))),
                            "current_location": loc,
                            "is_available": bool(data.get("is_available", True)),
                            "is_active": True,
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(emp.id)

            elif target_entity == "ServiceRequest":
                default_sla = SLA.objects.filter(workspace=workspace).first()
                if not default_sla:
                    default_sla, _ = SLA.objects.get_or_create(
                        workspace=workspace,
                        priority=SLAPriority.MEDIUM,
                        defaults={"name": "Standard Medium SLA", "response_time_hours": 4, "resolution_time_hours": 24},
                    )
                for row_num, data in valid_payloads:
                    cust = Customer.objects.for_workspace(workspace).filter(code=data["customer_id"]).first()
                    svc = Service.objects.for_workspace(workspace).filter(code=data["service_code"]).first()
                    assigned_tech = None
                    if data.get("assigned_employee_code"):
                        assigned_tech = Employee.objects.for_workspace(workspace).filter(code=data["assigned_employee_code"]).first()

                    loc = None
                    if data.get("latitude") is not None and data.get("longitude") is not None:
                        loc = Point(float(data["longitude"]), float(data["latitude"]), srid=4326)

                    req, created = ServiceRequest.objects.update_or_create(
                        workspace=workspace,
                        request_number=str(data["request_number"]).strip(),
                        defaults={
                            "customer": cust,
                            "service": svc,
                            "sla": default_sla,
                            "title": str(data["title"]).strip(),
                            "priority": data.get("priority", ServiceRequestPriority.MEDIUM),
                            "status": data.get("status", ServiceRequestStatus.OPEN),
                            "assigned_employee": assigned_tech,
                            "location": loc,
                            "response_deadline_at": data.get("response_deadline_at"),
                            "resolution_deadline_at": data.get("resolution_deadline_at"),
                        },
                    )
                    inserted_count += 1
                    persisted_ids.append(req.id)

            elif target_entity == "Task":
                for row_num, data in valid_payloads:
                    sr = ServiceRequest.objects.for_workspace(workspace).filter(request_number=data["request_number"]).first()
                    assigned_tech = None
                    if data.get("assigned_employee_code"):
                        assigned_tech = Employee.objects.for_workspace(workspace).filter(code=data["assigned_employee_code"]).first()

                    task = Task.objects.create(
                        service_request=sr,
                        assigned_employee=assigned_tech,
                        title=str(data["title"]).strip(),
                        status=data.get("status", TaskStatus.PENDING),
                        estimated_duration_minutes=int(data.get("estimated_duration", 60)),
                        actual_duration_minutes=data.get("actual_duration"),
                    )
                    inserted_count += 1
                    persisted_ids.append(task.id)

            elif target_entity == "LaborEntry":
                for row_num, data in valid_payloads:
                    task = Task.objects.filter(service_request__workspace=workspace, id=data["task_id"]).first()
                    emp = Employee.objects.for_workspace(workspace).filter(code=data["employee_code"]).first()
                    rate = Decimal(str(data.get("hourly_rate_snapshot") or (emp.hourly_labor_rate if emp else "150000.00")))
                    dur = int(data.get("duration_minutes", 60))
                    cost = (Decimal(dur) / Decimal("60.0")) * rate

                    entry = LaborEntry.objects.create(
                        task=task,
                        employee=emp,
                        started_at=data["started_at"],
                        ended_at=data["ended_at"],
                        duration_minutes=dur,
                        hourly_rate_snapshot=rate,
                        labor_cost=cost,
                    )
                    inserted_count += 1
                    persisted_ids.append(entry.id)

    except Exception as e:
        log_action(
            workspace=workspace,
            actor_user=user,
            action="MAPPING_FAILED",
            entity_type=target_entity,
            entity_id=str(profile.id),
            changes={"error": str(e), "profile_id": str(profile.id), "import_job_id": str(import_job.id)},
        )
        return {
            "status": "FAILED",
            "message": f"Database transaction failed: {str(e)}",
            "inserted_count": 0,
            "failed_count": total_records,
            "errors": [{"error": str(e)}],
        }

    status_str = "COMPLETED" if len(import_errors) == 0 else "PARTIAL"

    log_action(
        workspace=workspace,
        actor_user=user,
        action="MAPPING_APPLIED",
        entity_type=target_entity,
        entity_id=str(profile.id),
        changes={
            "profile_name": profile.name,
            "target_entity": target_entity,
            "import_job_id": str(import_job.id),
            "total_records": total_records,
            "inserted_count": inserted_count,
            "failed_count": len(import_errors),
            "status": status_str,
        },
    )

    return {
        "status": status_str,
        "target_entity": target_entity,
        "total_records": total_records,
        "inserted_count": inserted_count,
        "failed_count": len(import_errors),
        "errors": import_errors,
    }
