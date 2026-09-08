"""
apps.service_ops.urls - REST API Routing for Service Operations Domain.
"""

from django.urls import path
from apps.service_ops import views

urlpatterns = [
    # Services Catalog
    path("services/", views.ServiceListCreateAPIView.as_view(), name="service_api_services"),
    path("services/<int:pk>/", views.ServiceDetailAPIView.as_view(), name="service_api_service_detail"),

    # Employees / Technicians
    path("employees/", views.EmployeeListCreateAPIView.as_view(), name="service_api_employees"),
    path("employees/<int:pk>/", views.EmployeeDetailAPIView.as_view(), name="service_api_employee_detail"),

    # SLA Policies
    path("slas/", views.SLAListCreateAPIView.as_view(), name="service_api_slas"),

    # Service Requests (Tickets)
    path("requests/", views.ServiceRequestListCreateAPIView.as_view(), name="service_api_requests"),
    path("requests/<int:pk>/", views.ServiceRequestDetailAPIView.as_view(), name="service_api_request_detail"),
    path("requests/<int:pk>/cost/", views.ServiceRequestCostAPIView.as_view(), name="service_api_request_cost"),
    path("requests/<int:pk>/assign/", views.ServiceRequestAssignAPIView.as_view(), name="service_api_request_assign"),
    path("requests/<int:pk>/start/", views.ServiceRequestStartAPIView.as_view(), name="service_api_request_start"),
    path("requests/<int:pk>/resolve/", views.ServiceRequestResolveAPIView.as_view(), name="service_api_request_resolve"),
    path("requests/<int:pk>/close/", views.ServiceRequestCloseAPIView.as_view(), name="service_api_request_close"),
    path("requests/<int:pk>/cancel/", views.ServiceRequestCancelAPIView.as_view(), name="service_api_request_cancel"),

    # Tasks
    path("tasks/", views.TaskListCreateAPIView.as_view(), name="service_api_tasks"),
    path("tasks/<int:pk>/", views.TaskDetailAPIView.as_view(), name="service_api_task_detail"),
    path("tasks/<int:pk>/start/", views.TaskStartAPIView.as_view(), name="service_api_task_start"),
    path("tasks/<int:pk>/complete/", views.TaskCompleteAPIView.as_view(), name="service_api_task_complete"),
    path("tasks/<int:pk>/cancel/", views.TaskCancelAPIView.as_view(), name="service_api_task_cancel"),
    path("tasks/<int:task_id>/labor/", views.TaskLaborListCreateAPIView.as_view(), name="service_api_task_labor"),

    # Labor Entries
    path("labor-entries/", views.LaborEntryListCreateAPIView.as_view(), name="service_api_labor_entries"),

    # Schedules
    path("schedules/", views.ScheduleListCreateAPIView.as_view(), name="service_api_schedules"),
    path("schedules/<int:pk>/", views.ScheduleDetailAPIView.as_view(), name="service_api_schedule_detail"),

    # Analytics & Workload
    path("analytics/overview/", views.AnalyticsOverviewAPIView.as_view(), name="service_api_analytics_overview"),
    path("analytics/workload/", views.AnalyticsWorkloadAPIView.as_view(), name="service_api_analytics_workload"),
    path("analytics/sla/", views.AnalyticsSLAAPIView.as_view(), name="service_api_analytics_sla"),
]
