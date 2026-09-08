"""
Serializers for Identity, Authentication, and RBAC models.
"""

from rest_framework import serializers
from apps.accounts.models import User, Role, Permission


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission entity."""

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "module", "created_at"]
        read_only_fields = ["id", "created_at"]


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role entity with embedded permissions."""

    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        source="permissions",
        required=False,
    )

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "permission_ids", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User profile details."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_staff", "is_superuser", "created_at", "updated_at"]


class LoginSerializer(serializers.Serializer):
    """Serializer validating login credentials."""

    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})


class UserWorkspaceMembershipSummarySerializer(serializers.Serializer):
    """Summary of user's membership in a workspace."""

    workspace_id = serializers.UUIDField(source="workspace.id")
    workspace_name = serializers.CharField(source="workspace.name")
    workspace_code = serializers.CharField(source="workspace.code")
    workspace_type = serializers.CharField(source="workspace.workspace_type")
    role_name = serializers.CharField(source="role.name", default="None")
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()


class MeSerializer(serializers.Serializer):
    """Serializer for current authenticated user context and active workspace."""

    user = UserSerializer()
    token = serializers.CharField(allow_null=True)
    active_workspace = serializers.DictField(allow_null=True)
    memberships = UserWorkspaceMembershipSummarySerializer(many=True)
