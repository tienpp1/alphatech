"""
Predictive Analytics & Forecasting Models.
Follows docs/ai-architecture.md Section 3 and AGENT_MASTER_SPEC.md.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.workspaces.models import WorkspaceScopedModel


class TargetType(models.TextChoices):
    RETAIL_REVENUE = "RETAIL_REVENUE", "Retail Revenue"
    RETAIL_ORDER_VOLUME = "RETAIL_ORDER_VOLUME", "Retail Order Volume"
    RETAIL_PRODUCT_DEMAND = "RETAIL_PRODUCT_DEMAND", "Retail Product Demand"
    SERVICE_TICKET_VOLUME = "SERVICE_TICKET_VOLUME", "Service Ticket Volume"


class ModelType(models.TextChoices):
    XGBOOST_REGRESSOR = "XGBOOST_REGRESSOR", "XGBoost Regressor"


class Granularity(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"


class RunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class ForecastModelConfig(WorkspaceScopedModel):
    """
    Configuration specification for a time-series forecasting model.
    Scoped strictly to an active workspace.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True,
    )
    model_type = models.CharField(
        max_length=50,
        choices=ModelType.choices,
        default=ModelType.XGBOOST_REGRESSOR,
    )
    granularity = models.CharField(
        max_length=20,
        choices=Granularity.choices,
        default=Granularity.DAILY,
    )
    feature_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuration for lag periods, rolling windows, and calendar features.",
    )
    training_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="XGBoost hyperparameters: n_estimators, max_depth, learning_rate, subsample, test_size.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    model_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "forecasting_model_config"
        ordering = ["-updated_at"]
        verbose_name = "Forecast Model Config"
        verbose_name_plural = "Forecast Model Configs"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "target_type", "model_version"],
                name="unique_workspace_target_model_version",
            )
        ]

    def __str__(self):
        return f"{self.name} [{self.get_target_type_display()}] v{self.model_version}"


class ForecastRun(WorkspaceScopedModel):
    """
    Execution instance of training/evaluation for a forecast model configuration.
    Tracks training timestamps, dataset volume, evaluation metrics, and artifact path.
    """

    id = models.BigAutoField(primary_key=True)
    model_config = models.ForeignKey(
        ForecastModelConfig,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.PENDING,
        db_index=True,
    )
    training_start_at = models.DateTimeField(null=True, blank=True)
    training_end_at = models.DateTimeField(null=True, blank=True)
    job_parameters = models.JSONField(default=dict, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    cancel_requested = models.BooleanField(default=False)

    dataset_period_start = models.DateField(null=True, blank=True)
    dataset_period_end = models.DateField(null=True, blank=True)
    dataset_row_count = models.PositiveIntegerField(default=0)
    train_row_count = models.PositiveIntegerField(default=0)
    test_row_count = models.PositiveIntegerField(default=0)

    model_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="XGBoost test metrics: mae, rmse, mape, r2.",
    )
    baseline_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Naive persistence baseline metrics: naive_mae, naive_rmse, naive_mape.",
    )
    feature_importances = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature importance scores extracted from XGBoost.",
    )
    artifact_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Relative path to serialized model artifact within ml_models/forecasting/.",
    )
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forecast_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "forecasting_run"
        ordering = ["-created_at"]
        verbose_name = "Forecast Run"
        verbose_name_plural = "Forecast Runs"

    def __str__(self):
        return f"Run #{self.id} [{self.get_target_type_display()}] - {self.status}"


class ForecastResult(WorkspaceScopedModel):
    """
    Specific predicted data point on a future target date.
    Stores point forecast, prediction intervals, and actual value (for backtests).
    """

    id = models.BigAutoField(primary_key=True)
    forecast_run = models.ForeignKey(
        ForecastRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
        db_index=True,
    )
    forecast_date = models.DateField(db_index=True)
    predicted_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        help_text="Point prediction generated by model.",
    )
    lower_bound = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Lower interval bound (e.g. 95% confidence).",
    )
    upper_bound = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Upper interval bound (e.g. 95% confidence).",
    )
    actual_value = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual observed value when backtesting.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forecasting_result"
        ordering = ["forecast_date"]
        verbose_name = "Forecast Result"
        verbose_name_plural = "Forecast Results"
        constraints = [
            models.UniqueConstraint(
                fields=["forecast_run", "forecast_date"],
                name="unique_run_forecast_date",
            )
        ]

    def __str__(self):
        return f"{self.target_type} @ {self.forecast_date}: {self.predicted_value}"
