"""
Django Admin configurations for User, Role, and Permission.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User, Role, Permission


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin configuration."""

    list_display = ["username", "email", "first_name", "last_name", "is_staff", "is_active", "created_at"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["username"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin configuration for Permission entity."""

    list_display = ["codename", "name", "module", "created_at"]
    list_filter = ["module"]
    search_fields = ["codename", "name", "module"]
    ordering = ["module", "codename"]
    readonly_fields = ["created_at"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin configuration for Role entity with filter_horizontal for permissions."""

    list_display = ["name", "description", "get_permissions_count", "created_at", "updated_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["permissions"]
    readonly_fields = ["created_at", "updated_at"]

    def get_permissions_count(self, obj):
        return obj.permissions.count()

    get_permissions_count.short_description = "Permissions Count"
