"""
Identity, User, Role, and Permission Models (Tier 1: Global Entities).
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class Permission(models.Model):
    """
    Global granular permission definition.
    Example codename: 'retail.create_order', 'service.assign_task', 'ai.approve_action'.
    """

    codename = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_permission"
        ordering = ["module", "codename"]
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"

    def __str__(self):
        return f"{self.module}: {self.codename} ({self.name})"


class Role(models.Model):
    """
    Global role bundle containing a set of permissions.
    Standard roles: ADMIN, MANAGER, EMPLOYEE, VIEWER.
    """

    name = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_role"
        ordering = ["name"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name

    def has_permission(self, codename: str) -> bool:
        """Check if this role contains a specific permission codename."""
        return self.permissions.filter(codename=codename).exists()


class User(AbstractUser):
    """
    Custom Global User entity.
    Independent of workspace scope; a single user may hold distinct roles
    across multiple workspaces via WorkspaceMembership.
    """

    email = models.EmailField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username
