"""
Prediction and future horizon generation engine.
Implements safe model artifact loading, recursive multi-step forecasting,
and approximate 95% prediction bands based on historical test residual standard deviation.
"""

from decimal import Decimal
from pathlib import Path
from typing import List, Optional
import datetime
import pandas as pd
import numpy as np
from django.conf import settings
from django.db import transaction
import xgboost as xgb

from apps.forecasting.models import ForecastRun, ForecastResult, Granularity
from apps.forecasting.selectors import get_historical_timeseries
from apps.forecasting.features import recursive_feature_predictions


def load_model_artifact(artifact_path: str) -> xgb.XGBRegressor:
    """
    Safely loads a serialized XGBoost model JSON from the trusted artifacts directory.
    Rejects directory traversal attempts.
    """
    base_dir = Path(getattr(settings, "FORECASTING_ARTIFACTS_DIR", settings.BASE_DIR / "ml_models" / "forecasting")).resolve()
    target_path = (settings.BASE_DIR / artifact_path).resolve()

    # Security check: must resolve inside base_dir or BASE_DIR/ml_models
    if not target_path.is_relative_to(base_dir):
        raise PermissionError(f"Access to artifact path '{artifact_path}' outside trusted directory is prohibited.")

    if not target_path.exists():
        raise FileNotFoundError(f"Model artifact not found at '{target_path}'.")

    model = xgb.XGBRegressor()
    model.load_model(str(target_path))
    return model


def generate_future_forecast(
    forecast_run: ForecastRun,
    horizon_days: int = 14,
) -> List[ForecastResult]:
    """
    Generates point forecasts and approximate 95% prediction bands based on historical test
    residual standard deviation for future horizon dates.
    Uses recursive feature roll-forward based on observed history + successive predictions.

    Note:
    - This is an uncertainty visualization.
    - Recursive multi-step forecasts may accumulate error forward in time.
    - It is not a formally calibrated probabilistic interval.
    """
    if not forecast_run.artifact_path:
        raise ValueError("Cannot predict from a run without an artifact_path.")

    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or horizon_days < 1:
        raise ValueError("Forecast horizon must be a positive integer.")
    model = load_model_artifact(forecast_run.artifact_path)
    workspace = forecast_run.workspace
    target_type = forecast_run.target_type

    provenance = (forecast_run.job_parameters or {}).get("provenance", {})
    granularity = provenance.get("granularity", forecast_run.model_config.granularity)
    feature_config = provenance.get("feature_config", forecast_run.model_config.feature_config)
    # Snapshot configuration takes precedence over later edits to model_config.
    ts_df = get_historical_timeseries(workspace, target_type, granularity=granularity,
                                    dimensions=provenance.get("dimensions", (forecast_run.job_parameters or {}).get("dimensions", {})))
    if ts_df.empty:
        raise ValueError("No historical series available to anchor future predictions.")

    last_date = ts_df.index[-1]
    # horizon_days remains the existing number of forecast points. Weekly
    # configurations produce weekly points, not daily points from weekly totals.
    stride = 7 if granularity == Granularity.WEEKLY else 1
    dates = [last_date + datetime.timedelta(days=stride * step) for step in range(1, horizon_days + 1)]
    predictions = recursive_feature_predictions(model, ts_df, dates, feature_config,
                                               provenance.get("feature_columns"))

    # Obtain model test RMSE for interval estimation
    metrics = forecast_run.model_metrics or {}
    try:
        rmse = float(metrics.get("rmse"))
    except (TypeError, ValueError):
        rmse = None
    if rmse is not None and (not np.isfinite(rmse) or rmse < 0):
        rmse = None
    created_results = []
    for step, (target_date, pred_val) in enumerate(zip(dates, predictions), start=1):
        # Prediction intervals (growing uncertainty with step horizon)
        step_uncertainty = rmse * np.sqrt(1.0 + 0.05 * (step - 1)) if rmse is not None else None
        lower_bound = max(0.0, pred_val - 1.96 * step_uncertainty) if step_uncertainty is not None else None
        upper_bound = max(0.0, pred_val + 1.96 * step_uncertainty) if step_uncertainty is not None else None

        res = ForecastResult(
            workspace=workspace,
            forecast_run=forecast_run,
            target_type=target_type,
            forecast_date=target_date.date(),
            predicted_value=Decimal(str(round(pred_val, 2))),
            lower_bound=Decimal(str(round(lower_bound, 2))) if lower_bound is not None else None,
            upper_bound=Decimal(str(round(upper_bound, 2))) if upper_bound is not None else None,
        )
        created_results.append(res)

    # Never erase the last good result on prediction or persistence failure.
    # Lock serializes concurrent replacements of the same run.
    with transaction.atomic():
        ForecastRun.objects.select_for_update().get(pk=forecast_run.pk, workspace=workspace)
        ForecastResult.objects.filter(forecast_run=forecast_run, workspace=workspace).delete()
        ForecastResult.objects.bulk_create(created_results)
    return created_results
