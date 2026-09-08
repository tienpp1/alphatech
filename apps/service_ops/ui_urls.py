"""
apps.service_ops.ui_urls - Web UI Route Patterns under /services/.
"""

from django.urls import path
from apps.service_ops import ui_views

urlpatterns = [
    path("", ui_views.dashboard_view, name="services_ui_dashboard"),
    path("services/", ui_views.services_view, name="services_ui_services"),
    path("employees/", ui_views.employees_view, name="services_ui_employees"),
    path("requests/", ui_views.requests_view, name="services_ui_requests"),
    path("requests/<int:pk>/", ui_views.request_detail_view, name="services_ui_request_detail"),
    path("tasks/", ui_views.tasks_view, name="services_ui_tasks"),
    path("schedules/", ui_views.schedules_view, name="services_ui_schedules"),
    path("slas/", ui_views.slas_view, name="services_ui_slas"),
    path("labor-cost/", ui_views.labor_cost_view, name="services_ui_labor_cost"),
]

