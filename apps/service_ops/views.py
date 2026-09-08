"""
apps.service_ops.views - REST API Endpoints for Service Operations.
All endpoints adhere to docs/api-conventions.md JSON envelope format.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import dateparse

from apps.accounts.services import has_workspace_permission
from apps.workspaces.permissions import IsWorkspaceMember
from apps.service_ops.models import (
    Service,
    Employee,
    SLA,
    ServiceRequest,
    ServiceRequestStatus,
    Task,
    TaskStatus,
    Schedule,
    LaborEntry,
)
from apps.service_ops.serializers import (
    ServiceSerializer,
    EmployeeSerializer,
    SLASerializer,
    ServiceRequestSerializer,
    TaskSerializer,
    ScheduleSerializer,
    LaborEntrySerializer,
)
from apps.service_ops.services import (
    create_service,
    update_service,
    delete_service,
    create_employee,
    update_employee,
    create_sla_policy,
    create_service_request,
    assign_service_request,
    transition_service_request_status,
    create_task,
    transition_task_status,
    create_schedule,
    create_labor_entry,
    get_service_request_cost_breakdown,
)
from apps.service_ops.selectors import (
    get_service_dashboard_summary,
    get_technicians_workload_breakdown,
    get_requests_by_status_breakdown,
    get_requests_by_priority_breakdown,
    get_requests_by_category_breakdown,
)
from apps.service_ops.filters import (
    filter_services,
    filter_employees,
    filter_service_requests,
    filter_tasks,
    filter_schedules,
    filter_labor_entries,
)


def api_success(data=None, count=None, status_code=status.HTTP_200_OK):
    res = {"success": True}
    if count is not None:
        res["count"] = count
    if data is not None:
        res["data"] = data
    return Response(res, status=status_code)


def api_error(message: str, code: str = "ERROR", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": errors or [],
            },
        },
        status=status_code,
    )


def check_permission(request, perm_codename: str) -> bool:
    """Verifies that the caller possesses the specified workspace-scoped RBAC permission."""
    if not request.user or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    ws = getattr(request, "active_workspace", None)
    if not ws:
        return False
    return has_workspace_permission(request.user, ws, perm_codename)


# ==========================================
# Service Catalog Endpoints
# ==========================================

class ServiceListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Service.objects.filter(workspace=request.active_workspace)
        qs = filter_services(qs, request.query_params)
        serializer = ServiceSerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.manage_service"):
            return api_error("Permission denied: service.manage_service required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        try:
            service = create_service(request.active_workspace, request.user, request.data)
            serializer = ServiceSerializer(service)
            return api_success(data=serializer.data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk, workspace=request.active_workspace)
        serializer = ServiceSerializer(service)
        return api_success(data=serializer.data)

    def patch(self, request, pk):
        if not check_permission(request, "service.manage_service"):
            return api_error("Permission denied", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        service = get_object_or_404(Service, pk=pk, workspace=request.active_workspace)
        try:
            service = update_service(service, request.user, request.data)
            return api_success(data=ServiceSerializer(service).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")

    def delete(self, request, pk):
        if not check_permission(request, "service.manage_service"):
            return api_error("Permission denied", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        service = get_object_or_404(Service, pk=pk, workspace=request.active_workspace)
        try:
            delete_service(service, request.user)
            return api_success(data={"message": "Service deleted successfully"})
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# Employee / Technician Endpoints
# ==========================================

class EmployeeListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Employee.objects.filter(workspace=request.active_workspace)
        qs = filter_employees(qs, request.query_params)
        serializer = EmployeeSerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.manage_employee"):
            return api_error("Permission denied: service.manage_employee required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        try:
            emp = create_employee(request.active_workspace, request.user, request.data)
            return api_success(data=EmployeeSerializer(emp).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class EmployeeDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        emp = get_object_or_404(Employee, pk=pk, workspace=request.active_workspace)
        return api_success(data=EmployeeSerializer(emp).data)

    def patch(self, request, pk):
        if not check_permission(request, "service.manage_employee"):
            return api_error("Permission denied", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        emp = get_object_or_404(Employee, pk=pk, workspace=request.active_workspace)
        try:
            emp = update_employee(emp, request.user, request.data)
            return api_success(data=EmployeeSerializer(emp).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# SLA Policy Endpoints
# ==========================================

class SLAListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = SLA.objects.filter(workspace=request.active_workspace)
        serializer = SLASerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.manage_sla"):
            return api_error("Permission denied: service.manage_sla required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        try:
            sla = create_sla_policy(request.active_workspace, request.user, request.data)
            return api_success(data=SLASerializer(sla).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# Service Request (Ticket) Endpoints
# ==========================================

class ServiceRequestListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = ServiceRequest.objects.filter(workspace=request.active_workspace).select_related(
            "customer", "service", "sla", "assigned_employee"
        ).prefetch_related("tasks__assigned_to", "tasks__labor_entries__employee")
        qs = filter_service_requests(qs, request.query_params)
        serializer = ServiceRequestSerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.create_request"):
            return api_error("Permission denied: service.create_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        try:
            req = create_service_request(request.active_workspace, request.user, request.data)
            return api_success(data=ServiceRequestSerializer(req).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceRequestDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        req = get_object_or_404(
            ServiceRequest.objects.select_related("customer", "service", "sla", "assigned_employee").prefetch_related("tasks__assigned_to", "tasks__labor_entries__employee"),
            pk=pk,
            workspace=request.active_workspace,
        )
        return api_success(data=ServiceRequestSerializer(req).data)


class ServiceRequestCostAPIView(APIView):
    """
    Returns aggregated labor time, hourly rate snapshots, and labor cost summary for a ticket.
    """
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        cost_data = get_service_request_cost_breakdown(req)
        return api_success(data=cost_data)


class ServiceRequestAssignAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.assign_request"):
            return api_error("Permission denied: service.assign_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        employee_id = request.data.get("employee_id")
        if not employee_id:
            return api_error("employee_id is required", code="MISSING_PARAM")

        emp = get_object_or_404(Employee, pk=employee_id, workspace=request.active_workspace)
        try:
            req = assign_service_request(req, emp, request.user, scheduled_at=request.data.get("scheduled_at"))
            return api_success(data=ServiceRequestSerializer(req).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceRequestStartAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_request"):
            return api_error("Permission denied: service.manage_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        try:
            req = transition_service_request_status(req, ServiceRequestStatus.IN_PROGRESS, request.user)
            return api_success(data=ServiceRequestSerializer(req).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceRequestResolveAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_request"):
            return api_error("Permission denied: service.manage_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        try:
            req = transition_service_request_status(req, ServiceRequestStatus.RESOLVED, request.user)
            return api_success(data=ServiceRequestSerializer(req).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceRequestCloseAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_request"):
            return api_error("Permission denied: service.manage_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        try:
            req = transition_service_request_status(req, ServiceRequestStatus.CLOSED, request.user)
            return api_success(data=ServiceRequestSerializer(req).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ServiceRequestCancelAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_request"):
            return api_error("Permission denied: service.manage_request required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        req = get_object_or_404(ServiceRequest, pk=pk, workspace=request.active_workspace)
        try:
            req = transition_service_request_status(req, ServiceRequestStatus.CANCELLED, request.user)
            return api_success(data=ServiceRequestSerializer(req).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# Task Endpoints
# ==========================================

class TaskListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Task.objects.filter(service_request__workspace=request.active_workspace).select_related("assigned_to", "service_request").prefetch_related("labor_entries__employee")
        qs = filter_tasks(qs, request.query_params)
        serializer = TaskSerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.manage_task"):
            return api_error("Permission denied", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        request_id = request.data.get("service_request_id")
        req = get_object_or_404(ServiceRequest, pk=request_id, workspace=request.active_workspace)
        try:
            task = create_task(req, request.user, request.data)
            return api_success(data=TaskSerializer(task).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class TaskDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk, service_request__workspace=request.active_workspace)
        return api_success(data=TaskSerializer(task).data)


class TaskStartAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_task"):
            return api_error("Permission denied: service.manage_task required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        task = get_object_or_404(Task, pk=pk, service_request__workspace=request.active_workspace)
        try:
            task = transition_task_status(task, TaskStatus.IN_PROGRESS, request.user)
            return api_success(data=TaskSerializer(task).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class TaskCompleteAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_task"):
            return api_error("Permission denied: service.manage_task required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        task = get_object_or_404(Task, pk=pk, service_request__workspace=request.active_workspace)
        actual_duration = request.data.get("actual_duration_minutes")
        try:
            task = transition_task_status(task, TaskStatus.COMPLETED, request.user, actual_duration_minutes=actual_duration)
            return api_success(data=TaskSerializer(task).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class TaskCancelAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "service.manage_task"):
            return api_error("Permission denied: service.manage_task required", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        task = get_object_or_404(Task, pk=pk, service_request__workspace=request.active_workspace)
        try:
            task = transition_task_status(task, TaskStatus.CANCELLED, request.user)
            return api_success(data=TaskSerializer(task).data)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# Labor Time Tracking Endpoints
# ==========================================

class LaborEntryListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = LaborEntry.objects.filter(task__service_request__workspace=request.active_workspace).select_related("employee", "task__service_request")
        qs = filter_labor_entries(qs, request.query_params)
        serializer = LaborEntrySerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        task_id = request.data.get("task_id")
        employee_id = request.data.get("employee_id")

        if not task_id or not employee_id:
            return api_error("task_id and employee_id are required.", code="MISSING_PARAM")

        task = get_object_or_404(Task, pk=task_id, service_request__workspace=request.active_workspace)
        emp = get_object_or_404(Employee, pk=employee_id, workspace=request.active_workspace)

        # RBAC: Technician can log labor for self, or manager/admin can log for any
        user_emp = (
            request.user.employee_profile.filter(workspace=request.active_workspace).first()
            if hasattr(request.user, "employee_profile")
            else None
        )
        is_manager = check_permission(request, "service.manage_task") or check_permission(request, "service.manage_employee")

        if not is_manager and (not user_emp or user_emp.id != emp.id):
            return api_error("Technicians may only log labor entries for themselves.", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        # Parse timestamps
        started_at = request.data.get("started_at")
        ended_at = request.data.get("ended_at")
        if isinstance(started_at, str):
            started_at = dateparse.parse_datetime(started_at)
        if isinstance(ended_at, str):
            ended_at = dateparse.parse_datetime(ended_at)

        payload = {
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_minutes": request.data.get("duration_minutes"),
            "notes": request.data.get("notes", ""),
        }

        try:
            labor = create_labor_entry(task, emp, request.user, payload)
            return api_success(data=LaborEntrySerializer(labor).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class TaskLaborListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id, service_request__workspace=request.active_workspace)
        entries = task.labor_entries.select_related("employee").order_by("-started_at")
        return api_success(data=LaborEntrySerializer(entries, many=True).data, count=entries.count())

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id, service_request__workspace=request.active_workspace)
        employee_id = request.data.get("employee_id") or (task.assigned_to.id if task.assigned_to else None)
        if not employee_id:
            return api_error("employee_id is required", code="MISSING_PARAM")

        emp = get_object_or_404(Employee, pk=employee_id, workspace=request.active_workspace)

        user_emp = (
            request.user.employee_profile.filter(workspace=request.active_workspace).first()
            if hasattr(request.user, "employee_profile")
            else None
        )
        is_manager = check_permission(request, "service.manage_task") or check_permission(
            request, "service.manage_employee"
        )
        if not is_manager and (not user_emp or user_emp.id != emp.id):
            return api_error("Technicians may only log labor entries for themselves.", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        started_at = request.data.get("started_at")
        ended_at = request.data.get("ended_at")
        if isinstance(started_at, str):
            started_at = dateparse.parse_datetime(started_at)
        if isinstance(ended_at, str):
            ended_at = dateparse.parse_datetime(ended_at)

        payload = {
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_minutes": request.data.get("duration_minutes"),
            "notes": request.data.get("notes", ""),
        }

        try:
            labor = create_labor_entry(task, emp, request.user, payload)
            return api_success(data=LaborEntrySerializer(labor).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


# ==========================================
# Schedule Endpoints
# ==========================================

class ScheduleListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Schedule.objects.filter(task__service_request__workspace=request.active_workspace).select_related("employee", "task")
        qs = filter_schedules(qs, request.query_params)
        serializer = ScheduleSerializer(qs, many=True)
        return api_success(data=serializer.data, count=qs.count())

    def post(self, request):
        if not check_permission(request, "service.manage_schedule"):
            return api_error("Permission denied", code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

        task_id = request.data.get("task_id")
        emp_id = request.data.get("employee_id")
        task = get_object_or_404(Task, pk=task_id, service_request__workspace=request.active_workspace)
        emp = get_object_or_404(Employee, pk=emp_id, workspace=request.active_workspace)

        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        if isinstance(start_time, str):
            start_time = dateparse.parse_datetime(start_time)
        if isinstance(end_time, str):
            end_time = dateparse.parse_datetime(end_time)

        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "status": request.data.get("status"),
            "notes": request.data.get("notes", ""),
        }

        try:
            schedule = create_schedule(task, emp, request.user, payload)
            return api_success(data=ScheduleSerializer(schedule).data, status_code=status.HTTP_201_CREATED)
        except ValidationError as e:
            return api_error(str(e.message if hasattr(e, "message") else e), code="VALIDATION_ERROR")


class ScheduleDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        sch = get_object_or_404(Schedule, pk=pk, task__service_request__workspace=request.active_workspace)
        return api_success(data=ScheduleSerializer(sch).data)


# ==========================================
# Analytics & Workload Endpoints
# ==========================================

class AnalyticsOverviewAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        summary = get_service_dashboard_summary(request.active_workspace)
        return api_success(data=summary)


class AnalyticsWorkloadAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        breakdown = get_technicians_workload_breakdown(request.active_workspace)
        return api_success(data=breakdown, count=len(breakdown))


class AnalyticsSLAAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        summary = get_service_dashboard_summary(request.active_workspace)
        sla_data = {
            "on_time_count": summary["on_time_sla_count"],
            "at_risk_count": summary["at_risk_sla_count"],
            "breached_count": summary["breached_sla_count"],
            "compliance_rate": summary["sla_compliance_rate"],
        }
        return api_success(data=sla_data)
