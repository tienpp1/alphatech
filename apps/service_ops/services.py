"""
apps.service_ops.services - Transactional Business Services for Service Operations.

Enforces:
- Atomic service request creation & SLA deadline computation
- Strict request & task lifecycle state machines
- Technician assignment & workload score recalculation
- Schedule conflict validation (overlap rejection)
- Server-calculated labor time tracking & immutable rate snapshotting
- Service request labor cost aggregation
- Comprehensive audit logging via apps.audit
"""

from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point

from apps.workspaces.models import Workspace
from apps.audit.services import log_action
from apps.retail.models import Customer
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    SLA,
    SLAPriority,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    Schedule,
    ScheduleStatus,
    LaborEntry,
)


# ==========================================
# Service Catalog Management
# ==========================================

def create_service(workspace: Workspace, user, data: dict) -> Service:
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    category = (data.get("category") or ServiceCategory.INSTALLATION).strip().upper()

    if not code or not name:
        raise ValidationError("Service code and name are required.")

    if category not in ServiceCategory.values:
        raise ValidationError(f"Invalid service category '{category}'.")

    if Service.objects.filter(workspace=workspace, code=code).exists():
        raise ValidationError(f"Service with code '{code}' already exists in this workspace.")

    service = Service.objects.create(
        workspace=workspace,
        code=code,
        name=name,
        category=category,
        description=data.get("description", ""),
        standard_duration_minutes=int(data.get("standard_duration_minutes", 60)),
        base_fee=Decimal(str(data.get("base_fee", "0.00"))),
        is_active=bool(data.get("is_active", True)),
    )

    log_action(
        actor_user=user,
        workspace=workspace,
        action="SERVICE_CREATED",
        entity_type="Service",
        entity_id=str(service.id),
        changes={"code": service.code, "name": service.name, "category": service.category, "base_fee": str(service.base_fee)},
    )
    return service


def update_service(service: Service, user, data: dict) -> Service:
    before = {
        "name": service.name,
        "category": service.category,
        "description": service.description,
        "standard_duration_minutes": service.standard_duration_minutes,
        "base_fee": str(service.base_fee),
        "is_active": service.is_active,
    }

    if "name" in data and data["name"]:
        service.name = data["name"].strip()
    if "category" in data and data["category"]:
        cat = data["category"].strip().upper()
        if cat not in ServiceCategory.values:
            raise ValidationError(f"Invalid service category '{cat}'.")
        service.category = cat
    if "description" in data:
        service.description = data["description"]
    if "standard_duration_minutes" in data:
        service.standard_duration_minutes = int(data["standard_duration_minutes"])
    if "base_fee" in data:
        service.base_fee = Decimal(str(data["base_fee"]))
    if "is_active" in data:
        service.is_active = bool(data["is_active"])

    service.save()

    after = {
        "name": service.name,
        "category": service.category,
        "standard_duration_minutes": service.standard_duration_minutes,
        "base_fee": str(service.base_fee),
        "is_active": service.is_active,
    }

    log_action(
        actor_user=user,
        workspace=service.workspace,
        action="SERVICE_UPDATED",
        entity_type="Service",
        entity_id=str(service.id),
        changes={"before": before, "after": after},
    )
    return service


def delete_service(service: Service, user) -> None:
    if service.requests.exists():
        raise ValidationError(
            f"Cannot delete service '{service.code}' because service requests are associated with it. Deactivate it instead."
        )
    service_id = str(service.id)
    service_code = service.code
    workspace = service.workspace
    service.delete()

    log_action(
        actor_user=user,
        workspace=workspace,
        action="SERVICE_DELETED",
        entity_type="Service",
        entity_id=service_id,
        changes={"code": service_code},
    )


# ==========================================
# Employee / Technician Management
# ==========================================

