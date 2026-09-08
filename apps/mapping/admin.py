from django.contrib import admin
from apps.mapping.models import MappingProfile, MappingRule


class MappingRuleInline(admin.TabularInline):
    model = MappingRule
    extra = 0
    fields = [
        "source_field",
        "target_field",
        "rule_type",
        "transformation_config",
        "confidence_score",
        "ai_status",
        "is_active",
        "order",
    ]


@admin.register(MappingProfile)
class MappingProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "target_entity", "workspace", "data_source", "is_active", "version", "created_at"]
    list_filter = ["workspace", "target_entity", "is_active"]
    search_fields = ["name", "target_entity", "description"]
    inlines = [MappingRuleInline]


@admin.register(MappingRule)
class MappingRuleAdmin(admin.ModelAdmin):
    list_display = ["id", "profile", "source_field", "target_field", "rule_type", "ai_status", "is_active", "confidence_score"]
    list_filter = ["rule_type", "ai_status", "is_active"]
    search_fields = ["source_field", "target_field", "profile__name"]
