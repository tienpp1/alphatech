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



def get_user_permissions(user: User, workspace) -> Set[str]:
    """
    Return all permission codenames granted to the user in the specified workspace.
    - Superusers inherit all existing permissions across all workspaces.
    - Regular users inherit permissions associated with their active WorkspaceMembership Role.
    """
    if not user or not user.is_authenticated:
        return set()

    if user.is_superuser:
        return set(Permission.objects.values_list("codename", flat=True))

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
            return set(membership.role.permissions.values_list("codename", flat=True))
    except WorkspaceMembership.DoesNotExist:
        return set()

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
    """
    if not user or not user.is_authenticated or not workspace:
        return None

    from apps.workspaces.models import WorkspaceMembership

    try:
        membership = WorkspaceMembership.objects.select_related("role").get(
            user=user,
            workspace=workspace,
            is_active=True,
        )
        return membership.role
    except WorkspaceMembership.DoesNotExist:
        return None


def assign_role_to_user_in_workspace(user: User, workspace, role: Role, is_default: bool = False):
    """
    Assign or update a role for a user in a specific workspace via WorkspaceMembership.
    """
    from apps.workspaces.models import WorkspaceMembership

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