def create_employee(workspace: Workspace, user, data: dict) -> Employee:
    code = (data.get("code") or "").strip().upper()
    full_name = (data.get("full_name") or "").strip()
    if not code or not full_name:
        raise ValidationError("Employee code and full name are required.")

    if Employee.objects.filter(workspace=workspace, code=code).exists():
        raise ValidationError(f"Employee with code '{code}' already exists in this workspace.")

    lat = data.get("latitude")
    lng = data.get("longitude")
    location = None
    if lat is not None and lng is not None:
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
                raise ValidationError("Invalid coordinates: Latitude must be between -90 and 90, Longitude between -180 and 180.")
            location = Point(lng_f, lat_f, srid=4326)
        except (ValueError, TypeError):
            raise ValidationError("Invalid coordinates format.")

    hourly_rate = Decimal(str(data.get("hourly_labor_rate", "150000.00")))
    if hourly_rate < Decimal("0.00"):
        raise ValidationError("Hourly labor rate cannot be negative.")

    employee = Employee.objects.create(
        workspace=workspace,
        user_id=data.get("user_id"),
        code=code,
        full_name=full_name,
        phone=data.get("phone", ""),
        email=data.get("email"),
        skills=data.get("skills", []),
        hourly_labor_rate=hourly_rate,
        current_location=location,
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lng)) if lng is not None else None,
        location_updated_at=timezone.now() if location else None,
        is_available=bool(data.get("is_available", True)),
        is_active=bool(data.get("is_active", True)),
    )

    log_action(
        actor_user=user,
        workspace=workspace,
        action="EMPLOYEE_CREATED",
        entity_type="Employee",
        entity_id=str(employee.id),
        changes={
            "code": employee.code,
            "full_name": employee.full_name,
            "skills": employee.skills,
            "hourly_labor_rate": str(employee.hourly_labor_rate),
        },
    )
    return employee


def update_employee(employee: Employee, user, data: dict) -> Employee:
    before = {
        "full_name": employee.full_name,
        "phone": employee.phone,
        "skills": employee.skills,
        "hourly_labor_rate": str(employee.hourly_labor_rate),
        "is_available": employee.is_available,
        "is_active": employee.is_active,
    }

    if "full_name" in data and data["full_name"]:
        employee.full_name = data["full_name"].strip()
    if "phone" in data:
        employee.phone = data["phone"]
    if "email" in data:
        employee.email = data["email"]
    if "skills" in data:
        employee.skills = data["skills"]
    if "hourly_labor_rate" in data:
        rate = Decimal(str(data["hourly_labor_rate"]))
        if rate < Decimal("0.00"):
            raise ValidationError("Hourly labor rate cannot be negative.")
        employee.hourly_labor_rate = rate
    if "is_available" in data:
        employee.is_available = bool(data["is_available"])
    if "is_active" in data:
        employee.is_active = bool(data["is_active"])

    if "latitude" in data and "longitude" in data:
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat is not None and lng is not None:
            lat_f = float(lat)
            lng_f = float(lng)
            if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
                raise ValidationError("Invalid coordinates range.")
            employee.current_location = Point(lng_f, lat_f, srid=4326)
            employee.latitude = Decimal(str(lat))
            employee.longitude = Decimal(str(lng))
            employee.location_updated_at = timezone.now()

    employee.save()

    after = {
        "full_name": employee.full_name,
        "hourly_labor_rate": str(employee.hourly_labor_rate),
        "is_available": employee.is_available,
        "is_active": employee.is_active,
    }

    log_action(
        actor_user=user,
        workspace=employee.workspace,
        action="EMPLOYEE_UPDATED",
        entity_type="Employee",
        entity_id=str(employee.id),
        changes={"before": before, "after": after},
    )
    return employee


