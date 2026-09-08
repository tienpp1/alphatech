from django.contrib import admin
from apps.forecasting.models import ForecastModelConfig, ForecastRun, ForecastResult


@admin.register(ForecastModelConfig)
class ForecastModelConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "target_type", "model_type", "model_version", "is_active", "updated_at")
    list_filter = ("workspace", "target_type", "is_active")
    search_fields = ("name", "workspace__name")


@admin.register(ForecastRun)
class ForecastRunAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "target_type", "status", "dataset_row_count", "created_at")
    list_filter = ("workspace", "target_type", "status")
    search_fields = ("workspace__name", "artifact_path")


@admin.register(ForecastResult)
class ForecastResultAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "target_type", "forecast_date", "predicted_value", "lower_bound", "upper_bound")
    list_filter = ("workspace", "target_type", "forecast_date")
    search_fields = ("workspace__name",)
