"""
Service layer for Internal Notification Center.
Handles notification creation, role-based distribution, deduplication, and lifecycle operations.
"""

from typing import List, Optional, Any
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from apps.notifications.models import Notification, NotificationEventType
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


def resolve_collaboration_workspace(request, parameters, *, use_session=False):
    """Resolve a collaboration selector; explicit invalid input never falls back.

    Reuse active-membership scoping and the middleware's canonical header result.
    Absence retains the existing authorized default behavior, not a global lookup.
    """
    from apps.workspaces.services import get_explicit_workspace_selector

    allowed = get_user_authorized_workspaces(request.user)

    def lookup(value):
        if not value:
            return None
        try:
            return allowed.filter(pk=value).first()
        except (ValidationError, ValueError, TypeError):
            return None

    if getattr(request, 'workspace_access_denied', False):
        return None
    header, _ = get_explicit_workspace_selector(request)
    if header:
        active = getattr(request, 'active_workspace', None)
        workspace = lookup(active.pk) if active else None
        if 'workspace_id' in parameters:
            selected = lookup(parameters.get('workspace_id'))
            if not selected or not workspace or selected.pk != workspace.pk:
                return None
        return workspace
    if 'workspace_id' in parameters:
        return lookup(parameters.get('workspace_id'))
    if use_session:
        workspace = lookup(request.session.get('active_workspace_id'))
        if workspace:
            return workspace
    return allowed.first()


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

    notif = Notification.objects.create(
        workspace=workspace,
        recipient=recipient,
        event_type=event_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=str(entity_id),
        target_url=target_url,
    )
    if hasattr(recipient, "_cached_unread_counts"):
        recipient._cached_unread_counts.clear()
    return notif


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
    Uses in-memory per-instance memoization on `user` to avoid redundant COUNT queries during request rendering.
    """
    if not user or not user.is_authenticated:
        return 0

    ws_key = str(getattr(workspace, "id", workspace)) if workspace else "all"

    if not hasattr(user, "_cached_unread_counts"):
        user._cached_unread_counts = {}

    if ws_key in user._cached_unread_counts:
        return user._cached_unread_counts[ws_key]

    if workspace:
        count = Notification.objects.filter(
            recipient=user,
            workspace=workspace,
            is_read=False,
        ).count()
    else:
        authorized_workspaces = get_user_authorized_workspaces(user)
        count = Notification.objects.filter(
            recipient=user,
            workspace__in=authorized_workspaces,
            is_read=False,
        ).count()

    user._cached_unread_counts[ws_key] = count
    return count


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
    if hasattr(user, "_cached_unread_counts"):
        user._cached_unread_counts.clear()
    return notif


def mark_all_notifications_as_read(user: Any, workspace: Optional[Workspace] = None) -> int:
    """
    Marks all unread notifications as read for CURRENT user across authorized workspaces.
    Returns the count of updated rows.
    """
    if not user or not user.is_authenticated:
        return 0

    if hasattr(user, "_cached_unread_counts"):
        user._cached_unread_counts.clear()

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