def recalculate_employee_workload(employee: Employee) -> float:
    """
    Computes workload score: active_tasks + (overdue_tasks * 1.5).
    """
    now = timezone.now()
    active_tasks = Task.objects.filter(assigned_to=employee, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
    active_count = active_tasks.count()
    overdue_count = active_tasks.filter(due_at__lt=now).count()

    score = round(active_count * 1.0 + (overdue_count * 1.5), 2)
    employee.current_workload_score = score
    employee.save(update_fields=["current_workload_score"])
    return score


# ==========================================
# SLA Policy Management
# ==========================================

def create_sla_policy(workspace: Workspace, user, data: dict) -> SLA:
    name = (data.get("name") or "").strip()
    priority = (data.get("priority") or "MEDIUM").strip().upper()
    if priority not in SLAPriority.values:
        raise ValidationError(f"Invalid SLA priority '{priority}'.")

    if SLA.objects.filter(workspace=workspace, priority=priority).exists():
        raise ValidationError(f"SLA policy for priority '{priority}' already exists in this workspace.")

    sla = SLA.objects.create(
        workspace=workspace,
        name=name or f"{priority.title()} Priority SLA",
        priority=priority,
        response_time_hours=int(data.get("response_time_hours", 24)),
        resolution_time_hours=int(data.get("resolution_time_hours", 48)),
        is_active=bool(data.get("is_active", True)),
    )

    log_action(
        actor_user=user,
        workspace=workspace,
        action="SLA_CREATED",
        entity_type="SLA",
        entity_id=str(sla.id),
        changes={"name": sla.name, "priority": sla.priority, "response_time_hours": sla.response_time_hours, "resolution_time_hours": sla.resolution_time_hours},
    )
    return sla


# ==========================================
# Service Request Lifecycle & Operations
# ==========================================

@transaction.atomic
def create_service_request(workspace: Workspace, user, data: dict) -> ServiceRequest:
    """
    Creates a new service incident ticket with deterministic SLA deadlines.
    """
    customer_id = data.get("customer_id")
    service_id = data.get("service_id")
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()

    if not title:
        raise ValidationError("Title is required for service request.")

    try:
        customer = Customer.objects.get(id=customer_id, workspace=workspace, is_active=True)
    except Customer.DoesNotExist:
        raise ValidationError("Valid active Customer belonging to this workspace is required.")

    try:
        service = Service.objects.get(id=service_id, workspace=workspace, is_active=True)
    except Service.DoesNotExist:
        raise ValidationError("Valid active Service belonging to this workspace is required.")

    priority = data.get("priority", ServiceRequestPriority.MEDIUM).upper()
    if priority not in ServiceRequestPriority.values:
        raise ValidationError(f"Invalid priority '{priority}'.")

    # Resolve SLA policy
    sla = SLA.objects.filter(workspace=workspace, priority=priority, is_active=True).first()
    now = timezone.now()

    response_hours = sla.response_time_hours if sla else 24
    resolution_hours = sla.resolution_time_hours if sla else 48

    response_deadline = now + timedelta(hours=response_hours)
    resolution_deadline = now + timedelta(hours=resolution_hours)

    # Generate request number if not provided
    request_number = data.get("request_number")
    if not request_number:
        count = ServiceRequest.objects.filter(workspace=workspace).count() + 1
        request_number = f"SR-{now.strftime('%Y%m%d')}-{count:04d}"

    # Location
    lat = data.get("latitude")
    lng = data.get("longitude")
    location = None
    if lat is not None and lng is not None:
        lat_f = float(lat)
        lng_f = float(lng)
        location = Point(lng_f, lat_f, srid=4326)
    elif customer.location:
        location = customer.location
        lat = customer.latitude
        lng = customer.longitude

    assigned_employee = None
    assigned_employee_id = data.get("assigned_employee_id")
    if assigned_employee_id:
        try:
            assigned_employee = Employee.objects.get(id=assigned_employee_id, workspace=workspace, is_active=True)
        except Employee.DoesNotExist:
            raise ValidationError("Assigned employee not found or inactive in this workspace.")

    status = ServiceRequestStatus.ASSIGNED if assigned_employee else ServiceRequestStatus.OPEN
    responded_at = now if assigned_employee else None

    req = ServiceRequest.objects.create(
        workspace=workspace,
        request_number=request_number,
        customer=customer,
        service=service,
        sla=sla,
        assigned_employee=assigned_employee,
        title=title,
        description=description,
        location=location,
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lng)) if lng is not None else None,
        priority=priority,
        status=status,
        scheduled_at=data.get("scheduled_at"),
        response_deadline_at=response_deadline,
        resolution_deadline_at=resolution_deadline,
        responded_at=responded_at,
    )

    # If assigned immediately, create initial task
    if assigned_employee:
        Task.objects.create(
            service_request=req,
            assigned_to=assigned_employee,
            title=f"Execute: {service.name}",
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            estimated_duration_minutes=service.standard_duration_minutes,
            due_at=resolution_deadline,
        )
        recalculate_employee_workload(assigned_employee)

    log_action(
        actor_user=user,
        workspace=workspace,
        action="REQUEST_CREATED",
        entity_type="ServiceRequest",
        entity_id=str(req.id),
        changes={
            "request_number": req.request_number,
            "title": req.title,
            "priority": req.priority,
            "status": req.status,
            "assigned_employee": str(assigned_employee.id) if assigned_employee else None,
        },
    )
    return req


