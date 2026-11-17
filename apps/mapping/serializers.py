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
from apps.mapping.engine.transformer import validate_transformation_config


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
    def validate_transformation_config(self, value):
        try:
            return validate_transformation_config(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

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
    source_columns = serializers.ListField(child=serializers.CharField(max_length=100), required=True, min_length=1, max_length=100)
    sample_values = serializers.DictField(required=False, default=dict)
    inferred_types = serializers.DictField(required=False, default=dict)
    mode = serializers.ChoiceField(choices=('heuristic', 'groq_schema'), default='heuristic')
    allow_schema_export = serializers.BooleanField(default=False)
    profile_id = serializers.UUIDField(required=False)

    def validate(self, data):
        if len(set(data['source_columns'])) != len(data['source_columns']):
            raise serializers.ValidationError('Tên cột nguồn không được trùng nhau.')
        if data['mode'] == 'groq_schema' and (not data.get('allow_schema_export') or not data.get('profile_id')):
            raise serializers.ValidationError('Cần chọn hồ sơ và đồng ý gửi tên cột tới Groq; không gửi dữ liệu mẫu.')
        if any(not isinstance(v, list) or len(v) > 50 for v in data['sample_values'].values()):
            raise serializers.ValidationError('Dữ liệu mẫu phải là danh sách có giới hạn.')
        if any(not isinstance(v, str) for v in data['inferred_types'].values()):
            raise serializers.ValidationError('Kiểu dữ liệu suy luận không hợp lệ.')
        return data

    def validate_target_entity(self, value):
        if value not in CANONICAL_MODELS:
            raise serializers.ValidationError(
                f"Unknown target entity '{value}'. Allowed: {list(CANONICAL_MODELS.keys())}"
            )
        return value
