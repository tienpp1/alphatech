"""
Web UI Views for Approval Center (Phase 10).
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.review import approval_review_state, review_queue


@login_required
def approvals_dashboard_view(request):
    workspace = resolve_authorized_ui_workspace(request, None, "approvals.view_approval")

    status_filter = request.GET.get("status", "")
    risk_filter = request.GET.get("risk", "")

    qs = ApprovalRequest.objects.for_workspace(workspace).select_related("requester", "reviewer")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if risk_filter:
        qs = qs.filter(risk_level=risk_filter)

    can_approve = has_workspace_permission(request.user, workspace, "approvals.manage_approval") or request.user.is_superuser

    all_rows = review_queue(qs.select_related('workspace', 'requester', 'source_recommendation'), approval_review_state, 'all')
    queue = request.GET.get('queue', 'current')
    rows = [row for row in all_rows if queue == 'all' or (not row.review_state['current'] if queue == 'history' else row.review_state['current'])]
    for row in rows:
        row.can_review = can_approve and (row.requester_id != request.user.pk or request.user.is_superuser)
    context = {
        "active_workspace": workspace,
        "approval_requests": rows,
        "selected_queue": queue,
        "selected_status": status_filter,
        "selected_risk": risk_filter,
        "can_approve": can_approve,
        "pending_count": sum(row.review_state['current'] for row in all_rows),
        "total_count": len(rows),
    }
    return render(request, "approvals/index.html", context)
