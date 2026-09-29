"""
Django Template Context Processors for Workspace data.
"""

from apps.workspaces.services import get_user_workspaces


def workspace_context(request):
    """
    Expose active workspace and accessible workspace list to all templates.
    """
    active_workspace = getattr(request, "active_workspace", None)
    active_membership = getattr(request, "active_membership", None)

    user_workspaces = []
    if hasattr(request, "user") and request.user.is_authenticated:
        cached = getattr(request, "_cached_user_workspaces", None)
        if cached is not None:
            user_workspaces = cached
        else:
            user_workspaces = list(get_user_workspaces(request.user))
            request._cached_user_workspaces = user_workspaces

    return {
        "active_workspace": active_workspace,
        "active_membership": active_membership,
        "user_workspaces": user_workspaces,
    }
