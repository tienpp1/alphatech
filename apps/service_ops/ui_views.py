"""
apps.service_ops.ui_views - Web UI Views for Field & IT Service Operations.
"""

from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone, dateparse

from apps.accounts.services import has_workspace_permission
from apps.workspaces.models import WorkspaceType
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    SLA,
    ServiceRequest,
    ServiceRequestStatus,
    Task,
    TaskStatus,
    Schedule,
    LaborEntry,
)
from apps.service_ops.selectors import (
    get_service_dashboard_summary,
    get_technicians_workload_breakdown,
    get_requests_by_status_breakdown,
    get_requests_by_priority_breakdown,
    get_requests_by_category_breakdown,
)
from apps.service_ops.sla_engine import calculate_sla_status
from apps.service_ops.services import (
    assign_service_request,
    transition_service_request_status,
    transition_task_status,
    create_labor_entry,
    get_service_request_cost_breakdown,
)


def _get_service_workspace(request, permission_codename):
    return resolve_authorized_ui_workspace(
        request,
        WorkspaceType.SERVICE,
        permission_codename,
    )


@login_required
def dashboard_view(request):
    workspace = _get_service_workspace(request, "service.view_analytics")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_dashboard"})

    summary = get_service_dashboard_summary(workspace)
    technicians = get_technicians_workload_breakdown(workspace)[:6]
    status_breakdown = get_requests_by_status_breakdown(workspace)
    priority_breakdown = get_requests_by_priority_breakdown(workspace)
    category_breakdown = get_requests_by_category_breakdown(workspace)
    recent_requests = ServiceRequest.objects.filter(workspace=workspace).select_related(
        "customer", "service", "assigned_employee"
    ).order_by("-created_at")[:8]

    enriched_requests = []
    now = timezone.now()
    for req in recent_requests:
        sla_info = calculate_sla_status(req, reference_time=now)
        enriched_requests.append({"req": req, "sla": sla_info})

    context = {
        "active_tab": "service_dashboard",
        "active_workspace": workspace,
        "summary": summary,
        "technicians": technicians,
        "status_breakdown": status_breakdown,
        "priority_breakdown": priority_breakdown,
        "category_breakdown": category_breakdown,
        "recent_requests": enriched_requests,
    }
    return render(request, "service_ops/dashboard.html", context)


@login_required
def services_view(request):
    workspace = _get_service_workspace(request, "service.view_service")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_services"})

    qs = Service.objects.filter(workspace=workspace).order_by("category", "code")
    category_filter = request.GET.get("category")
    if category_filter:
        qs = qs.filter(category=category_filter.upper())

    return render(
        request,
        "service_ops/services.html",
        {
            "active_tab": "service_services",
            "active_workspace": workspace,
            "services": qs,
            "categories": ServiceCategory.choices,
            "current_category": category_filter,
        },
    )


@login_required
def employees_view(request):
    workspace = _get_service_workspace(request, "service.view_employee")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_employees"})

    technicians = get_technicians_workload_breakdown(workspace)
    return render(
        request,
        "service_ops/employees.html",
        {"active_tab": "service_employees", "active_workspace": workspace, "technicians": technicians},
    )


@login_required
def requests_view(request):
    workspace = _get_service_workspace(request, "service.view_request")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_requests"})

    qs = ServiceRequest.objects.filter(workspace=workspace).select_related(
        "customer", "service", "assigned_employee"
    ).order_by("-created_at")

    status_filter = request.GET.get("status")
    priority_filter = request.GET.get("priority")
    category_filter = request.GET.get("category")

    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    if priority_filter:
        qs = qs.filter(priority=priority_filter.upper())
    if category_filter:
        qs = qs.filter(service__category=category_filter.upper())

    now = timezone.now()
    enriched = []
    for req in qs[:100]:
        enriched.append({"req": req, "sla": calculate_sla_status(req, reference_time=now)})

    return render(
        request,
        "service_ops/requests.html",
        {
            "active_tab": "service_requests",
            "active_workspace": workspace,
            "requests": enriched,
            "current_status": status_filter,
            "current_priority": priority_filter,
            "current_category": category_filter,
            "categories": ServiceCategory.choices,
        },
    )


