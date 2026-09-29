"""
Business service layer for Workspace Internal Bulletins (Bản tin Điều hành Nội bộ).
Enforces workspace multi-tenant isolation, RBAC publishing rights, and pinned announcements.
"""

from typing import List, Optional
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.notifications.models import InternalBulletin, BulletinPriority
from apps.workspaces.models import Workspace, WorkspaceMembership


@transaction.atomic
def update_bulletin(workspace, user, bulletin_id, *, title, content, priority):
    """Update editorial fields only; never move tenants or replace the author."""
    if not can_manage_bulletins(user, workspace):
        raise PermissionDenied("Bạn không có quyền cập nhật bản tin.")
    bulletin = get_object_or_404(
        InternalBulletin.objects.select_for_update().filter(workspace=workspace),
        pk=bulletin_id,
    )
    from apps.notifications.bulletin_forms import BulletinEditForm
    form = BulletinEditForm(
        {"title": title, "content": content, "priority": priority}, instance=bulletin
    )
    if not form.is_valid():
        from django.core.exceptions import ValidationError
        raise ValidationError(form.errors.as_data())
    # Save only allowed fields, preserving concurrent non-editorial metadata.
    bulletin = form.save(commit=False)
    bulletin.save(update_fields=["title", "content", "priority", "updated_at"])
    return bulletin


def get_workspace_bulletins(
    workspace: Workspace,
    priority: Optional[str] = None,
    include_unpublished: bool = False,
) -> List[InternalBulletin]:
    """
    Returns all bulletins scoped strictly to the given workspace.
    Orders PINNED bulletins first (if active), followed by newest bulletins.
    """
    qs = InternalBulletin.objects.filter(workspace=workspace)
    if not include_unpublished:
        qs = qs.filter(is_published=True)

    if priority and priority in BulletinPriority.values:
        qs = qs.filter(priority=priority)

    now = timezone.now()
    bulletins = list(qs.select_related("author", "workspace").order_by("-created_at"))

    # Separate pinned vs regular for clean top-pinning
    pinned = []
    regular = []
    for b in bulletins:
        if b.is_pinned:
            pinned.append(b)
        else:
            regular.append(b)

    return pinned + regular


def create_bulletin(
    workspace: Workspace,
    author,
    title: str,
    content: str,
    priority: str = BulletinPriority.NORMAL,
    pinned_until: Optional[timezone.datetime] = None,
    is_published: bool = True,
    is_pinned: bool = False,
) -> InternalBulletin:
    """
    Creates a new internal bulletin within a workspace.
    Caller must verify that the author has administrative or managerial rights.
    """
    if is_pinned or priority == BulletinPriority.PINNED:
        priority = BulletinPriority.PINNED
    elif priority not in BulletinPriority.values:
        priority = BulletinPriority.NORMAL

    bulletin = InternalBulletin.objects.create(
        workspace=workspace,
        author=author,
        title=title.strip(),
        content=content.strip(),
        priority=priority,
        pinned_until=pinned_until,
        is_published=is_published,
    )
    return bulletin


def can_manage_bulletins(user, workspace: Workspace) -> bool:
    """
    Returns True if user has administrative rights to publish or delete bulletins in this workspace.
    Staff with MANAGER or ADMIN role, or superusers.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    from apps.accounts.services import get_user_role_in_workspace

    role = get_user_role_in_workspace(user, workspace)
    if not role:
        return False

    role_name = (role.name or "").upper()
    # Django admin-site access is not a workspace publishing capability.
    return role_name in ("ADMIN", "MANAGER")