@transaction.atomic
def assign_service_request(service_request: ServiceRequest, employee: Employee, user, scheduled_at=None) -> ServiceRequest:
    """
    Assigns an employee/technician to a service request.
    """
    if employee.workspace_id != service_request.workspace_id:
        raise ValidationError("Technician does not belong to the ticket workspace.")
    if not employee.is_active:
        raise ValidationError("Cannot assign inactive technician.")

    now = timezone.now()
    old_assigned = service_request.assigned_employee
    service_request.assigned_employee = employee
    if service_request.status == ServiceRequestStatus.OPEN:
        service_request.status = ServiceRequestStatus.ASSIGNED

    if not service_request.responded_at:
        service_request.responded_at = now

    if scheduled_at:
        service_request.scheduled_at = scheduled_at

    service_request.save()

    # Create or update primary task
    task = service_request.tasks.filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]).first()
    if not task:
        Task.objects.create(
            service_request=service_request,
            assigned_to=employee,
            title=f"Execute: {service_request.service.name}",
            description=service_request.description,
            status=TaskStatus.PENDING,
            priority=service_request.priority,
            estimated_duration_minutes=service_request.service.standard_duration_minutes,
            due_at=service_request.resolution_deadline_at,
        )
    else:
        task.assigned_to = employee
        task.save(update_fields=["assigned_to"])

    recalculate_employee_workload(employee)
    if old_assigned and old_assigned.id != employee.id:
        recalculate_employee_workload(old_assigned)

    log_action(
        actor_user=user,
        workspace=service_request.workspace,
        action="REQUEST_ASSIGNED",
        entity_type="ServiceRequest",
        entity_id=str(service_request.id),
        changes={"employee_id": str(employee.id), "employee_name": employee.full_name, "status": service_request.status},
    )
    return service_request


@transaction.atomic
def transition_service_request_status(service_request: ServiceRequest, new_status: str, user) -> ServiceRequest:
    """
    Enforces valid state machine transitions:
    OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
    Terminal cancellations: OPEN -> CANCELLED, ASSIGNED -> CANCELLED, IN_PROGRESS -> CANCELLED
    """
    current = service_request.status
    if current == new_status:
        return service_request

    valid_transitions = {
        ServiceRequestStatus.OPEN: [ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.CANCELLED],
        ServiceRequestStatus.ASSIGNED: [ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.OPEN, ServiceRequestStatus.CANCELLED],
        ServiceRequestStatus.IN_PROGRESS: [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CANCELLED],
        ServiceRequestStatus.RESOLVED: [ServiceRequestStatus.CLOSED, ServiceRequestStatus.IN_PROGRESS],
        ServiceRequestStatus.CLOSED: [],
        ServiceRequestStatus.CANCELLED: [],
    }

    if new_status not in valid_transitions.get(current, []):
        raise ValidationError(f"Invalid status transition from '{current}' to '{new_status}'.")

    now = timezone.now()
    if new_status in [ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS] and not service_request.responded_at:
        service_request.responded_at = now
    if new_status == ServiceRequestStatus.RESOLVED:
        service_request.resolved_at = now
    if new_status in [ServiceRequestStatus.CLOSED, ServiceRequestStatus.CANCELLED]:
        service_request.closed_at = now

    old_status = service_request.status
    service_request.status = new_status
    service_request.save()

    if service_request.assigned_employee:
        recalculate_employee_workload(service_request.assigned_employee)

    log_action(
        actor_user=user,
        workspace=service_request.workspace,
        action="REQUEST_STATUS_CHANGED",
        entity_type="ServiceRequest",
        entity_id=str(service_request.id),
        changes={"before": {"status": old_status}, "after": {"status": new_status}},
    )
    return service_request


