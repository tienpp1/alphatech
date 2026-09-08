"""
Web UI Views for Approval Center (Phase 10).
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.approvals.models import ApprovalRequest, ApprovalStatus


@login_required
def approvals_dashboard_view(request):
    workspace = resolve_authorized_ui_workspace(request, None, "approvals.view_approval")

    status_filter = request.GET.get("status", "")
    risk_filter = request.GET.get("risk", "")

    qs = ApprovalRequest.objects.for_workspace(workspace)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if risk_filter:
        qs = qs.filter(risk_level=risk_filter)

    can_approve = has_workspace_permission(request.user, workspace, "approvals.manage_approval") or request.user.is_superuser

    context = {
        "active_workspace": workspace,
        "approval_requests": qs,
        "selected_status": status_filter,
        "selected_risk": risk_filter,
        "can_approve": can_approve,
        "pending_count": ApprovalRequest.objects.for_workspace(workspace).filter(status=ApprovalStatus.PENDING).count(),
        "total_count": qs.count(),
    }
    return render(request, "approvals/index.html", context)
