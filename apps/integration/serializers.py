"""
Data Integration & Ingestion Serializers.
"""

from rest_framework import serializers
from apps.integration.models import DataSource, ImportJob, RawImportRecord, SourceType, EntityType, ImportStatus
from apps.integration.safety import redact, validate_connection_config, display_source_metadata


class RedactedModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = redact(super().to_representation(instance))
        if 'source_metadata' in data:
            data['source_metadata'] = display_source_metadata(data['source_metadata'])
        return data


class DataSourceSerializer(RedactedModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    import_jobs_count = serializers.IntegerField(source="import_jobs.count", read_only=True, default=0)

    class Meta:
        model = DataSource
        fields = [
            "id",
            "name",
            "source_type",
            "connection_config",
            "is_active",
            "created_by_username",
            "import_jobs_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by_username", "import_jobs_count"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        config = data.get("connection_config")
        data['connection_config'] = redact(config)
        return data


class DataSourceCreateSerializer(serializers.ModelSerializer):
    def validate_connection_config(self, value):
        try:
            return validate_connection_config(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    class Meta:
        model = DataSource
        fields = [
            "name",
            "source_type",
            "connection_config",
            "is_active",
        ]

    def validate_name(self, value):
        clean = value.strip()
        if not clean:
            raise serializers.ValidationError("Data source name cannot be empty.")
        return clean


class RawImportRecordSerializer(RedactedModelSerializer):
    class Meta:
        model = RawImportRecord
        fields = [
            "id",
            "row_number",
            "raw_data",
            "is_valid",
            "validation_errors",
            "created_at",
        ]


class ImportJobSerializer(RedactedModelSerializer):
    data_source_name = serializers.CharField(source="data_source.name", read_only=True)
    data_source_type = serializers.CharField(source="data_source.source_type", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    success_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "data_source",
            "data_source_name",
            "data_source_type",
            "entity_type",
            "status",
            "total_rows",
            "successful_rows",
            "failed_rows",
            "success_rate",
            "source_metadata",
            "started_at",
            "completed_at",
            "created_by_username",
            "created_at",
        ]


class ImportJobDetailSerializer(RedactedModelSerializer):
    data_source = DataSourceSerializer(read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default=None)
    success_rate = serializers.FloatField(read_only=True)
    recent_raw_records = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "data_source",
            "entity_type",
            "status",
            "total_rows",
            "successful_rows",
            "failed_rows",
            "success_rate",
            "error_summary",
            "source_file",
            "source_metadata",
            "started_at",
            "completed_at",
            "created_by_username",
            "recent_raw_records",
            "created_at",
            "updated_at",
        ]

    def get_recent_raw_records(self, obj):
        records = obj.raw_records.all()[:20]
        return RawImportRecordSerializer(records, many=True).data


class ImportPreviewRequestSerializer(serializers.Serializer):
    file = serializers.FileField(required=False, allow_null=True)
    data_source_id = serializers.UUIDField(required=False, allow_null=True)
    source_type = serializers.ChoiceField(choices=SourceType.choices, required=False, allow_null=True)
    sheet_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    endpoint_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sample_count = serializers.IntegerField(default=5, min_value=1, max_value=50)


class ImportExecutionRequestSerializer(serializers.Serializer):
    data_source_id = serializers.UUIDField(required=True)
    file = serializers.FileField(required=False, allow_null=True)
    entity_type = serializers.ChoiceField(choices=EntityType.choices, default=EntityType.GENERAL)
    sheet_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
