"""
XGBoost training pipeline with chronological split, naive baseline comparison,
and safe model artifact persistence.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import hashlib
import os
import datetime
import platform
import django
import pandas as pd
import numpy as np
from django.utils import timezone
from django.conf import settings
from django.db import transaction
import xgboost as xgb

from apps.workspaces.models import Workspace, WorkspaceType
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    RunStatus,
    TargetType,
    ModelType,
    Granularity,
)
from apps.forecasting.selectors import get_historical_timeseries
from apps.forecasting.features import build_features, get_feature_column_names, DEFAULT_FEATURE_CONFIG
from apps.forecasting.evaluation import (
    compute_metrics,
    compute_interval_coverage,
    generate_naive_baseline_predictions,
    generate_moving_average_baseline_predictions,
    compare_model_against_baseline,
    rolling_origin_backtest,
)


def validate_target_for_workspace(workspace: Workspace, target_type: str) -> None:
    """Ensures target type aligns with workspace operational domain."""
    ws_type = getattr(workspace, "workspace_type", "")
    if ws_type == WorkspaceType.RETAIL:
        if target_type not in (TargetType.RETAIL_REVENUE, TargetType.RETAIL_ORDER_VOLUME, TargetType.RETAIL_PRODUCT_DEMAND):
            raise ValueError(f"Retail workspace '{workspace.code}' only supports RETAIL_REVENUE, RETAIL_ORDER_VOLUME, and RETAIL_PRODUCT_DEMAND.")
    elif ws_type == WorkspaceType.SERVICE:
        if target_type != TargetType.SERVICE_TICKET_VOLUME:
            raise ValueError(f"Service workspace '{workspace.code}' only supports SERVICE_TICKET_VOLUME.")


def chronological_split(
    feature_df: pd.DataFrame,
    test_size: float = 0.20,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, int]:
    """
    Splits time-series data chronologically.
    Strict invariant: Train indices strictly precede Test indices.
    """
    n_rows = len(feature_df)
    test_rows = max(1, int(n_rows * test_size))
    split_idx = n_rows - test_rows

    feature_cols = get_feature_column_names(feature_df)

    X_train = feature_df.iloc[:split_idx][feature_cols]
    y_train = feature_df.iloc[:split_idx]["target"]

    X_test = feature_df.iloc[split_idx:][feature_cols]
    y_test = feature_df.iloc[split_idx:][feature_cols + ["target"]]["target"]

    return X_train, X_test, y_train, y_test, split_idx


def build_run_provenance(
    timeseries: pd.DataFrame,
    *,
    workspace: Workspace,
    target_type: str,
    model_config: ForecastModelConfig,
    feature_config: dict,
    training_config: dict,
    horizon_days: int,
    dimensions: dict,
    train_rows: Optional[int] = None,
    test_rows: Optional[int] = None,
) -> dict:
    """Build reproducibility metadata without storing source business data."""
    hashed_rows = pd.util.hash_pandas_object(timeseries, index=True).values.tobytes()
    data_fingerprint = hashlib.sha256(hashed_rows).hexdigest()
    attrs = getattr(timeseries, "attrs", {}) or {}
    return {
        "workspace_code": workspace.code,
        "target_type": target_type,
        "model_config_id": model_config.pk,
        "model_version": model_config.model_version,
        "granularity": model_config.granularity,
        "dimensions": dimensions or {},
        "horizon_days": int(horizon_days),
        "feature_config": feature_config or {},
        "source_sha256": {
            name: hashlib.sha256((settings.BASE_DIR / "apps" / "forecasting" / name).read_bytes()).hexdigest()
            for name in ("training.py", "selectors.py", "features.py", "evaluation.py")
        },
        "training_config": training_config or {},
        "dataset": {
            "period_start": str(timeseries.index.min().date()),
            "period_end": str(timeseries.index.max().date()),
            "row_count": int(len(timeseries)),
            "source_observation_count": int(attrs.get("source_observation_count", len(timeseries))),
            "missing_period_count": int(attrs.get("missing_period_count", 0)),
            "missing_period_policy": attrs.get("missing_period_policy", "unknown"),
            "source_frequency": attrs.get("source_frequency", model_config.granularity),
            "fingerprint_sha256": data_fingerprint,
        },
        "split": {
            "test_size": training_config.get("test_size"),
            "train_rows": train_rows,
            "test_rows": test_rows,
            "method": "chronological",
        },
        "runtime": {
            "python": platform.python_version(),
            "django": django.get_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "xgboost": getattr(xgb, "__version__", "unknown"),
            "code_revision": (
                os.getenv("GIT_COMMIT")
                or os.getenv("RENDER_GIT_COMMIT")
                or os.getenv("COMMIT_SHA")
                or "unknown"
            ),
        },
    }


def train_forecast_model(
    workspace: Workspace,
    target_type: str,
    model_config: Optional[ForecastModelConfig] = None,
    user=None,
    hyperparams: Optional[dict] = None,
    horizon_days: int = 14,
    run: Optional[ForecastRun] = None,
    lease_token=None,
    dimensions=None,
) -> ForecastRun:
    """
    Executes end-to-end training of an XGBoost forecasting model for the active workspace.
    Saves model artifact and generates future horizon predictions.
    """
    validate_target_for_workspace(workspace, target_type)

    if run is not None and model_config is None:
        model_config = run.model_config

    if model_config is None:
        model_config, _ = ForecastModelConfig.objects.get_or_create(
            workspace=workspace,
            target_type=target_type,
            defaults={
                "name": f"Default {target_type} Forecaster",
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

    if run is None:
        run = ForecastRun.objects.create(
            workspace=workspace,
            model_config=model_config,
            target_type=target_type,
            status=RunStatus.RUNNING,
            training_start_at=timezone.now(),
            created_by=user if user and user.is_authenticated else None,
            job_parameters={"dimensions": dimensions or {}},
        )
    else:
        if run.workspace_id != workspace.id or run.model_config_id != model_config.id or run.target_type != target_type:
            raise ValueError("Existing ForecastRun does not match the requested workspace, model config, and target.")
        with transaction.atomic():
            locked = ForecastRun.objects.select_for_update().get(pk=run.pk)
            if lease_token and (locked.lease_token != lease_token or locked.status != RunStatus.RUNNING
                                or locked.cancel_requested or locked.lease_expires_at <= timezone.now()):
                raise ValueError("FORECAST_LEASE_LOST")
            if not lease_token and locked.status not in (RunStatus.PENDING, RunStatus.RUNNING):
                raise ValueError("FORECAST_RUN_NOT_PENDING")
            run.status = RunStatus.RUNNING
            run.training_start_at = timezone.now()
            run.training_end_at = None
            run.error_message = ""
            run.save(update_fields=["status", "training_start_at", "training_end_at", "error_message"])

    try:
        # 1. Fetch historical timeseries
        ts_df = get_historical_timeseries(workspace, target_type, granularity=model_config.granularity,
                                        dimensions=run.job_parameters.get("dimensions", {}))
        if ts_df.empty or len(ts_df) < 20:
            raise ValueError(f"Insufficient historical data ({len(ts_df)} rows). At least 20 continuous data points required for training.")

        run.dataset_period_start = ts_df.index.min().date()
        run.dataset_period_end = ts_df.index.max().date()
        run.dataset_row_count = len(ts_df)

        # 2. Build feature matrix and retain the effective training settings.
        feature_cfg = {**DEFAULT_FEATURE_CONFIG, **(model_config.feature_config or {})}
        train_cfg = {**(model_config.training_config or {}), **(hyperparams or {})}
        dimensions = run.job_parameters.get("dimensions", {}) or {}
        provenance = build_run_provenance(
            ts_df,
            workspace=workspace,
            target_type=target_type,
            model_config=model_config,
            feature_config=feature_cfg,
            training_config=train_cfg,
            horizon_days=horizon_days,
            dimensions=dimensions,
        )
        run.job_parameters = {**(run.job_parameters or {}), "provenance": provenance}
        # Publish metadata with results only after the final lease check.
        feat_df = build_features(ts_df, feature_config=feature_cfg, drop_na=True)
        if len(feat_df) < 10:
            raise ValueError("Insufficient rows remaining after lag feature calculation. Need more historical data.")

        # 3. Chronological split
        test_size = float(train_cfg.get("test_size", getattr(settings, "FORECAST_DEFAULT_TEST_SIZE", 0.20)))

        X_train, X_test, y_train, y_test, split_idx = chronological_split(feat_df, test_size=test_size)
        run.train_row_count = len(X_train)
        run.test_row_count = len(X_test)
        provenance["split"].update(
            {
                "test_size": test_size,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "train_start": X_train.index.min().isoformat(),
                "train_end": X_train.index.max().isoformat(),
                "test_start": X_test.index.min().isoformat(),
                "test_end": X_test.index.max().isoformat(),
                "validation": "no_separate_validation_partition",
                "evaluation": "one_step_observed_history",
            }
        )
        run.job_parameters = {**(run.job_parameters or {}), "provenance": provenance}

        # 4. Naive Baseline benchmarking on test partition
        y_full = feat_df["target"].values
        baseline_preds = generate_naive_baseline_predictions(
            y_full=y_full,
            test_start_idx=split_idx,
            seasonality_lag=7,
        )
        base_metrics = compute_metrics(y_test.values, baseline_preds)
        moving_average_preds = generate_moving_average_baseline_predictions(
            y_full=y_full,
            test_start_idx=split_idx,
            window=7,
        )
        moving_average_metrics = compute_metrics(y_test.values, moving_average_preds)
        run.baseline_metrics = {
            "naive_mae": base_metrics["mae"],
            "naive_rmse": base_metrics["rmse"],
            "naive_mape": base_metrics["mape"],
            "naive_r2": base_metrics["r2"],
            "moving_average_7_mae": moving_average_metrics["mae"],
            "moving_average_7_rmse": moving_average_metrics["rmse"],
            "moving_average_7_mape": moving_average_metrics["mape"],
            "moving_average_7_r2": moving_average_metrics["r2"],
        }

        # 5. Train XGBoost Regressor
        n_estimators = int(train_cfg.get("n_estimators", getattr(settings, "FORECAST_DEFAULT_ESTIMATORS", 100)))
        max_depth = int(train_cfg.get("max_depth", getattr(settings, "FORECAST_DEFAULT_MAX_DEPTH", 4)))
        learning_rate = float(train_cfg.get("learning_rate", getattr(settings, "FORECAST_DEFAULT_LEARNING_RATE", 0.05)))
        subsample = float(train_cfg.get("subsample", 0.8))
        colsample_bytree = float(train_cfg.get("colsample_bytree", 0.8))

        model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            random_state=42,
            objective="reg:squarederror",
            eval_metric="mae",
        )
        provenance["training_config"] = {
            "n_estimators": n_estimators, "max_depth": max_depth,
            "learning_rate": learning_rate, "subsample": subsample,
            "colsample_bytree": colsample_bytree, "random_state": 42,
            "objective": "reg:squarederror", "eval_metric": "mae",
            "test_size": test_size,
        }
        provenance["feature_columns"] = list(X_train.columns)
        provenance["dataset"]["unit"] = {
            TargetType.RETAIL_REVENUE: "VND",
            TargetType.RETAIL_ORDER_VOLUME: "orders",
            TargetType.RETAIL_PRODUCT_DEMAND: "item_units",
            TargetType.SERVICE_TICKET_VOLUME: "tickets",
        }[target_type]

        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # 6. Evaluate Model on Test Partition
        test_preds = model.predict(X_test)
        # Clamping at zero for business targets (revenue, counts cannot be negative)
        test_preds = np.maximum(test_preds, 0.0)

        mod_metrics = compute_metrics(y_test.values, test_preds)
        interval_coverage = compute_interval_coverage(
            y_test.values,
            test_preds,
            mod_metrics["rmse"],
        )
        comparison = compare_model_against_baseline(mod_metrics, run.baseline_metrics)
        run.model_metrics = {**mod_metrics, **comparison}
        run.model_metrics.update(
            {
                "interval_coverage": round(interval_coverage, 4) if interval_coverage is not None else None,
                "interval_nominal_coverage": 0.95,
                "interval_evaluation": "one_step_holdout_diagnostic_using_holdout_rmse",
            }
        )
        run.model_metrics["backtest"] = rolling_origin_backtest(
            feat_df.iloc[:split_idx], lambda: xgb.XGBRegressor(**model.get_params()),
        )

        # 7. Extract Feature Importances
        feature_cols = get_feature_column_names(feat_df)
        raw_importances = model.feature_importances_
        importances_dict = {
            feat_name: round(float(imp), 4)
            for feat_name, imp in sorted(
                zip(feature_cols, raw_importances),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        run.feature_importances = importances_dict

        # 8. Save Model Artifact to disk
        artifacts_dir = getattr(settings, "FORECASTING_ARTIFACTS_DIR", settings.BASE_DIR / "ml_models" / "forecasting")
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        artifact_filename = f"{workspace.id}_{target_type}_run_{run.id}_{lease_token or 'sync'}.json"
        full_artifact_path = artifacts_dir / artifact_filename
        model.save_model(str(full_artifact_path))
        provenance["artifact_sha256"] = hashlib.sha256(full_artifact_path.read_bytes()).hexdigest()

        run.artifact_path = f"ml_models/forecasting/{artifact_filename}"
        # Publish results and completion together, only while this attempt owns
        # the lease. A killed/replaced worker can never publish stale results.
        with transaction.atomic():
            locked = ForecastRun.objects.select_for_update().get(pk=run.pk)
            if lease_token and (locked.lease_token != lease_token or locked.status != RunStatus.RUNNING
                                or locked.cancel_requested or locked.lease_expires_at <= timezone.now()):
                raise ValueError("FORECAST_LEASE_LOST")
            from apps.forecasting.prediction import generate_future_forecast
            generate_future_forecast(run, horizon_days=horizon_days)
            run.status = RunStatus.COMPLETED
            run.training_end_at = timezone.now()
            run.lease_token = None
            run.lease_expires_at = None
            run.save()

        return run

    except Exception as e:
        if lease_token:
            from .queue import finish_failed
            finish_failed(run.pk, lease_token, "TRAINING_FAILED")
            raise
        run.status = RunStatus.FAILED
        run.error_message = str(e)
        run.training_end_at = timezone.now()
        run.save()
        raise
