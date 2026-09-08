from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "workspace",
        "actor_user",
        "actor_type",
        "action",
        "entity_type",
        "entity_id",
    )
    list_filter = ("actor_type", "action", "entity_type", "workspace")
    search_fields = ("action", "entity_type", "entity_id", "actor_user__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
