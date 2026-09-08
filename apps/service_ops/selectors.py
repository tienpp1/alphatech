"""
apps.service_ops.selectors - High-Performance Aggregations, Selectors, and Workload Metrics.

Provides:
- Real-time KPI summaries for Service Operations dashboard (Tickets, Tasks, SLA, Labor Cost, Avg Resolution Time)
- Deterministic technician workload rankings and statistics
- Category, Priority, and Status breakdowns
- SLA compliance metrics
"""

from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Q, Avg, Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone

from apps.workspaces.models import Workspace
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    Schedule,
    ScheduleStatus,
    LaborEntry,
)
from apps.service_ops.sla_engine import calculate_sla_status, SLAComplianceStatus


def get_service_dashboard_summary(workspace: Workspace) -> dict:
    """
    Computes overarching operations KPI summary for the active workspace.
    """
    now = timezone.now()
    requests_qs = ServiceRequest.objects.filter(workspace=workspace)
    total_requests = requests_qs.count()

    open_requests = requests_qs.filter(status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]).count()
    in_progress_requests = requests_qs.filter(status=ServiceRequestStatus.IN_PROGRESS).count()
    resolved_requests = requests_qs.filter(status__in=[ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED]).count()
    cancelled_requests = requests_qs.filter(status=ServiceRequestStatus.CANCELLED).count()

    tasks_qs = Task.objects.filter(service_request__workspace=workspace)
    active_tasks = tasks_qs.filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]).count()
    completed_tasks = tasks_qs.filter(status=TaskStatus.COMPLETED).count()
    overdue_tasks = tasks_qs.filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS], due_at__lt=now).count()

    employees_qs = Employee.objects.filter(workspace=workspace, is_active=True)
    total_technicians = employees_qs.count()
    available_technicians = employees_qs.filter(is_available=True).count()

    # Labor Cost & Labor Time Aggregation
    labor_entries_qs = LaborEntry.objects.filter(task__service_request__workspace=workspace)
    total_labor_cost = labor_entries_qs.aggregate(total=Sum("labor_cost"))["total"] or Decimal("0.00")
    total_labor_minutes = labor_entries_qs.aggregate(total=Sum("duration_minutes"))["total"] or 0
    total_labor_hours = round(total_labor_minutes / 60.0, 1)

    # Average Resolution Time Calculation (hours)
    resolved_tickets = requests_qs.filter(
        status__in=[ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED],
        resolved_at__isnull=False,
    )
    total_res_hours = 0.0
    res_count = 0
    for r in resolved_tickets[:200]:
        if r.resolved_at and r.created_at:
            total_res_hours += (r.resolved_at - r.created_at).total_seconds() / 3600.0
            res_count += 1
    avg_resolution_time_hours = round(total_res_hours / res_count, 1) if res_count > 0 else 0.0

    # Calculate SLA breaches and compliance rate
    breached_count = 0
    at_risk_count = 0
    on_time_count = 0

    for req in requests_qs.select_related("sla")[:200]:
        sla_info = calculate_sla_status(req, reference_time=now)
        if sla_info["overall_status"] == SLAComplianceStatus.BREACHED:
            breached_count += 1
        elif sla_info["overall_status"] == SLAComplianceStatus.AT_RISK:
            at_risk_count += 1
        else:
            on_time_count += 1

    evaluated_total = breached_count + at_risk_count + on_time_count
    compliance_rate = round((on_time_count / evaluated_total * 100), 1) if evaluated_total > 0 else 100.0

    # Tickets by Service Category Breakdown
    category_counts = {cat: 0 for cat in ServiceCategory.values}
    cat_agg = (
        requests_qs.values("service__category")
        .annotate(count=Count("id"))
    )
    for entry in cat_agg:
        cat_val = entry["service__category"]
        if cat_val in category_counts:
            category_counts[cat_val] = entry["count"]

    return {
        "total_requests": total_requests,
        "open_requests": open_requests,
        "in_progress_requests": in_progress_requests,
        "resolved_requests": resolved_requests,
        "cancelled_requests": cancelled_requests,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "total_technicians": total_technicians,
        "available_technicians": available_technicians,
        "total_labor_cost": total_labor_cost,
        "total_labor_hours": total_labor_hours,
        "avg_resolution_time_hours": avg_resolution_time_hours,
        "on_time_sla_count": on_time_count,
        "at_risk_sla_count": at_risk_count,
        "breached_sla_count": breached_count,
        "sla_compliance_rate": compliance_rate,
        "tickets_by_category": category_counts,
    }


def get_technicians_workload_breakdown(workspace: Workspace) -> list[dict]:
    """
    Returns technicians sorted by current workload score and active assignments.
    """
    now = timezone.now()
    employees = Employee.objects.filter(workspace=workspace, is_active=True).order_by("-current_workload_score", "full_name")
    breakdown = []

    for emp in employees:
        active_tasks = Task.objects.filter(assigned_to=emp, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        active_count = active_tasks.count()
        overdue_count = active_tasks.filter(due_at__lt=now).count()
        estimated_minutes = active_tasks.aggregate(total=Sum("estimated_duration_minutes"))["total"] or 0

        # Labor logged by this technician
        labor_logged = LaborEntry.objects.filter(employee=emp)
        logged_minutes = labor_logged.aggregate(total=Sum("duration_minutes"))["total"] or 0
        logged_cost = labor_logged.aggregate(total=Sum("labor_cost"))["total"] or Decimal("0.00")

        breakdown.append({
            "id": emp.id,
            "code": emp.code,
            "name": emp.full_name,
            "phone": emp.phone,
            "skills": emp.skills,
            "hourly_labor_rate": emp.hourly_labor_rate,
            "is_available": emp.is_available,
            "workload_score": emp.current_workload_score,
            "active_tasks_count": active_count,
            "overdue_tasks_count": overdue_count,
            "estimated_minutes": estimated_minutes,
            "total_labor_minutes": logged_minutes,
            "total_labor_cost": logged_cost,
        })
    return breakdown


def get_requests_by_status_breakdown(workspace: Workspace) -> list[dict]:
    data = (
        ServiceRequest.objects.filter(workspace=workspace)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    return list(data)


def get_requests_by_priority_breakdown(workspace: Workspace) -> list[dict]:
    data = (
        ServiceRequest.objects.filter(workspace=workspace)
        .values("priority")
        .annotate(count=Count("id"))
        .order_by("priority")
    )
    return list(data)


def get_requests_by_category_breakdown(workspace: Workspace) -> list[dict]:
    data = (
        ServiceRequest.objects.filter(workspace=workspace)
        .values("service__category")
        .annotate(count=Count("id"))
        .order_by("service__category")
    )
    return list(data)
