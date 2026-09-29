"""
UI Views for Internal Notification Center (/noibo/thong-bao/).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from apps.notifications.models import Notification, NotificationEventType
from apps.notifications.services import (
    get_unread_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_user_authorized_workspaces,
    resolve_collaboration_workspace,
)
from apps.workspaces.models import WorkspaceMembership


def _ensure_internal_access(request):
    """Verifies that the user has an active internal workspace membership."""
    if request.user.is_superuser:
        return True
    return WorkspaceMembership.objects.filter(user=request.user, is_active=True).exists()


@login_required(login_url="/accounts/login/")
def notification_center_ui_view(request):
    """
    Internal Notification Center Page (GET & POST /noibo/thong-bao/).
    Displays unified paginated list of notifications across all authorized workspaces.
    """
    if not _ensure_internal_access(request):
        return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = get_user_authorized_workspaces(request.user)

    # Handle POST bulk actions from form
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "mark_all_read":
            count = mark_all_notifications_as_read(request.user)
            messages.success(request, f"Đã đánh dấu tất cả ({count}) thông báo là đã đọc.")
            return redirect("/noibo/thong-bao/")

        elif action == "mark_read":
            notif_id = request.POST.get("notification_id")
            if notif_id:
                mark_notification_as_read(notif_id, request.user)
            return redirect(request.get_full_path())

    # Build query across authorized workspaces
    qs = Notification.objects.filter(
        recipient=request.user,
        workspace__in=authorized_workspaces,
    ).select_related("workspace").order_by("-created_at")

    workspace_filter = request.GET.get("workspace_id")
    if workspace_filter:
        qs = qs.filter(workspace_id=workspace_filter)

    filter_type = request.GET.get("type", "all")
    if filter_type == "unread":
        qs = qs.filter(is_read=False)
    elif filter_type in NotificationEventType.values:
        qs = qs.filter(event_type=filter_type)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    unread_count = get_unread_count(request.user)
    total_count = Notification.objects.filter(
        recipient=request.user,
        workspace__in=authorized_workspaces,
    ).count()

    context = {
        "page_title": "Trung tâm thông báo | Quản trị Nội bộ",
        "notifications": page_obj,
        "active_tab": "notifications",
        "filter_type": filter_type,
        "selected_workspace": workspace_filter or "",
        "authorized_workspaces": authorized_workspaces,
        "unread_count": unread_count,
        "total_count": total_count,
        "event_types": NotificationEventType.choices,
        "notice": request.GET.get("notice"),
    }
    return render(request, "notifications/index.html", context)


@login_required(login_url="/accounts/login/")
def notification_redirect_detail_view(request, pk):
    """
    Direct Notification Navigation (GET /noibo/thong-bao/<pk>/).
    Marks notification as read and redirects safely to the target business entity.
    Gracefully handles cases where the target entity no longer exists.
    """
    from django.contrib import messages

    if not _ensure_internal_access(request):
        return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = get_user_authorized_workspaces(request.user)
    notif = get_object_or_404(
        Notification,
        id=pk,
        recipient=request.user,
        workspace__in=authorized_workspaces,
    )
    notif.mark_as_read()

    # Verify if related entity exists when entity_type and entity_id are defined
    entity_exists = True
    if notif.entity_type and notif.entity_id:
        try:
            if notif.entity_type == "Order":
                from apps.retail.models import Order
                entity_exists = Order.objects.filter(id=notif.entity_id).exists()
            elif notif.entity_type == "ServiceRequest":
                from apps.service_ops.models import ServiceRequest
                entity_exists = ServiceRequest.objects.filter(id=notif.entity_id).exists()
            elif notif.entity_type == "Customer":
                from apps.retail.models import Customer
                entity_exists = Customer.objects.filter(id=notif.entity_id).exists()
        except Exception:
            entity_exists = False

    if not entity_exists:
        messages.warning(
            request,
            f"Thực thể liên quan ({notif.entity_type} #{notif.entity_id}) không còn tồn tại trong hệ thống hoặc đã bị xóa."
        )
        return redirect("/noibo/thong-bao/")

    # If target_url exists, navigate safely
    if notif.target_url:
        return redirect(notif.target_url)

    return redirect("/noibo/thong-bao/")


from apps.notifications.bulletin_service import (
    get_workspace_bulletins,
    create_bulletin,
    can_manage_bulletins,
)
from apps.notifications.chat_service import (
    get_recent_team_messages,
    send_team_message,
    get_workspace_colleagues,
    verify_chat_access,
)
from apps.notifications.models import BulletinPriority
from apps.workspaces.models import Workspace


@login_required(login_url="/accounts/login/")
def bulletin_board_ui_view(request):
    """
    Internal Bulletin Board Page (GET /noibo/bang-tin/).
    Displays executive directives, policies, and pinned announcements per Workspace.
    """
    if not _ensure_internal_access(request):
        return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = get_user_authorized_workspaces(request.user)
    if not authorized_workspaces.exists():
        return render(request, "retail/no_workspace.html", {"message": "Bạn chưa được cấp quyền truy cập không gian làm việc nào."})

    target_workspace = resolve_collaboration_workspace(request, request.GET, use_session=True)
    if target_workspace is None:
        raise PermissionDenied("Không gian làm việc không hợp lệ hoặc không được cấp quyền.")

    priority_filter = request.GET.get("priority", "")
    bulletins = get_workspace_bulletins(target_workspace, priority=priority_filter or None)
    can_manage = can_manage_bulletins(request.user, target_workspace)

    context = {
        "active_workspace": target_workspace,
        "authorized_workspaces": authorized_workspaces,
        "bulletins": bulletins,
        "can_manage": can_manage,
        "priority_filter": priority_filter,
        "priority_choices": BulletinPriority.choices,
        "total_bulletins_count": len(bulletins),
    }
    return render(request, "notifications/bulletin_board.html", context)


@login_required(login_url="/accounts/login/")
def bulletin_create_ui_view(request):
    """
    POST /noibo/bang-tin/create/
    Creates a new internal bulletin within the target workspace.
    """
    if not _ensure_internal_access(request):
        return redirect("/tai-khoan/?notice=customer_only")

    if request.method != "POST":
        return redirect("/noibo/bang-tin/")

    target_workspace = resolve_collaboration_workspace(request, request.POST)

    if not target_workspace:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Không gian làm việc không hợp lệ.")

    if not can_manage_bulletins(request.user, target_workspace):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Bạn không có quyền ban hành bản tin trong không gian làm việc này.")

    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    priority = request.POST.get("priority", BulletinPriority.NORMAL)

    if not title or not content:
        messages.error(request, "Vui lòng nhập đầy đủ tiêu đề và nội dung bản tin.")
        return redirect(f"/noibo/bang-tin/?workspace_id={target_workspace.id}")

    create_bulletin(
        workspace=target_workspace,
        author=request.user,
        title=title,
        content=content,
        priority=priority,
    )
    messages.success(request, f"Đã đăng bản tin '{title}' thành công tới toàn thể nhân sự.")
    return redirect(f"/noibo/bang-tin/?workspace_id={target_workspace.id}")


@login_required(login_url="/accounts/login/")
def team_chat_ui_view(request):
    """
    Internal Team Chat Page (GET & POST /noibo/trao-doi/).
    Enables workspace-scoped real-time messaging between colleagues.
    """
    if not _ensure_internal_access(request):
        return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = get_user_authorized_workspaces(request.user)
    if not authorized_workspaces.exists():
        return render(request, "retail/no_workspace.html", {"message": "Bạn chưa được cấp quyền truy cập không gian làm việc nào."})

    target_workspace = resolve_collaboration_workspace(request, request.GET, use_session=True)
    if target_workspace is None:
        raise PermissionDenied("Không gian làm việc không hợp lệ hoặc không được cấp quyền.")

    # Verify access to this specific workspace
    if not verify_chat_access(request.user, target_workspace):
        messages.error(request, "Bạn không có quyền tham gia kênh trao đổi của không gian làm việc này.")
        return redirect("/noibo/")

    # Handle standard form POST message submission (fallback when JS disabled)
    if request.method == "POST":
        msg_text = request.POST.get("message", "").strip()
        if msg_text:
            try:
                send_team_message(target_workspace, request.user, msg_text)
                return redirect(f"/noibo/trao-doi/?workspace_id={target_workspace.id}")
            except ValueError:
                messages.error(request, "Nội dung tin nhắn không hợp lệ.")

    messages_list = get_recent_team_messages(target_workspace, request.user, limit=50)
    colleagues = get_workspace_colleagues(target_workspace)

    context = {
        "active_workspace": target_workspace,
        "authorized_workspaces": authorized_workspaces,
        "messages_list": messages_list,
        "colleagues": colleagues,
        "latest_message_id": messages_list[-1].id if messages_list else 0,
    }
    return render(request, "notifications/team_chat.html", context)
