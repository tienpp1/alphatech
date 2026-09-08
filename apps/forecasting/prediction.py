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
import xgboost as xgb

from apps.forecasting.models import ForecastRun, ForecastResult
from apps.forecasting.selectors import get_historical_timeseries
from apps.forecasting.features import build_features, get_feature_column_names


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

    model = load_model_artifact(forecast_run.artifact_path)
    workspace = forecast_run.workspace
    target_type = forecast_run.target_type

    # 1. Fetch latest observed historical time-series
    ts_df = get_historical_timeseries(workspace, target_type, granularity=forecast_run.model_config.granularity,
                                    dimensions=forecast_run.job_parameters.get("dimensions", {}))
    if ts_df.empty:
        raise ValueError("No historical series available to anchor future predictions.")

    # Historical series as a mutable dictionary date -> value
    history_map = {d.date(): val for d, val in zip(ts_df.index, ts_df["target"])}
    last_date = max(history_map.keys())

    # Obtain model test RMSE for interval estimation
    metrics = forecast_run.model_metrics or {}
    rmse = float(metrics.get("rmse", 1.0))
    if rmse <= 0:
        rmse = 1.0

    # Delete existing future results for this specific run to ensure idempotency
    ForecastResult.objects.filter(forecast_run=forecast_run).delete()

    created_results = []
    current_date = last_date

    # Feature columns used during training
    dummy_feat = build_features(ts_df, feature_config=forecast_run.model_config.feature_config)
    feature_cols = get_feature_column_names(dummy_feat)

    for step in range(1, horizon_days + 1):
        target_date = last_date + datetime.timedelta(days=step)

        # Construct single feature row for target_date
        row_dict = {}
        # Lags: look back from target_date
        for lag in [1, 7, 14]:
            lag_date = target_date - datetime.timedelta(days=lag)
            row_dict[f"lag_{lag}"] = history_map.get(lag_date, 0.0)

        # Rolling statistics: computed over recent history up to target_date - 1 day
        recent_7 = [
            history_map.get(target_date - datetime.timedelta(days=d), 0.0)
            for d in range(1, 8)
        ]
        row_dict["rolling_mean_7"] = float(np.mean(recent_7)) if recent_7 else 0.0
        row_dict["rolling_std_7"] = float(np.std(recent_7)) if len(recent_7) > 1 else 0.0

        recent_14 = [
            history_map.get(target_date - datetime.timedelta(days=d), 0.0)
            for d in range(1, 15)
        ]
        row_dict["rolling_mean_14"] = float(np.mean(recent_14)) if recent_14 else 0.0

        # Calendar features
        row_dict["day_of_week"] = target_date.weekday()
        row_dict["day_of_month"] = target_date.day
        row_dict["month"] = target_date.month
        row_dict["week_of_year"] = int(target_date.isocalendar()[1])
        row_dict["is_weekend"] = 1 if target_date.weekday() >= 5 else 0

        # Build 1-row DataFrame aligned with training features
        X_step = pd.DataFrame([row_dict])[feature_cols]

        # Point prediction
        pred_val = float(model.predict(X_step)[0])
        # Non-negative clamping (business metrics cannot be negative)
        pred_val = max(0.0, pred_val)

        # Store in roll-forward map for subsequent lags
        history_map[target_date] = pred_val

        # Prediction intervals (growing uncertainty with step horizon)
        step_uncertainty = rmse * np.sqrt(1.0 + 0.05 * (step - 1))
        lower_bound = max(0.0, pred_val - 1.96 * step_uncertainty)
        upper_bound = max(0.0, pred_val + 1.96 * step_uncertainty)

        res = ForecastResult.objects.create(
            workspace=workspace,
            forecast_run=forecast_run,
            target_type=target_type,
            forecast_date=target_date,
            predicted_value=Decimal(str(round(pred_val, 2))),
            lower_bound=Decimal(str(round(lower_bound, 2))),
            upper_bound=Decimal(str(round(upper_bound, 2))),
        )
        created_results.append(res)

    return created_results
