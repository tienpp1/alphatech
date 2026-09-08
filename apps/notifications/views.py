"""
REST API endpoints for Internal Notifications.
Enforces authentication, internal role access, and multi-tenant workspace isolation.
"""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from apps.notifications.models import Notification
from apps.notifications.services import (
    get_unread_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_user_authorized_workspaces,
)
from apps.workspaces.models import Workspace, WorkspaceMembership


def _format_time_ago(dt) -> str:
    """Formats a datetime into a friendly Vietnamese relative time string."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "vừa xong"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} phút trước"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} giờ trước"
    days = hours // 24
    if days < 30:
        return f"{days} ngày trước"
    return dt.strftime("%d/%m/%Y")


def _verify_internal_user(request):
    """
    Ensures user is an authenticated internal staff member.
    Rejects public customers and unauthenticated requests.
    """
    if not request.user.is_authenticated:
        return False, JsonResponse({"error": "Yêu cầu đăng nhập."}, status=401)

    if request.user.is_superuser:
        return True, None

    has_membership = WorkspaceMembership.objects.filter(
        user=request.user,
        is_active=True,
    ).exists()

    if not has_membership:
        return False, JsonResponse({"error": "Không có quyền truy cập thông báo nội bộ."}, status=403)

    return True, None


@login_required(login_url="/accounts/login/")
@require_http_methods(["GET"])
def notification_unread_count_api(request):
    """
    GET /api/v1/notifications/unread-count/
    Returns aggregate unread count for current authenticated internal user across ALL authorized workspaces.
    Optionally accepts ?workspace_id= to filter by a specific workspace.
    """
    valid, err_resp = _verify_internal_user(request)
    if not valid:
        return err_resp

    target_workspace = None
    ws_id = request.GET.get("workspace_id")
    if ws_id:
        target_workspace = Workspace.objects.filter(id=ws_id, is_active=True).first()

    count = get_unread_count(request.user, workspace=target_workspace)
    return JsonResponse({
        "status": "success",
        "unread_count": count,
    })


@login_required(login_url="/accounts/login/")
@require_http_methods(["GET"])
def notification_latest_api(request):
    """
    GET /api/v1/notifications/latest/
    Returns the 5 most recent notifications for the bell dropdown across all authorized workspaces.
    """
    valid, err_resp = _verify_internal_user(request)
    if not valid:
        return err_resp

    authorized_workspaces = get_user_authorized_workspaces(request.user)
    if not authorized_workspaces.exists():
        return JsonResponse({"status": "success", "notifications": [], "unread_count": 0})

    notifications = (
        Notification.objects.filter(
            recipient=request.user,
            workspace__in=authorized_workspaces,
        )
        .select_related("workspace")
        .order_by("-created_at")[:5]
    )

    items = []
    for notif in notifications:
        items.append({
            "id": notif.id,
            "event_type": notif.event_type,
            "event_label": notif.get_event_type_display(),
            "event_icon": notif.event_icon,
            "workspace_name": notif.workspace.name,
            "workspace_code": notif.workspace.code,
            "title": notif.title,
            "message": notif.message,
            "is_read": notif.is_read,
            "time_ago": _format_time_ago(notif.created_at),
            "target_url": notif.target_url or f"/noibo/thong-bao/{notif.id}/",
            "created_at": notif.created_at.isoformat(),
        })

    unread_count = get_unread_count(request.user)

    return JsonResponse({
        "status": "success",
        "notifications": items,
        "unread_count": unread_count,
    })


@login_required(login_url="/accounts/login/")
@require_http_methods(["POST"])
def notification_mark_read_api(request, pk):
    """
    POST /api/v1/notifications/<int:pk>/read/
    Marks an individual notification as read within user's authorized workspaces.
    """
    valid, err_resp = _verify_internal_user(request)
    if not valid:
        return err_resp

    notif = mark_notification_as_read(pk, request.user)
    new_count = get_unread_count(request.user)

    return JsonResponse({
        "status": "success",
        "message": "Đã đánh dấu thông báo là đã đọc.",
        "id": notif.id,
        "is_read": True,
        "unread_count": new_count,
    })


@login_required(login_url="/accounts/login/")
@require_http_methods(["POST"])
def notification_mark_all_read_api(request):
    """
    POST /api/v1/notifications/read-all/
    Marks all notifications for current user across all authorized workspaces as read.
    """
    valid, err_resp = _verify_internal_user(request)
    if not valid:
        return err_resp

    marked_count = mark_all_notifications_as_read(request.user)

    return JsonResponse({
        "status": "success",
        "message": f"Đã đánh dấu {marked_count} thông báo là đã đọc.",
        "marked_count": marked_count,
        "unread_count": 0,
    })
