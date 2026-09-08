"""
Reusable Django REST Framework Permission Classes for Workspace Scoping and RBAC.
"""

from rest_framework.permissions import BasePermission
from apps.accounts.services import has_workspace_permission


class IsWorkspaceMember(BasePermission):
    """
    Allows access only if the authenticated user has an active membership in the active workspace.
    Explicitly rejects requests if an invalid/unauthorized X-Workspace-ID header was supplied.
    """

    message = "You do not have an active membership in the requested workspace."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not getattr(request, "active_workspace", None):
            from apps.workspaces.services import get_explicit_workspace_selector, resolve_active_workspace
            workspace, membership = resolve_active_workspace(request, request.user)
            request.active_workspace = workspace
            request.active_membership = membership
            selector_kind, _ = get_explicit_workspace_selector(request)
            if selector_kind and workspace is None:
                request.workspace_access_denied = True
                return False

        if getattr(request, "workspace_access_denied", False):
            return False

        return request.active_workspace is not None


class IsWorkspaceAdmin(BasePermission):
    """
    Allows access only to Workspace Administrators (or platform superusers).
    """

    message = "This action requires Workspace Administrator privileges."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not getattr(request, "active_workspace", None):
            from apps.workspaces.services import resolve_active_workspace
            workspace, membership = resolve_active_workspace(request, request.user)
            request.active_workspace = workspace
            request.active_membership = membership

        if getattr(request, "workspace_access_denied", False):
            return False

        membership = getattr(request, "active_membership", None)
        if not membership or not membership.role:
            return False

        return membership.role.name.upper() == "ADMIN"


class IsWorkspaceManager(BasePermission):
    """
    Allows access to Workspace Managers and Administrators (or platform superusers).
    """

    message = "This action requires Manager or Administrator privileges."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not getattr(request, "active_workspace", None):
            from apps.workspaces.services import resolve_active_workspace
            workspace, membership = resolve_active_workspace(request, request.user)
            request.active_workspace = workspace
            request.active_membership = membership

        if getattr(request, "workspace_access_denied", False):
            return False

        membership = getattr(request, "active_membership", None)
        if not membership or not membership.role:
            return False

        return membership.role.name.upper() in ("ADMIN", "MANAGER")


def require_permission(permission_codename: str):
    """
    Dynamic permission class factory verifying a specific RBAC permission codename.
    Usage:
        permission_classes = [IsWorkspaceMember, require_permission("retail.create_order")]
    """

    class DynamicWorkspacePermission(BasePermission):
        message = f"You do not possess the required permission: '{permission_codename}'."

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False

            if request.user.is_superuser:
                return True

            workspace = getattr(request, "active_workspace", None)
            if not workspace:
                from apps.workspaces.services import resolve_active_workspace
                workspace, membership = resolve_active_workspace(request, request.user)
                request.active_workspace = workspace
                request.active_membership = membership
                if not workspace:
                    return False

            if getattr(request, "workspace_access_denied", False):
                return False

            return has_workspace_permission(request.user, workspace, permission_codename)

    return DynamicWorkspacePermission
