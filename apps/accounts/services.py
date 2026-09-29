"""
Business service layer for Identity, Authentication and RBAC Authorization.
"""

from typing import Optional, Set, List
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from apps.accounts.models import User, Role, Permission


def authenticate_user(username_or_email: str, password: str) -> Optional[User]:
    """
    Authenticate user credentials against the Custom User model using either username or email.
    Returns the User instance if valid and active, otherwise None.
    """
    if not username_or_email or not password:
        return None
    user = authenticate(username=username_or_email, password=password)
    if not user:
        user_obj = User.objects.filter(email__iexact=username_or_email).first()
        if user_obj:
            user = authenticate(username=user_obj.username, password=password)
    if user and user.is_active:
        return user
    return None



from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

_PERMS_CACHE_VERSION = 0


@receiver(m2m_changed, sender=Role.permissions.through)
def _invalidate_perms_cache_on_m2m(sender, **kwargs):
    global _PERMS_CACHE_VERSION
    _PERMS_CACHE_VERSION += 1


@receiver(post_save, sender=Role)
def _invalidate_perms_cache_on_role_save(sender, **kwargs):
    global _PERMS_CACHE_VERSION
    _PERMS_CACHE_VERSION += 1


def get_user_permissions(user: User, workspace) -> Set[str]:
    """
    Return all permission codenames granted to the user in the specified workspace.
    - Superusers inherit all existing permissions across all workspaces.
    - Regular users inherit permissions associated with their active WorkspaceMembership Role.
    Uses in-memory per-instance memoization with global cache versioning to support dynamic permission mutations.
    """
    if not user or not user.is_authenticated:
        return set()

    ws_key = str(getattr(workspace, "id", workspace)) if workspace else ""

    cache_data = getattr(user, "_cached_workspace_perms", None)
    if (
        isinstance(cache_data, dict)
        and cache_data.get("version") == _PERMS_CACHE_VERSION
        and ws_key in cache_data.get("perms", {})
    ):
        return cache_data["perms"][ws_key]

    if not isinstance(cache_data, dict) or cache_data.get("version") != _PERMS_CACHE_VERSION:
        user._cached_workspace_perms = {"version": _PERMS_CACHE_VERSION, "perms": {}}

    if user.is_superuser:
        perms = set(Permission.objects.values_list("codename", flat=True))
        user._cached_workspace_perms["perms"][ws_key] = perms
        return perms

    if not workspace:
        return set()

    # Import dynamically to avoid circular dependencies
    from apps.workspaces.models import WorkspaceMembership

    try:
        membership = WorkspaceMembership.objects.select_related("role").get(
            user=user,
            workspace=workspace,
            is_active=True,
        )
        if membership.role:
            perms = set(membership.role.permissions.values_list("codename", flat=True))
            user._cached_workspace_perms["perms"][ws_key] = perms
            return perms
    except WorkspaceMembership.DoesNotExist:
        user._cached_workspace_perms["perms"][ws_key] = set()
        return set()

    user._cached_workspace_perms["perms"][ws_key] = set()
    return set()


def has_workspace_permission(user: User, workspace, permission_codename: str) -> bool:
    """
    Check if a user holds a specific permission within the context of a given workspace.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if user.is_superuser:
        return True

    if not workspace or not permission_codename:
        return False

    permissions = get_user_permissions(user, workspace)
    return permission_codename in permissions


def get_user_role_in_workspace(user: User, workspace) -> Optional[Role]:
    """
    Return the assigned Role of a user in a given workspace.
    Uses in-memory per-instance memoization on `user` to avoid redundant database queries during request processing.
    """
    if not user or not user.is_authenticated or not workspace:
        return None

    ws_key = str(getattr(workspace, "id", workspace)) if workspace else ""

    if not hasattr(user, "_cached_workspace_roles"):
        user._cached_workspace_roles = {}

    if ws_key in user._cached_workspace_roles:
        return user._cached_workspace_roles[ws_key]

    from apps.workspaces.models import WorkspaceMembership

    try:
        membership = WorkspaceMembership.objects.select_related("role").get(
            user=user,
            workspace=workspace,
            is_active=True,
        )
        role = membership.role
        user._cached_workspace_roles[ws_key] = role
        return role
    except WorkspaceMembership.DoesNotExist:
        user._cached_workspace_roles[ws_key] = None
        return None


def assign_role_to_user_in_workspace(user: User, workspace, role: Role, is_default: bool = False):
    """
    Assign or update a role for a user in a specific workspace via WorkspaceMembership.
    """
    from apps.workspaces.models import WorkspaceMembership

    ws_key = str(getattr(workspace, "id", workspace)) if workspace else ""
    if hasattr(user, "_cached_workspace_perms") and isinstance(user._cached_workspace_perms, dict):
        user._cached_workspace_perms.get("perms", {}).pop(ws_key, None)
    if hasattr(user, "_cached_workspace_roles") and isinstance(user._cached_workspace_roles, dict):
        user._cached_workspace_roles.pop(ws_key, None)

    membership, created = WorkspaceMembership.objects.update_or_create(
        user=user,
        workspace=workspace,
        defaults={
            "role": role,
            "is_active": True,
            "is_default": is_default,
        },
    )
    return membership
