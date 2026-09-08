"""
Views for Workspace listings, switching, and current active context.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied

from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.workspaces.serializers import (
    WorkspaceSerializer,
    WorkspaceSwitchSerializer,
)
from apps.workspaces.services import (
    get_user_memberships,
    switch_workspace,
)
from apps.accounts.services import get_user_permissions


class WorkspaceListAPIView(APIView):
    """
    GET /api/v1/workspaces/
    Lists all active workspaces accessible to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        memberships = get_user_memberships(request.user)

        data = [
            {
                "id": str(m.workspace.id),
                "name": m.workspace.name,
                "code": m.workspace.code,
                "workspace_type": m.workspace.workspace_type,
                "description": m.workspace.description,
                "role": m.role.name if m.role else None,
                "is_default": m.is_default,
                "is_active": m.is_active,
                "joined_at": m.joined_at.isoformat(),
            }
            for m in memberships
        ]

        return Response(
            {
                "success": True,
                "count": len(data),
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class WorkspaceSwitchAPIView(APIView):
    """
    POST /api/v1/workspaces/switch/
    Switches the active workspace context in the caller's session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WorkspaceSwitchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid workspace switch payload.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace_id = serializer.validated_data["workspace_id"]

        try:
            workspace, membership = switch_workspace(
                user=request.user,
                workspace_id=workspace_id,
                request=request,
            )
        except PermissionDenied as e:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": str(e),
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        permissions = sorted(list(get_user_permissions(request.user, workspace)))

        return Response(
            {
                "success": True,
                "message": f"Successfully switched to workspace: '{workspace.name}'.",
                "data": {
                    "active_workspace": {
                        "id": str(workspace.id),
                        "name": workspace.name,
                        "code": workspace.code,
                        "workspace_type": workspace.workspace_type,
                        "role": membership.role.name if membership and membership.role else None,
                    },
                    "permissions": permissions,
                },
            },
            status=status.HTTP_200_OK,
        )


class CurrentWorkspaceAPIView(APIView):
    """
    GET /api/v1/workspaces/current/
    Returns the currently active workspace and permissions for the authenticated caller.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        active_workspace = getattr(request, "active_workspace", None)
        active_membership = getattr(request, "active_membership", None)

        if not active_workspace:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NO_ACTIVE_WORKSPACE",
                        "message": "No active workspace is currently selected or accessible.",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        permissions = sorted(list(get_user_permissions(request.user, active_workspace)))

        return Response(
            {
                "success": True,
                "data": {
                    "workspace": WorkspaceSerializer(active_workspace).data,
                    "role": active_membership.role.name if active_membership and active_membership.role else None,
                    "is_default": active_membership.is_default if active_membership else False,
                    "permissions": permissions,
                },
            },
            status=status.HTTP_200_OK,
        )
