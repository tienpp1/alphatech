"""
Business service layer for Workspace Team Chat (Kênh Trao đổi Nội bộ Nhân sự).
Enforces tenant isolation, active workspace membership, and incremental message synchronization.
"""

from typing import List, Optional, Tuple
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.notifications.models import TeamChatMessage
from apps.workspaces.models import Workspace, WorkspaceMembership


def verify_chat_access(user, workspace: Workspace) -> bool:
    """
    Ensures user is an authenticated internal staff member with active membership in the workspace.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    return WorkspaceMembership.objects.filter(
        user=user,
        workspace=workspace,
        is_active=True,
    ).exists()


def send_team_message(
    workspace: Workspace,
    sender,
    message: str,
    attachment_name: str = "",
) -> TeamChatMessage:
    """
    Sends a team chat message within a workspace.
    Raises PermissionDenied if the sender has no active membership in the workspace.
    """
    if not verify_chat_access(sender, workspace):
        raise PermissionDenied("Bạn không có quyền gửi tin nhắn trong không gian làm việc này.")

    clean_msg = message.strip()
    if not clean_msg:
        raise ValueError("Nội dung tin nhắn không được để trống.")

    msg = TeamChatMessage.objects.create(
        workspace=workspace,
        sender=sender,
        message=clean_msg,
        attachment_name=attachment_name.strip(),
    )
    return msg


def get_recent_team_messages(
    workspace: Workspace,
    user=None,
    limit: int = 50,
    since_id: Optional[int] = None,
) -> List[TeamChatMessage]:
    """
    Retrieves chronological messages for the workspace.
    If since_id is provided, returns only messages newer than since_id (for live polling).
    Raises PermissionDenied if a user is supplied and has no active membership in the workspace.
    """
    if user is not None and not verify_chat_access(user, workspace):
        raise PermissionDenied("Bạn không có quyền truy cập kênh trao đổi của không gian làm việc này.")

    qs = TeamChatMessage.objects.filter(workspace=workspace).select_related("sender")

    if since_id:
        return list(qs.filter(id__gt=since_id).order_by("created_at")[:limit])

    # Default initial load: get latest `limit` messages in chronological order in 1 query
    messages = list(qs.order_by("-created_at")[:limit])
    messages.reverse()
    return messages


def get_workspace_colleagues(workspace: Workspace) -> List[dict]:
    """
    Returns the list of active team members in this workspace with their roles.
    """
    memberships = (
        WorkspaceMembership.objects.filter(workspace=workspace, is_active=True)
        .select_related("user", "role")
        .order_by("role__name", "user__username")
    )
    results = []
    for m in memberships:
        results.append({
            "user": m.user,
            "user_id": m.user.id,
            "username": m.user.username,
            "full_name": m.user.get_full_name() or m.user.username,
            "role": m.role.name if m.role else "",
            "is_staff": m.user.is_staff,
        })
    return results
