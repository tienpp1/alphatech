"""
Views for Identity & Authentication APIs (Session + DRF Token Auth).
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout

from apps.accounts.serializers import LoginSerializer, UserSerializer, MeSerializer
from apps.accounts.services import authenticate_user, get_user_permissions
from apps.workspaces.models import WorkspaceMembership


class LoginAPIView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates user, establishes Django session, and returns DRF Token.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid credentials payload.",
                        "details": serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate_user(username, password)
        if not user:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "AUTHENTICATION_FAILED",
                        "message": "Invalid username or password, or account is disabled.",
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 1. Establish Django session authentication
        login(request, user)

        # 2. Get or create DRF Token
        token, _ = Token.objects.get_or_create(user=user)

        # 3. Retrieve user memberships and determine default active workspace
        memberships = (
            WorkspaceMembership.objects.filter(user=user, is_active=True)
            .select_related("workspace", "role")
            .order_by("-is_default", "joined_at")
        )

        active_workspace_data = None
        if memberships.exists():
            default_membership = memberships.first()
            request.session["active_workspace_id"] = str(default_membership.workspace.id)
            active_workspace_data = {
                "id": str(default_membership.workspace.id),
                "name": default_membership.workspace.name,
                "code": default_membership.workspace.code,
                "workspace_type": default_membership.workspace.workspace_type,
                "role": default_membership.role.name if default_membership.role else None,
            }

        memberships_data = [
            {
                "workspace": {
                    "id": m.workspace.id,
                    "name": m.workspace.name,
                    "code": m.workspace.code,
                    "workspace_type": m.workspace.workspace_type,
                },
                "role": {"name": m.role.name if m.role else None},
                "is_default": m.is_default,
                "is_active": m.is_active,
            }
            for m in memberships
        ]

        response_payload = {
            "success": True,
            "message": "Authentication successful.",
            "data": {
                "user": UserSerializer(user).data,
                "token": token.key,
                "active_workspace": active_workspace_data,
                "memberships": [
                    {
                        "workspace_id": m.workspace.id,
                        "workspace_name": m.workspace.name,
                        "workspace_code": m.workspace.code,
                        "workspace_type": m.workspace.workspace_type,
                        "role_name": m.role.name if m.role else None,
                        "is_default": m.is_default,
                        "is_active": m.is_active,
                    }
                    for m in memberships
                ],
            },
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    """
    POST /api/v1/auth/logout/
    Flushes user session and deletes the active DRF auth token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 1. Delete user token if it exists
        Token.objects.filter(user=request.user).delete()

        # 2. Flush Django session
        logout(request)

        return Response(
            {
                "success": True,
                "message": "Successfully logged out.",
            },
            status=status.HTTP_200_OK,
        )


class MeAPIView(APIView):
    """
    GET /api/v1/auth/me/
    Returns identity and tenancy context for the authenticated caller.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        token = Token.objects.filter(user=user).first()

        active_workspace = getattr(request, "active_workspace", None)
        active_membership = getattr(request, "active_membership", None)

        active_workspace_data = None
        user_permissions = []

        if active_workspace:
            active_workspace_data = {
                "id": str(active_workspace.id),
                "name": active_workspace.name,
                "code": active_workspace.code,
                "workspace_type": active_workspace.workspace_type,
                "role": active_membership.role.name if active_membership and active_membership.role else None,
            }
            user_permissions = sorted(list(get_user_permissions(user, active_workspace)))

        memberships = (
            WorkspaceMembership.objects.filter(user=user, is_active=True)
            .select_related("workspace", "role")
            .order_by("-is_default", "joined_at")
        )

        return Response(
            {
                "success": True,
                "data": {
                    "user": UserSerializer(user).data,
                    "token": token.key if token else None,
                    "active_workspace": active_workspace_data,
                    "permissions": user_permissions,
                    "memberships": [
                        {
                            "workspace_id": m.workspace.id,
                            "workspace_name": m.workspace.name,
                            "workspace_code": m.workspace.code,
                            "workspace_type": m.workspace.workspace_type,
                            "role_name": m.role.name if m.role else None,
                            "is_default": m.is_default,
                            "is_active": m.is_active,
                        }
                        for m in memberships
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )
