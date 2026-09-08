"""
Web UI Views for Business Recommendations (Phase 10).
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.recommendations.models import Recommendation, RecommendationStatus
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations


@login_required
def recommendations_dashboard_view(request):
    workspace = resolve_authorized_ui_workspace(request, None, "recommendations.view_recommendation")

    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")

    qs = Recommendation.objects.for_workspace(workspace)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    can_manage = has_workspace_permission(request.user, workspace, "recommendations.manage_recommendation") or request.user.is_superuser

    context = {
        "active_workspace": workspace,
        "recommendations": qs,
        "selected_status": status_filter,
        "selected_priority": priority_filter,
        "can_manage": can_manage,
        "total_count": qs.count(),
        "pending_count": Recommendation.objects.for_workspace(workspace).filter(status=RecommendationStatus.PENDING).count(),
    }
    return render(request, "recommendations/index.html", context)