# ==========================================
# Task Management
# ==========================================

def create_task(service_request: ServiceRequest, user, data: dict) -> Task:
    title = (data.get("title") or "").strip()
    if not title:
        raise ValidationError("Task title is required.")

    assigned_to = None
    assigned_to_id = data.get("assigned_to_id")
    if assigned_to_id:
        try:
            assigned_to = Employee.objects.get(id=assigned_to_id, workspace=service_request.workspace, is_active=True)
        except Employee.DoesNotExist:
            raise ValidationError("Assigned employee not found or inactive in ticket workspace.")

    task = Task.objects.create(
        service_request=service_request,
        assigned_to=assigned_to,
        title=title,
        description=data.get("description", ""),
        status=data.get("status", TaskStatus.PENDING),
        priority=data.get("priority", service_request.priority),
        estimated_duration_minutes=int(data.get("estimated_duration_minutes", 60)),
        due_at=data.get("due_at", service_request.resolution_deadline_at),
    )

    if assigned_to:
        recalculate_employee_workload(assigned_to)

    log_action(
        actor_user=user,
        workspace=service_request.workspace,
        action="TASK_CREATED",
        entity_type="Task",
        entity_id=str(task.id),
        changes={"title": task.title, "service_request_id": str(service_request.id), "status": task.status},
    )
    return task


def transition_task_status(task: Task, new_status: str, user, actual_duration_minutes=None) -> Task:
    current = task.status
    if current == new_status:
        return task

    valid_transitions = {
        TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
        TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.CANCELLED],
        TaskStatus.COMPLETED: [],
        TaskStatus.CANCELLED: [],
    }

    if new_status not in valid_transitions.get(current, []):
        raise ValidationError(f"Invalid task status transition from '{current}' to '{new_status}'.")

    now = timezone.now()
    if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = now
    elif new_status == TaskStatus.COMPLETED:
        task.completed_at = now
        if actual_duration_minutes:
            task.actual_duration_minutes = int(actual_duration_minutes)
        elif task.started_at:
            task.actual_duration_minutes = max(int((now - task.started_at).total_seconds() / 60), 1)

    old_status = task.status
    task.status = new_status
    task.save()

    if task.assigned_to:
        recalculate_employee_workload(task.assigned_to)

    log_action(
        actor_user=user,
        workspace=task.workspace,
        action="TASK_STATUS_CHANGED",
        entity_type="Task",
        entity_id=str(task.id),
        changes={"before": {"status": old_status}, "after": {"status": new_status}},
    )
    return task


# ==========================================
# Scheduling & Conflict Detection
# ==========================================

