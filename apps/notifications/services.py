"""
Service layer for Internal Notification Center.
Handles notification creation, role-based distribution, deduplication, and lifecycle operations.
"""

from typing import List, Optional, Any
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.notifications.models import Notification, NotificationEventType
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


def create_notification(
    workspace: Workspace,
    recipient: Any,
    event_type: str,
    title: str,
    message: str,
    entity_type: str = "",
    entity_id: str = "",
    target_url: str = "",
) -> Optional[Notification]:
    """
    Creates a notification for an individual recipient inside a workspace.
    Enforces deduplication: will not create duplicate notifications for the same
    (workspace, recipient, event_type, entity_type, entity_id).
    """
    if not workspace or not recipient:
        return None

    # Deduplication check
    if entity_type and entity_id:
        existing = Notification.objects.filter(
            workspace=workspace,
            recipient=recipient,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
        ).first()
        if existing:
            return existing

    return Notification.objects.create(
        workspace=workspace,
        recipient=recipient,
        event_type=event_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=str(entity_id),
        target_url=target_url,
    )


def get_user_authorized_workspaces(user: Any):
    """
    Returns active Workspaces that the user is authorized to administer or access.
    Superusers have access across all active workspaces.
    Standard internal staff access workspaces where they hold an active membership.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return Workspace.objects.none()

    if user.is_superuser:
        return Workspace.objects.filter(is_active=True)

    return Workspace.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        is_active=True,
    ).distinct()


def notify_workspace_roles(
    workspace: Workspace,
    roles: List[str],
    event_type: str,
    title: str,
    message: str,
    entity_type: str = "",
    entity_id: str = "",
    target_url: str = "",
) -> List[Notification]:
    """
    Distributes notifications to active members of the specified workspace
    holding any of the authorized roles (e.g. ADMIN, MANAGER, EMPLOYEE),
    as well as active platform superusers who oversee operations.
    """
    if not workspace:
        return []

    # Query active members with the matching roles (case-insensitive)
    upper_roles = [r.upper() for r in roles]
    memberships = (
        WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True,
            user__is_active=True,
            role__name__in=upper_roles,
        )
        .select_related("user")
        .distinct()
    )

    recipients = {m.user for m in memberships}

    # Also notify active superusers who have platform administrator privileges
    if "ADMIN" in upper_roles:
        from apps.accounts.models import User
        superusers = User.objects.filter(is_superuser=True, is_active=True)
        recipients.update(superusers)

    created_notifications = []
    for user in recipients:
        notif = create_notification(
            workspace=workspace,
            recipient=user,
            event_type=event_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            target_url=target_url,
        )
        if notif:
            created_notifications.append(notif)

    return created_notifications


# =========================================================================
# DOMAIN EVENT DISPATCHERS
# =========================================================================

def dispatch_new_customer_notification(customer) -> List[Notification]:
    """
    Event: New customer registration (PUBLIC WEBSITE).
    Recipients: ADMIN, MANAGER of Retail workspace.
    """
    if not customer:
        return []

    workspace = customer.workspace or Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first()
    if not workspace:
        return []

    return notify_workspace_roles(
        workspace=workspace,
        roles=["ADMIN", "MANAGER"],
        event_type=NotificationEventType.NEW_CUSTOMER,
        title="Khách hàng mới đăng ký",
        message=f"Khách hàng {customer.name} vừa tạo tài khoản.",
        entity_type="Customer",
        entity_id=str(customer.id),
        target_url="/noibo/retail/customers/",
    )


def dispatch_new_order_notification(order) -> List[Notification]:
    """
    Event: New retail order placed (PUBLIC CHECKOUT).
    Recipients: ADMIN, MANAGER, EMPLOYEE of Retail workspace.
    """
    if not order:
        return []

    workspace = order.workspace or Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first()
    if not workspace:
        return []

    amount_str = f"{order.total_amount:,.0f} ₫".replace(",", ".")

    return notify_workspace_roles(
        workspace=workspace,
        roles=["ADMIN", "MANAGER", "EMPLOYEE"],
        event_type=NotificationEventType.NEW_ORDER,
        title="Đơn hàng mới",
        message=f"Có đơn hàng mới #{order.order_number} trị giá {amount_str}.",
        entity_type="Order",
        entity_id=str(order.id),
        target_url=f"/noibo/retail/orders/{order.id}/",
    )


def dispatch_new_service_request_notification(service_request) -> List[Notification]:
    """
    Event: New service request / ticket submitted (PUBLIC WEBSITE).
    Recipients: ADMIN, MANAGER, EMPLOYEE of Service workspace.
    """
    if not service_request:
        return []

    workspace = service_request.workspace or Workspace.objects.filter(workspace_type=WorkspaceType.SERVICE).first()
    if not workspace:
        return []

    return notify_workspace_roles(
        workspace=workspace,
        roles=["ADMIN", "MANAGER", "EMPLOYEE"],
        event_type=NotificationEventType.NEW_SERVICE_REQUEST,
        title="Yêu cầu dịch vụ mới",
        message=f"Có yêu cầu dịch vụ mới: {service_request.title}.",
        entity_type="ServiceRequest",
        entity_id=str(service_request.id),
        target_url=f"/noibo/services/requests/{service_request.id}/",
    )


def dispatch_new_contact_notification(
    workspace: Optional[Workspace] = None,
    name: str = "",
    phone: str = "",
    email: str = "",
    contact_id: str = "",
) -> List[Notification]:
    """
    Event: New public contact form submitted.
    Recipients: ADMIN, MANAGER of Retail workspace.
    """
    target_workspace = workspace or Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
    if not target_workspace:
        return []

    today_str = timezone.now().strftime("%Y%m%d%H")
    eid = contact_id or f"{name}_{phone}_{today_str}"

    return notify_workspace_roles(
        workspace=target_workspace,
        roles=["ADMIN", "MANAGER"],
        event_type=NotificationEventType.NEW_CONTACT,
        title="Có liên hệ mới",
        message=f"Website vừa nhận được một yêu cầu liên hệ mới từ {name} ({phone}).",
        entity_type="Contact",
        entity_id=eid,
        target_url="/noibo/",
    )


# =========================================================================
# NOTIFICATION OPERATIONS & QUERIES
# =========================================================================

def get_unread_count(user: Any, workspace: Optional[Workspace] = None) -> int:
    """
    Returns unread notifications count for CURRENT user.
    If workspace is provided, filters by that workspace.
    Otherwise, aggregates across ALL authorized workspaces for the user.
    Uses efficient SQL COUNT.
    """
    if not user or not user.is_authenticated:
        return 0

    if workspace:
        return Notification.objects.filter(
            recipient=user,
            workspace=workspace,
            is_read=False,
        ).count()

    authorized_workspaces = get_user_authorized_workspaces(user)
    return Notification.objects.filter(
        recipient=user,
        workspace__in=authorized_workspaces,
        is_read=False,
    ).count()


def mark_notification_as_read(
    notification_id: int,
    user: Any,
    workspace: Optional[Workspace] = None,
) -> Notification:
    """
    Marks an individual notification as read.
    Enforces strict ownership & workspace boundary (raises 404 if not authorized).
    """
    if workspace:
        notif = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=user,
            workspace=workspace,
        )
    else:
        authorized_workspaces = get_user_authorized_workspaces(user)
        notif = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=user,
            workspace__in=authorized_workspaces,
        )

    notif.mark_as_read()
    return notif


def mark_all_notifications_as_read(user: Any, workspace: Optional[Workspace] = None) -> int:
    """
    Marks all unread notifications as read for CURRENT user across authorized workspaces.
    Returns the count of updated rows.
    """
    if not user or not user.is_authenticated:
        return 0

    if workspace:
        return Notification.objects.filter(
            recipient=user,
            workspace=workspace,
            is_read=False,
        ).update(
            is_read=True,
            read_at=timezone.now(),
        )

    authorized_workspaces = get_user_authorized_workspaces(user)
    return Notification.objects.filter(
        recipient=user,
        workspace__in=authorized_workspaces,
        is_read=False,
    ).update(
        is_read=True,
        read_at=timezone.now(),
    )
