"""
Canonical Validation Engine for Data Mapping.
Validates transformed payloads against the Standard Data Model contracts,
choice enums, nullability, unique constraints, and foreign key references.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from apps.mapping.canonical import get_canonical_model, CanonicalFieldType
from apps.retail.models import Customer, Product, Branch
from apps.service_ops.models import Employee, Service, ServiceRequest, Task


def validate_canonical_record(
    canonical_data: Dict[str, Any],
    target_entity: str,
    workspace,
    check_foreign_keys: bool = True,
) -> List[Dict[str, Any]]:
    """
    Validates a transformed canonical dictionary against the target entity definition.
    Returns list of validation errors: [{"field": str, "message": str, "code": str}]
    """
    errors: List[Dict[str, Any]] = []
    model_def = get_canonical_model(target_entity)

    if not model_def:
        errors.append({
            "field": "__all__",
            "message": f"Unknown canonical entity '{target_entity}'.",
            "code": "UNKNOWN_ENTITY",
        })
        return errors

    # 1. Required Field Checks
    for fname, fdef in model_def.fields.items():
        if fdef.required:
            val = canonical_data.get(fname)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append({
                    "field": fname,
                    "message": f"Missing required canonical field '{fname}' ({fdef.description}).",
                    "code": "REQUIRED_FIELD_MISSING",
                })

    # Special rule: Order requires transaction amount in either total_amount or revenue
    if target_entity == "Order":
        has_total = canonical_data.get("total_amount") is not None and str(canonical_data.get("total_amount")).strip() != ""
        has_rev = canonical_data.get("revenue") is not None and str(canonical_data.get("revenue")).strip() != ""
        if not (has_total or has_rev):
            errors.append({
                "field": "total_amount",
                "message": "Order requires a transaction monetary amount ('total_amount' or 'revenue').",
                "code": "REQUIRED_FIELD_MISSING",
            })
        else:
            # Synchronize both fields so downstream services have consistent access
            amt_val = canonical_data.get("total_amount") if has_total else canonical_data.get("revenue")
            if not has_total:
                canonical_data["total_amount"] = amt_val
            if not has_rev:
                canonical_data["revenue"] = amt_val

    # 2. Field-level type, choices, and range checks
    for fname, val in list(canonical_data.items()):
        if val is None:
            continue

        fdef = model_def.get_field(fname)
        if not fdef:
            # Extra fields not defined in canonical model are allowed or warned
            continue

        # Choice / Enum Check
        if fdef.choices and str(val).upper() not in [c.upper() for c in fdef.choices]:
            errors.append({
                "field": fname,
                "message": f"Invalid choice '{val}'. Allowed choices: {fdef.choices}.",
                "code": "INVALID_CHOICE",
            })

        # Coordinates check
        if fname == "latitude":
            try:
                lat = float(val)
                if not (-90.0 <= lat <= 90.0):
                    errors.append({"field": fname, "message": f"Latitude '{lat}' must be between -90 and 90.", "code": "OUT_OF_RANGE"})
            except (ValueError, TypeError):
                errors.append({"field": fname, "message": "Latitude must be a valid number.", "code": "INVALID_TYPE"})

        if fname == "longitude":
            try:
                lon = float(val)
                if not (-180.0 <= lon <= 180.0):
                    errors.append({"field": fname, "message": f"Longitude '{lon}' must be between -180 and 180.", "code": "OUT_OF_RANGE"})
            except (ValueError, TypeError):
                errors.append({"field": fname, "message": "Longitude must be a valid number.", "code": "INVALID_TYPE"})

        # Monetary Checks
        if fname in ("unit_price", "total_amount", "revenue", "cost_price", "base_fee", "hourly_labor_rate", "hourly_rate_snapshot", "discount_amount", "tax_amount"):
            if isinstance(val, (int, float, str)):
                try:
                    val = Decimal(str(val))
                except Exception:
                    errors.append({"field": fname, "message": f"'{val}' is not a valid Decimal amount.", "code": "INVALID_DECIMAL"})
            if isinstance(val, Decimal) and val < 0:
                errors.append({"field": fname, "message": f"Amount '{val}' cannot be negative.", "code": "NEGATIVE_AMOUNT"})

        # Quantity and duration checks
        if fname in ("quantity", "standard_duration_minutes", "duration_minutes", "estimated_duration", "stock_quantity"):
            try:
                q = int(val)
                if q <= 0 and fname in ("quantity", "standard_duration_minutes", "duration_minutes"):
                    errors.append({"field": fname, "message": f"'{fname}' must be greater than zero.", "code": "INVALID_QUANTITY"})
                elif q < 0 and fname == "stock_quantity":
                    errors.append({"field": fname, "message": "'stock_quantity' cannot be negative.", "code": "INVALID_QUANTITY"})
            except (ValueError, TypeError):
                errors.append({"field": fname, "message": f"'{fname}' must be an integer.", "code": "INVALID_INTEGER"})

    # 3. Foreign Key Checks within the active workspace
    if check_foreign_keys and workspace:
        if target_entity == "Order":
            cust_id = canonical_data.get("customer_id")
            if cust_id:
                if not Customer.objects.for_workspace(workspace).filter(code=cust_id).exists():
                    errors.append({
                        "field": "customer_id",
                        "message": f"Customer with code '{cust_id}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

            branch_code = canonical_data.get("branch_code")
            if branch_code:
                if not Branch.objects.for_workspace(workspace).filter(code=branch_code).exists():
                    errors.append({
                        "field": "branch_code",
                        "message": f"Branch with code '{branch_code}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

        elif target_entity == "OrderItem":
            sku = canonical_data.get("sku")
            if sku:
                if not Product.objects.for_workspace(workspace).filter(sku=sku).exists():
                    errors.append({
                        "field": "sku",
                        "message": f"Product with SKU '{sku}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

        elif target_entity == "ServiceRequest":
            cust_id = canonical_data.get("customer_id")
            if cust_id:
                if not Customer.objects.for_workspace(workspace).filter(code=cust_id).exists():
                    errors.append({
                        "field": "customer_id",
                        "message": f"Customer with code '{cust_id}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

            service_code = canonical_data.get("service_code")
            if service_code:
                if not Service.objects.for_workspace(workspace).filter(code=service_code).exists():
                    errors.append({
                        "field": "service_code",
                        "message": f"Service with code '{service_code}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

            tech_code = canonical_data.get("assigned_employee_code")
            if tech_code:
                if not Employee.objects.for_workspace(workspace).filter(code=tech_code).exists():
                    errors.append({
                        "field": "assigned_employee_code",
                        "message": f"Technician with code '{tech_code}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

        elif target_entity == "Task":
            req_num = canonical_data.get("request_number")
            if req_num:
                if not ServiceRequest.objects.for_workspace(workspace).filter(request_number=req_num).exists():
                    errors.append({
                        "field": "request_number",
                        "message": f"Service request '{req_num}' does not exist in workspace '{workspace.code}'.",
                        "code": "FOREIGN_KEY_NOT_FOUND",
                    })

    return errors
