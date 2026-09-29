"""
Django Admin configurations for Workspace and WorkspaceMembership.
"""

from django.contrib import admin
from django.db.models import Count
from apps.workspaces.models import Workspace, WorkspaceMembership


class WorkspaceMembershipInline(admin.TabularInline):
    """Inline view of user memberships within a workspace."""

    model = WorkspaceMembership
    extra = 0
    autocomplete_fields = ["user", "role"]
    fields = ["user", "role", "is_default", "is_active", "joined_at"]
    readonly_fields = ["joined_at"]


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Admin configuration for Workspace entity."""

    list_display = ["name", "code", "workspace_type", "is_active", "get_member_count", "created_at"]
    list_filter = ["workspace_type", "is_active"]
    search_fields = ["name", "code", "description"]
    prepopulated_fields = {"code": ("name",)}
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [WorkspaceMembershipInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(annotated_member_count=Count("memberships"))

    def get_member_count(self, obj):
        return getattr(obj, "annotated_member_count", obj.memberships.count())

    get_member_count.short_description = "Members"
    get_member_count.admin_order_field = "annotated_member_count"


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    """Admin configuration for WorkspaceMembership scoping bridge."""

    list_display = ["user", "workspace", "role", "is_default", "is_active", "joined_at"]
    list_filter = ["workspace", "role", "is_default", "is_active"]
    search_fields = ["user__username", "user__email", "workspace__name", "role__name"]
    autocomplete_fields = ["user", "workspace", "role"]
    readonly_fields = ["joined_at"]
    list_select_related = ["user", "workspace", "role"]