def create_schedule(task: Task, employee: Employee, user, data: dict) -> Schedule:
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not start_time or not end_time:
        raise ValidationError("Schedule start_time and end_time are required.")

    if start_time >= end_time:
        raise ValidationError("Schedule end_time must be strictly after start_time.")

    if employee.workspace_id != task.workspace.id:
        raise ValidationError("Employee and Task must belong to the same workspace.")

    overlapping = Schedule.objects.filter(
        employee=employee,
        status__in=[ScheduleStatus.SCHEDULED, ScheduleStatus.IN_PROGRESS],
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if overlapping.exists():
        overlap_info = overlapping.first()
        raise ValidationError(
            f"Schedule conflict for technician {employee.full_name}: already scheduled from "
            f"{overlap_info.start_time.strftime('%Y-%m-%d %H:%M')} to {overlap_info.end_time.strftime('%H:%M')}."
        )

    schedule = Schedule.objects.create(
        task=task,
        employee=employee,
        start_time=start_time,
        end_time=end_time,
        status=data.get("status", ScheduleStatus.SCHEDULED),
        notes=data.get("notes", ""),
    )

    log_action(
        actor_user=user,
        workspace=task.workspace,
        action="SCHEDULE_CREATED",
        entity_type="Schedule",
        entity_id=str(schedule.id),
        changes={
            "task_id": str(task.id),
            "employee_id": str(employee.id),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
        },
    )
    return schedule


# ==========================================
# Labor Time Tracking & Cost Calculation
# ==========================================

@transaction.atomic
def create_labor_entry(task: Task, employee: Employee, user, data: dict) -> LaborEntry:
    """
    Creates a labor tracking entry.
    Snapshots employee's hourly labor rate at entry creation time and computes labor cost server-side.
    Formula: labor_cost = (duration_minutes / 60) * hourly_rate_snapshot
    """
    if employee.workspace_id != task.workspace.id:
        raise ValidationError("Employee and Task must belong to the same workspace.")

    started_at = data.get("started_at")
    ended_at = data.get("ended_at")

    if not started_at or not ended_at:
        raise ValidationError("started_at and ended_at timestamps are required for labor tracking.")

    if started_at >= ended_at:
        raise ValidationError("ended_at must be strictly after started_at.")

    # Calculate duration
    calculated_minutes = int((ended_at - started_at).total_seconds() / 60)
    explicit_minutes = data.get("duration_minutes")
    duration_minutes = int(explicit_minutes) if explicit_minutes else calculated_minutes
    if duration_minutes <= 0:
        raise ValidationError("Duration in minutes must be greater than 0.")

    # Immutable snapshot of hourly rate
    hourly_rate_snapshot = employee.hourly_labor_rate

    # Server-calculated labor cost
    hours = Decimal(str(duration_minutes)) / Decimal("60.0")
    labor_cost = round(hours * hourly_rate_snapshot, 2)

    labor_entry = LaborEntry.objects.create(
        task=task,
        employee=employee,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=duration_minutes,
        hourly_rate_snapshot=hourly_rate_snapshot,
        labor_cost=labor_cost,
        notes=data.get("notes", ""),
    )

    log_action(
        actor_user=user,
        workspace=task.workspace,
        action="LABOR_ENTRY_CREATED",
        entity_type="LaborEntry",
        entity_id=str(labor_entry.id),
        changes={
            "task_id": str(task.id),
            "employee_id": str(employee.id),
            "duration_minutes": labor_entry.duration_minutes,
            "hourly_rate_snapshot": str(labor_entry.hourly_rate_snapshot),
            "labor_cost": str(labor_entry.labor_cost),
        },
    )
    return labor_entry


def get_service_request_cost_breakdown(service_request: ServiceRequest) -> dict:
    """
    Computes total labor cost and estimated ticket cost breakdown.
    """
    entries = LaborEntry.objects.filter(task__service_request=service_request).select_related("employee", "task")
    
    total_labor_minutes = entries.aggregate(total=Sum("duration_minutes"))["total"] or 0
    total_labor_cost = entries.aggregate(total=Sum("labor_cost"))["total"] or Decimal("0.00")
    base_fee = service_request.service.base_fee
    total_cost = total_labor_cost + base_fee

    entries_data = [
        {
            "id": entry.id,
            "task_id": entry.task_id,
            "task_title": entry.task.title,
            "employee_id": entry.employee_id,
            "employee_name": entry.employee.full_name,
            "started_at": entry.started_at,
            "ended_at": entry.ended_at,
            "duration_minutes": entry.duration_minutes,
            "hourly_rate_snapshot": entry.hourly_rate_snapshot,
            "labor_cost": entry.labor_cost,
            "notes": entry.notes,
        }
        for entry in entries
    ]

    return {
        "service_request_id": service_request.id,
        "request_number": service_request.request_number,
        "total_labor_minutes": total_labor_minutes,
        "total_labor_hours": round(total_labor_minutes / 60.0, 2),
        "total_labor_cost": total_labor_cost,
        "service_base_fee": base_fee,
        "total_estimated_cost": total_cost,
        "labor_entries_count": entries.count(),
        "entries": entries_data,
    }
