"""
Web UI Views for Predictive Analytics & Forecasting Dashboard.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.workspaces.models import WorkspaceType
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    TargetType,
    RunStatus,
)
from apps.forecasting.services import (
    get_forecast_chart_data,
    get_default_target_for_workspace,
    get_or_create_default_config,
)


@login_required
def forecasting_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the predictive analytics studio with interactive time-series forecast charts,
    baseline performance benchmarking, feature importance scores, and training history.
    """
    workspace = resolve_authorized_ui_workspace(request, None, "forecasting.view_forecast")
    role = getattr(request, "active_membership", None)

    ws_type = getattr(workspace, "workspace_type", "")
    if ws_type == WorkspaceType.SERVICE:
        available_targets = [
            {"code": TargetType.SERVICE_TICKET_VOLUME, "label": "🎫 Service Ticket Volume"},
        ]
    else:
        available_targets = [
            {"code": TargetType.RETAIL_REVENUE, "label": "💰 Retail Daily Revenue"},
            {"code": TargetType.RETAIL_ORDER_VOLUME, "label": "📦 Retail Order Volume"},
            {"code": TargetType.RETAIL_PRODUCT_DEMAND, "label": "Nhu cầu sản phẩm bán lẻ"},
        ]

    # Selected target type from query param or default
    default_target = available_targets[0]["code"]
    selected_target = request.GET.get("target", default_target)
    # Ensure selected_target is valid for workspace
    valid_codes = [t["code"] for t in available_targets]
    if selected_target not in valid_codes:
        selected_target = default_target

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "forecasting.manage_forecast")
    # Creating defaults is a mutation and must not happen for read-only users.
    if can_manage:
        get_or_create_default_config(workspace, selected_target)

    # Fetch configs and recent runs
    configs = ForecastModelConfig.objects.for_workspace(workspace).filter(target_type=selected_target)
    runs = ForecastRun.objects.for_workspace(workspace).filter(target_type=selected_target).order_by("-created_at")[:10]

    # Chart data
    try:
        chart_data = get_forecast_chart_data(workspace, target_type=selected_target)
    except Exception as e:
        chart_data = {
            "error": str(e),
            "historical": [],
            "forecast": [],
            "metrics": {},
            "baseline_metrics": {},
            "feature_importances": [],
        }

    context = {
        "active_nav": "forecasting",
        "active_workspace": workspace,
        "active_role": role,
        "available_targets": available_targets,
        "selected_target": selected_target,
        "configs": configs,
        "runs": runs,
        "chart_data": chart_data,
        "can_manage": can_manage,
    }
    return render(request, "forecasting/index.html", context)
