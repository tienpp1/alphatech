from django.contrib import admin
from apps.approvals.models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "workspace", "requester", "proposed_action", "risk_level", "status", "created_at"]
    list_filter = ["workspace", "proposed_action", "risk_level", "status"]
    search_fields = ["proposed_action", "reason", "idempotency_key", "workspace__code"]
