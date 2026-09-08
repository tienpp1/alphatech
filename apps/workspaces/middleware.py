"""
Middleware resolving and attaching verified active Workspace and Membership context to each request.
"""

from apps.workspaces.services import get_explicit_workspace_selector, resolve_active_workspace


class WorkspaceMiddleware:
    """
    Middleware that establishes verified tenancy context on incoming HTTP requests.
    Attaches:
      - request.active_workspace (Workspace or None)
      - request.active_membership (WorkspaceMembership or None)
      - request.workspace_access_denied (bool)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_workspace = None
        request.active_membership = None
        request.workspace_access_denied = False

        if hasattr(request, "user") and request.user.is_authenticated:
            workspace, membership = resolve_active_workspace(request, request.user)
            request.active_workspace = workspace
            request.active_membership = membership

            # Check if an explicit header was supplied but failed validation
            selector_kind, _ = get_explicit_workspace_selector(request)
            if selector_kind and workspace is None:
                request.workspace_access_denied = True

        response = self.get_response(request)
        return response
