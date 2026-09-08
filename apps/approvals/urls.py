"""
URL configuration for Approvals & Controlled Tool Execution (Phase 10).
"""

from django.urls import path
from apps.approvals import views, ui_views

app_name = "approvals"

urlpatterns = [
    # Web UI Dashboard (Approval Center)
    path("approvals/", ui_views.approvals_dashboard_view, name="ui_dashboard"),

    # REST APIs for Approvals
    path("api/v1/approvals/", views.ApprovalRequestListAPIView.as_view(), name="api_list"),
    path("api/v1/approvals/<int:pk>/", views.ApprovalRequestDetailAPIView.as_view(), name="api_detail"),
    path("api/v1/approvals/<int:pk>/decision/", views.ApprovalRequestDecisionAPIView.as_view(), name="api_decision"),

    # REST APIs for Controlled Tools
    path("api/v1/tools/", views.ToolRegistryListAPIView.as_view(), name="api_tools_list"),
    path("api/v1/tools/<str:name>/execute/", views.ToolExecuteAPIView.as_view(), name="api_tool_execute"),
    path("api/v1/tools/execute/", views.ToolExecuteAPIView.as_view(), name="api_tool_execute_generic"),
]
