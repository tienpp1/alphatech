"""
Web UI Views for Workspace Operations (Switching Tenant Context).
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.workspaces.services import switch_workspace
from apps.workspaces.models import Workspace, WorkspaceType


@login_required
def switch_workspace_ui_view(request, workspace_id):
    """
    Switch active tenant context from Web UI and redirect to the corresponding domain dashboard.
    """
    try:
        workspace, _ = switch_workspace(
            user=request.user,
            workspace_id=workspace_id,
            request=request,
        )
        messages.success(request, f"Đã chuyển sang không gian làm việc: {workspace.name}")
        if workspace.workspace_type == WorkspaceType.SERVICE:
            return redirect("services_ui_dashboard")
        return redirect("retail_ui_dashboard")
    except PermissionDenied as e:
        messages.error(request, f"Không có quyền truy cập không gian làm việc này: {e}")
        return redirect("health_check_ui")
