"""
Data Mapping & Standard Data Model DRF Serializers.
"""

from rest_framework import serializers
from apps.mapping.models import (
    MappingProfile,
    MappingRule,
    RuleType,
    AIConfirmationStatus,
    ValidationStatus,
)
from apps.mapping.canonical import CANONICAL_MODELS


class MappingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingRule
        fields = [
            "id",
            "profile",
            "source_field",
            "target_field",
            "rule_type",
            "transformation_config",
            "confidence_score",
            "ai_status",
            "validation_status",
            "validation_error",
            "is_active",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "profile", "created_at", "updated_at"]


class MappingRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingRule
        fields = [
            "source_field",
            "target_field",
            "rule_type",
            "transformation_config",
            "confidence_score",
            "ai_status",
            "order",
            "is_active",
        ]

    def validate_target_field(self, value):
        clean = value.strip()
        if not clean:
            raise serializers.ValidationError("Target field cannot be empty.")
        return clean


class MappingProfileSerializer(serializers.ModelSerializer):
    rules = MappingRuleSerializer(many=True, read_only=True)
    active_rules_count = serializers.IntegerField(read_only=True)
    data_source_name = serializers.CharField(source="data_source.name", read_only=True, default=None)

    class Meta:
        model = MappingProfile
        fields = [
            "id",
            "name",
            "target_entity",
            "data_source",
            "data_source_name",
            "description",
            "is_active",
            "version",
            "active_rules_count",
            "rules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "active_rules_count", "version", "created_at", "updated_at"]


class MappingProfileCreateSerializer(serializers.ModelSerializer):
    data_source_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = MappingProfile
        fields = [
            "name",
            "target_entity",
            "data_source_id",
            "description",
            "is_active",
        ]

    def validate_name(self, value):
        clean = value.strip()
        if not clean:
            raise serializers.ValidationError("Profile name cannot be empty.")
        return clean

    def validate_target_entity(self, value):
        clean = value.strip()
        if clean not in CANONICAL_MODELS:
            raise serializers.ValidationError(
                f"Invalid target entity '{clean}'. Allowed canonical entities: {list(CANONICAL_MODELS.keys())}"
            )
        return clean


class MappingPreviewRequestSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(required=True)
    import_job_id = serializers.UUIDField(required=False, allow_null=True)
    raw_records = serializers.ListField(child=serializers.DictField(), required=False, allow_null=True)
    sample_count = serializers.IntegerField(default=5, min_value=1, max_value=50)


class MappingApplyRequestSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(required=True)
    import_job_id = serializers.UUIDField(required=True)
    strict = serializers.BooleanField(default=False)


class AISuggestRequestSerializer(serializers.Serializer):
    target_entity = serializers.CharField(required=True)
    source_columns = serializers.ListField(child=serializers.CharField(), required=True)
    sample_values = serializers.DictField(required=False, default=dict)
    inferred_types = serializers.DictField(required=False, default=dict)

    def validate_target_entity(self, value):
        if value not in CANONICAL_MODELS:
            raise serializers.ValidationError(
                f"Unknown target entity '{value}'. Allowed: {list(CANONICAL_MODELS.keys())}"
            )
        return value
