"""
Workspace and Tenancy Scoping Models (Tier 2: Scoping Bridge).
"""

import uuid
from django.db import models
from django.conf import settings


class WorkspaceType(models.TextChoices):
    RETAIL = "RETAIL", "Retail"
    SERVICE = "SERVICE", "Service"


class Workspace(models.Model):
    """
    Workspace / Tenant boundary.
    All business data in Tier 3 belongs directly or indirectly to a Workspace.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True, db_index=True)
    workspace_type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        db_index=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspaces_workspace"
        ordering = ["name"]
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self):
        return f"{self.name} ({self.workspace_type})"


class WorkspaceMembership(models.Model):
    """
    Scoping Bridge linking a User to a Workspace with an assigned Role.
    Allows a single User to hold distinct Roles across different Workspaces.
    """

    id = models.BigAutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.RESTRICT,
        related_name="workspace_memberships",
        null=True,
        blank=True,
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspaces_workspacemembership"
        ordering = ["workspace", "user"]
        verbose_name = "Workspace Membership"
        verbose_name_plural = "Workspace Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_workspace_user",
            )
        ]

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.user.username} in {self.workspace.name} as {role_name}"


class WorkspaceScopedQuerySet(models.QuerySet):
    """Custom QuerySet enabling easy filtering by workspace."""

    def for_workspace(self, workspace):
        if not workspace:
            return self.none()
        workspace_id = workspace.id if hasattr(workspace, "id") else workspace
        return self.filter(workspace_id=workspace_id)


class WorkspaceScopedManager(models.Manager.from_queryset(WorkspaceScopedQuerySet)):
    """Custom Manager enforcing workspace-scoped data access."""

    def for_workspace(self, workspace):
        return self.get_queryset().for_workspace(workspace)


class WorkspaceScopedModel(models.Model):
    """
    Abstract base model for Tier 3 domain entities.
    Enforces direct ForeignKey linking to Workspace and attaches WorkspaceScopedManager.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    objects = WorkspaceScopedManager()

    class Meta:
        abstract = True
