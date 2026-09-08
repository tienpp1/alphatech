"""
UI Views for Internal Notification Center (/noibo/thong-bao/).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages

from apps.notifications.models import Notification, NotificationEventType
from apps.notifications.services import (
    get_unread_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_user_authorized_workspaces,
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
