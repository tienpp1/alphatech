"""
Serializers for Workspace models and tenancy endpoints.
"""

from rest_framework import serializers
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.accounts.serializers import RoleSerializer, UserSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace entity."""

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "code",
            "workspace_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    """Serializer for WorkspaceMembership detailing user and assigned role."""

    workspace = WorkspaceSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = [
            "id",
            "workspace",
            "user",
            "role",
            "is_default",
            "is_active",
            "joined_at",
        ]
        read_only_fields = ["id", "joined_at"]


class WorkspaceSwitchSerializer(serializers.Serializer):
    """Serializer validating workspace switch requests."""

    workspace_id = serializers.UUIDField(required=True)


class CurrentWorkspaceDetailSerializer(serializers.Serializer):
    """Serializer representing current active workspace and permissions."""

    workspace = WorkspaceSerializer()
    role = serializers.CharField(allow_null=True)
    is_default = serializers.BooleanField()
    permissions = serializers.ListField(child=serializers.CharField())
