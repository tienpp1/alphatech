"""
Business services for Workspace lifecycle, Tenancy resolution, and Switching.
"""

from typing import Optional, Tuple, List
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import QuerySet
from apps.workspaces.models import Workspace, WorkspaceMembership


def get_user_workspaces(user) -> QuerySet[Workspace]:
    """
    Return all active Workspaces where the user holds an active membership.
    """
    if not user or not user.is_authenticated:
        return Workspace.objects.none()

    if user.is_superuser:
        return Workspace.objects.filter(is_active=True)

    return Workspace.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        is_active=True,
    ).distinct()


def get_user_memberships(user) -> QuerySet[WorkspaceMembership]:
    """
    Return all active WorkspaceMemberships for a user.
    """
    if not user or not user.is_authenticated:
        return WorkspaceMembership.objects.none()

    return (
        WorkspaceMembership.objects.filter(
            user=user,
            is_active=True,
            workspace__is_active=True,
        )
        .select_related("workspace", "role")
        .order_by("-is_default", "joined_at")
    )


def get_explicit_workspace_selector(request):
    """Return the explicit workspace selector, with ID taking precedence."""
    if not request:
        return None, None

    workspace_id = request.headers.get("X-Workspace-ID") if hasattr(request, "headers") else None
    if not workspace_id and hasattr(request, "META"):
        workspace_id = request.META.get("HTTP_X_WORKSPACE_ID")
    if workspace_id:
        return "id", workspace_id

    workspace_code = request.headers.get("X-Workspace") if hasattr(request, "headers") else None
    if not workspace_code and hasattr(request, "META"):
        workspace_code = request.META.get("HTTP_X_WORKSPACE")
    if workspace_code:
        return "code", workspace_code

    return None, None


def resolve_authorized_ui_workspace(request, workspace_type, permission_codename):
    """Resolve an internal UI workspace without ever using a global fallback.

    The active workspace wins when it has the expected type. If the active
    workspace belongs to another domain, a workspace of the expected type may
    be selected only from the user's authorized memberships. An explicit
    workspace header is never silently replaced with another workspace.
    """
    from apps.accounts.services import has_workspace_permission

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication is required for this internal workspace.")
    if getattr(request, "workspace_access_denied", False):
        raise PermissionDenied("You do not have access to the requested workspace.")

    active_workspace = getattr(request, "active_workspace", None)
    if active_workspace and (workspace_type is None or active_workspace.workspace_type == workspace_type):
        if has_workspace_permission(user, active_workspace, permission_codename):
            return active_workspace
        raise PermissionDenied(f"Missing workspace permission: {permission_codename}")

    selector_kind, _ = get_explicit_workspace_selector(request)
    if selector_kind:
        raise PermissionDenied("The requested workspace does not match this internal domain.")

    candidates = get_user_workspaces(user)
    if workspace_type is not None:
        candidates = candidates.filter(workspace_type=workspace_type)
    for workspace in candidates:
        if has_workspace_permission(user, workspace, permission_codename):
            return workspace

    raise PermissionDenied(f"Missing workspace permission: {permission_codename}")


def validate_workspace_access(
    user,
    workspace_id,
) -> Tuple[bool, Optional[WorkspaceMembership], Optional[Workspace]]:
    """
    Verify whether a user is authorized to access a target workspace.
    Returns: (is_valid, membership, workspace)
    """
    if not user or not user.is_authenticated or not user.is_active or not workspace_id:
        return False, None, None

    try:
        workspace = Workspace.objects.get(id=workspace_id, is_active=True)
    except (Workspace.DoesNotExist, ValueError, TypeError):
        return False, None, None

    if user.is_superuser:
        membership = WorkspaceMembership.objects.filter(
            user=user,
            workspace=workspace,
            is_active=True,
        ).first()
        return True, membership, workspace

    try:
        membership = WorkspaceMembership.objects.select_related("role").get(
            user=user,
            workspace=workspace,
            is_active=True,
        )
        return True, membership, workspace
    except WorkspaceMembership.DoesNotExist:
        return False, None, None


def resolve_active_workspace(
    request,
    user,
) -> Tuple[Optional[Workspace], Optional[WorkspaceMembership]]:
    """
    Resolve the active workspace context for the current request.
    Strictly verifies any requested workspace against user's active memberships.
    
    Priority resolution:
    1. 'X-Workspace-ID' HTTP header (Must be explicitly verified; forged headers rejected).
    2. 'active_workspace_id' stored in request session.
    3. User's designated default membership.
    4. First available active membership for user.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return None, None

    # Priority 1: explicit headers. X-Workspace-ID is authoritative when both
    # are supplied. The legacy code header is retained only with membership
    # validation through the same canonical access check.
    selector_kind, selector_value = get_explicit_workspace_selector(request)
    if selector_kind == "id":
        is_valid, membership, workspace = validate_workspace_access(user, selector_value)
        if is_valid:
            return workspace, membership
        return None, None
    if selector_kind == "code":
        workspace_id = (
            Workspace.objects.filter(code=selector_value, is_active=True)
            .values_list("id", flat=True)
            .first()
        )
        is_valid, membership, workspace = validate_workspace_access(user, workspace_id)
        if is_valid:
            return workspace, membership
        return None, None

    # Priority 2: Session active workspace
    if request and hasattr(request, "session"):
        session_workspace_id = request.session.get("active_workspace_id")
        if session_workspace_id:
            is_valid, membership, workspace = validate_workspace_access(user, session_workspace_id)
            if is_valid:
                return workspace, membership

    # Priority 3: Default membership
    default_membership = (
        WorkspaceMembership.objects.filter(
            user=user,
            is_active=True,
            is_default=True,
            workspace__is_active=True,
        )
        .select_related("workspace", "role")
        .first()
    )
    if default_membership:
        if request and hasattr(request, "session"):
            request.session["active_workspace_id"] = str(default_membership.workspace.id)
        return default_membership.workspace, default_membership

    # Priority 4: First active membership
    first_membership = (
        WorkspaceMembership.objects.filter(
            user=user,
            is_active=True,
            workspace__is_active=True,
        )
        .select_related("workspace", "role")
        .first()
    )
    if first_membership:
        if request and hasattr(request, "session"):
            request.session["active_workspace_id"] = str(first_membership.workspace.id)
        return first_membership.workspace, first_membership

    # Fallback for superuser with no memberships
    if user.is_superuser:
        first_workspace = Workspace.objects.filter(is_active=True).first()
        if first_workspace:
            return first_workspace, None

    return None, None


def resolve_request_workspace(request):
    """Resolve and attach a verified request workspace for API/UI callers."""
    user = getattr(request, "user", None)
    selector_kind, _ = get_explicit_workspace_selector(request)

    if not selector_kind and getattr(request, "active_workspace", None):
        return request.active_workspace

    workspace, membership = resolve_active_workspace(request, user)
    request.active_workspace = workspace
    request.active_membership = membership
    if selector_kind and workspace is None:
        request.workspace_access_denied = True
    return workspace


def switch_workspace(
    user,
    workspace_id,
    request=None,
) -> Tuple[Workspace, Optional[WorkspaceMembership]]:
    """
    Switch active tenant context for the user and persist into session.
    Raises PermissionDenied if the user does not possess an active membership.
    """
    is_valid, membership, workspace = validate_workspace_access(user, workspace_id)
    if not is_valid or not workspace:
        raise PermissionDenied("You do not have active access to the specified workspace.")

    if request and hasattr(request, "session"):
        request.session["active_workspace_id"] = str(workspace.id)

    return workspace, membership