@login_required
def request_detail_view(request, pk):
    workspace = _get_service_workspace(request, "service.view_request")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_requests"})

    req = get_object_or_404(
        ServiceRequest.objects.select_related("customer", "service", "sla", "assigned_employee"),
        pk=pk,
        workspace=workspace,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        action_permission = {
            "assign": "service.assign_request",
            "start": "service.manage_request",
            "resolve": "service.manage_request",
            "close": "service.manage_request",
            "cancel": "service.manage_request",
        }.get(action)
        if action_permission and not has_workspace_permission(request.user, workspace, action_permission):
            raise PermissionDenied(f"Missing workspace permission: {action_permission}")
        try:
            if action == "assign":
                emp_id = request.POST.get("employee_id")
                emp = get_object_or_404(Employee, pk=emp_id, workspace=workspace)
                assign_service_request(req, emp, request.user)
                messages.success(request, f"Assigned to {emp.full_name} successfully.")
            elif action == "start":
                transition_service_request_status(req, ServiceRequestStatus.IN_PROGRESS, request.user)
                messages.success(request, "Ticket marked IN PROGRESS.")
            elif action == "resolve":
                transition_service_request_status(req, ServiceRequestStatus.RESOLVED, request.user)
                messages.success(request, "Ticket marked RESOLVED.")
            elif action == "close":
                transition_service_request_status(req, ServiceRequestStatus.CLOSED, request.user)
                messages.success(request, "Ticket marked CLOSED.")
            elif action == "cancel":
                transition_service_request_status(req, ServiceRequestStatus.CANCELLED, request.user)
                messages.warning(request, "Ticket CANCELLED.")
            elif action == "log_labor":
                task_id = request.POST.get("task_id")
                emp_id = request.POST.get("employee_id")
                duration = int(request.POST.get("duration_minutes", 60))
                notes = request.POST.get("notes", "")

                task = get_object_or_404(Task, pk=task_id, service_request=req)
                emp = get_object_or_404(Employee, pk=emp_id, workspace=workspace)
                can_manage_labor = has_workspace_permission(
                    request.user, workspace, "service.manage_task"
                ) or has_workspace_permission(request.user, workspace, "service.manage_employee")
                if not can_manage_labor and emp.user_id != request.user.id:
                    raise PermissionDenied("Technicians may only log labor for themselves.")

                now = timezone.now()
                create_labor_entry(
                    task=task,
                    employee=emp,
                    user=request.user,
                    data={
                        "started_at": now - timezone.timedelta(minutes=duration),
                        "ended_at": now,
                        "duration_minutes": duration,
                        "notes": notes,
                    },
                )
                messages.success(request, f"Logged {duration} minutes labor for {emp.full_name}.")
        except PermissionDenied:
            raise
        except Exception as e:
            messages.error(request, f"Action failed: {e}")
        return redirect("services_ui_request_detail", pk=req.id)

    tasks = req.tasks.select_related("assigned_to").prefetch_related("labor_entries__employee").order_by("created_at")
    now = timezone.now()
    sla_info = calculate_sla_status(req, reference_time=now)
    cost_info = get_service_request_cost_breakdown(req)
    available_technicians = Employee.objects.filter(workspace=workspace, is_active=True).order_by("full_name")
    can_assign = has_workspace_permission(request.user, workspace, "service.assign_request")
    can_manage_request = has_workspace_permission(request.user, workspace, "service.manage_request")
    can_manage_labor = has_workspace_permission(
        request.user, workspace, "service.manage_task"
    ) or has_workspace_permission(request.user, workspace, "service.manage_employee")
    own_employee_ids = set(
        Employee.objects.filter(workspace=workspace, user=request.user).values_list("id", flat=True)
    )

    return render(
        request,
        "service_ops/request_detail.html",
        {
            "active_tab": "service_requests",
            "active_workspace": workspace,
            "req": req,
            "tasks": tasks,
            "sla": sla_info,
            "cost_summary": cost_info,
            "technicians": available_technicians,
            "can_assign": can_assign,
            "can_manage_request": can_manage_request,
            "can_log_labor": can_manage_labor or bool(own_employee_ids),
        },
    )


@login_required
def tasks_view(request):
    workspace = _get_service_workspace(request, "service.view_task")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_tasks"})

    tasks = Task.objects.filter(service_request__workspace=workspace).select_related(
        "service_request", "assigned_to"
    ).prefetch_related("labor_entries").order_by("-created_at")
    return render(
        request,
        "service_ops/tasks.html",
        {"active_tab": "service_tasks", "active_workspace": workspace, "tasks": tasks},
    )


@login_required
def schedules_view(request):
    workspace = _get_service_workspace(request, "service.view_schedule")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_schedules"})

    schedules = Schedule.objects.filter(task__service_request__workspace=workspace).select_related(
        "employee", "task__service_request"
    ).order_by("start_time")
    return render(
        request,
        "service_ops/schedules.html",
        {"active_tab": "service_schedules", "active_workspace": workspace, "schedules": schedules},
    )


@login_required
def slas_view(request):
    workspace = _get_service_workspace(request, "service.view_sla")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_slas"})

    slas = SLA.objects.filter(workspace=workspace).order_by("priority")
    return render(
        request,
        "service_ops/slas.html",
        {"active_tab": "service_slas", "active_workspace": workspace, "slas": slas},
    )


@login_required
def labor_cost_view(request):
    workspace = _get_service_workspace(request, "service.view_analytics")
    if not workspace:
        return render(request, "retail/no_workspace.html", {"active_tab": "service_labor"})

    labor_entries = (
        LaborEntry.objects.filter(task__service_request__workspace=workspace)
        .select_related("employee", "task", "task__service_request", "task__service_request__customer")
        .order_by("-started_at")
    )
    total_minutes = sum(e.duration_minutes for e in labor_entries)
    total_hours = round(total_minutes / 60, 1)
    total_cost = sum(e.labor_cost for e in labor_entries)

    return render(
        request,
        "service_ops/labor_cost.html",
        {
            "active_tab": "service_labor",
            "active_workspace": workspace,
            "labor_entries": labor_entries[:100],
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "total_cost": total_cost,
            "entry_count": len(labor_entries),
        },
    )
