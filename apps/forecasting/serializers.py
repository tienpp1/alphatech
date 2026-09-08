"""
DRF Serializers for Predictive Analytics & Forecasting.
"""

from rest_framework import serializers
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    ForecastResult,
    TargetType,
    ModelType,
    Granularity,
    RunStatus,
)


class ForecastModelConfigSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source="get_target_type_display", read_only=True)
    model_type_display = serializers.CharField(source="get_model_type_display", read_only=True)

    class Meta:
        model = ForecastModelConfig
        fields = [
            "id",
            "name",
            "target_type",
            "target_type_display",
            "model_type",
            "model_type_display",
            "granularity",
            "feature_config",
            "training_config",
            "is_active",
            "model_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ForecastRunSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source="get_target_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    config_name = serializers.CharField(source="model_config.name", read_only=True)

    class Meta:
        model = ForecastRun
        fields = [
            "id",
            "model_config",
            "config_name",
            "target_type",
            "target_type_display",
            "status",
            "status_display",
            "training_start_at",
            "training_end_at",
            "dataset_period_start",
            "dataset_period_end",
            "dataset_row_count",
            "train_row_count",
            "test_row_count",
            "model_metrics",
            "baseline_metrics",
            "feature_importances",
            "artifact_path",
            "job_parameters",
            "attempt_count",
            "heartbeat_at",
            "cancel_requested",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class ForecastResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastResult
        fields = [
            "id",
            "forecast_run",
            "target_type",
            "forecast_date",
            "predicted_value",
            "lower_bound",
            "upper_bound",
            "actual_value",
            "created_at",
        ]
        read_only_fields = fields


class TrainForecastRequestSerializer(serializers.Serializer):
    dimensions = serializers.DictField(child=serializers.IntegerField(min_value=1), required=False)
    target_type = serializers.ChoiceField(choices=TargetType.choices)
    is_async = serializers.BooleanField(default=False)
    horizon_days = serializers.IntegerField(default=14, min_value=1, max_value=90)
    n_estimators = serializers.IntegerField(required=False, min_value=10, max_value=500)
    max_depth = serializers.IntegerField(required=False, min_value=1, max_value=10)
    learning_rate = serializers.FloatField(required=False, min_value=0.001, max_value=1.0)
    test_size = serializers.FloatField(required=False, min_value=0.05, max_value=0.5)
