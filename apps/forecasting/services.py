"""
High-level service orchestration for forecasting tasks, background execution,
and dashboard payload preparation.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import datetime
import logging
from django.utils import timezone
from django.db.models import Q

from apps.workspaces.models import Workspace, WorkspaceType
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    ForecastResult,
    TargetType,
    ModelType,
    Granularity,
    RunStatus,
)
from apps.forecasting.selectors import get_historical_timeseries
from apps.forecasting.training import train_forecast_model, validate_target_for_workspace
from apps.audit.services import log_audit_event


logger = logging.getLogger(__name__)


def get_default_target_for_workspace(workspace: Workspace) -> str:
    """Returns the primary target type appropriate for the workspace type."""
    if getattr(workspace, "workspace_type", "") == WorkspaceType.SERVICE:
        return TargetType.SERVICE_TICKET_VOLUME
    return TargetType.RETAIL_REVENUE


def get_or_create_default_config(workspace: Workspace, target_type: str) -> ForecastModelConfig:
    """Retrieves or provisions default configuration for the given workspace and target."""
    validate_target_for_workspace(workspace, target_type)

    cfg, _ = ForecastModelConfig.objects.get_or_create(
        workspace=workspace,
        target_type=target_type,
        model_version=1,
        defaults={
            "name": f"Default {target_type.replace('_', ' ').title()}",
            "model_type": ModelType.XGBOOST_REGRESSOR,
            "granularity": Granularity.DAILY,
            "feature_config": {
                "lags": [1, 7, 14],
                "rolling_windows": [7, 14],
                "calendar_features": True,
            },
            "training_config": {
                "n_estimators": 100,
                "max_depth": 4,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "test_size": 0.20,
            },
            "is_active": True,
            "model_version": 1,
        },
    )
    return cfg


def execute_training_job(
    workspace: Workspace,
    target_type: str,
    user=None,
    hyperparams: Optional[dict] = None,
    horizon_days: int = 14,
    is_async: bool = False,
    dimensions: Optional[dict] = None,
) -> ForecastRun:
    """
    Triggers model training. When is_async=True, persists a job for forecast_worker
    and returns immediately with a PENDING run record.
    """
    validate_target_for_workspace(workspace, target_type)
    config = get_or_create_default_config(workspace, target_type)
    if dimensions:
        get_historical_timeseries(workspace, target_type, dimensions=dimensions)

    if not is_async:
        run = train_forecast_model(
            workspace=workspace,
            target_type=target_type,
            model_config=config,
            user=user,
            hyperparams=hyperparams,
            horizon_days=horizon_days,
            dimensions=dimensions,
        )
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            log_audit_event(
                workspace=workspace,
                user=user,
                action="TRAIN_MODEL",
                entity_type="ForecastRun",
                entity_id=str(run.id),
                metadata={"target_type": target_type, "status": run.status, "metrics": run.model_metrics},
            )
        return run

    # A committed PENDING row is the durable queue. No web-process thread.
    run = ForecastRun.objects.create(
        workspace=workspace,
        model_config=config,
        target_type=target_type,
        status=RunStatus.PENDING,
        created_by=user if user and user.is_authenticated else None,
        job_parameters={"hyperparams": hyperparams or {}, "horizon_days": horizon_days,
                        "dimensions": dimensions or {}},
    )

    return run


def get_forecast_chart_data(
    workspace: Workspace,
    target_type: Optional[str] = None,
    history_days: int = 60,
    horizon_days: int = 14,
) -> Dict[str, Any]:
    """
    Builds a unified visual payload for Chart.js containing historical actuals,
    future predictions, approximate 95% prediction bands, baseline metrics, and feature importances.
    """
    if not target_type:
        target_type = get_default_target_for_workspace(workspace)

    validate_target_for_workspace(workspace, target_type)

    # 1. Historical actuals
    cutoff_date = (timezone.now() - datetime.timedelta(days=history_days)).date()
    ts_df = get_historical_timeseries(workspace, target_type, start_date=cutoff_date)
    if ts_df.empty:
        # Fallback to available historical sequence if data is from another date range
        ts_df = get_historical_timeseries(workspace, target_type)


    historical_points = [
        {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)}
        for d, v in zip(ts_df.index, ts_df["target"])
    ] if not ts_df.empty else []

    # 2. Latest completed run and its forecast results
    latest_run = (
        ForecastRun.objects.for_workspace(workspace)
        .filter(target_type=target_type, status=RunStatus.COMPLETED)
        .filter(Q(job_parameters__dimensions={}) | Q(job_parameters__dimensions__isnull=True))
        .order_by("-created_at")
        .first()
    )

    forecast_points = []
    model_metrics = {}
    baseline_metrics = {}
    feature_importances = []

    if latest_run:
        results = (
            ForecastResult.objects.for_workspace(workspace)
            .filter(forecast_run=latest_run)
            .order_by("forecast_date")[:horizon_days]
        )
        forecast_points = [
            {
                "date": r.forecast_date.strftime("%Y-%m-%d"),
                "predicted": float(r.predicted_value),
                "lower": float(r.lower_bound) if r.lower_bound is not None else None,
                "upper": float(r.upper_bound) if r.upper_bound is not None else None,
            }
            for r in results
        ]
        model_metrics = latest_run.model_metrics or {}
        baseline_metrics = latest_run.baseline_metrics or {}
        feature_importances = [
            {"feature": k, "importance": v}
            for k, v in (latest_run.feature_importances or {}).items()
        ]

    return {
        "workspace_code": workspace.code,
        "target_type": target_type,
        "run_id": latest_run.id if latest_run else None,
        "run_date": latest_run.created_at.strftime("%Y-%m-%d %H:%M") if latest_run else None,
        "historical": historical_points,
        "forecast": forecast_points,
        "metrics": model_metrics,
        "baseline_metrics": baseline_metrics,
        "feature_importances": feature_importances,
    }
