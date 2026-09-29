"""Offline synthetic revenue experiment, not a production ForecastRun.

Reuses application feature/metric implementations. Never connects to the DB.
Output must be a NEW directory. Explicit --dataset allows replay of a snapshot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import xgboost as xgb
from apps.forecasting.features import build_features, get_feature_column_names, DEFAULT_FEATURE_CONFIG
from apps.forecasting.evaluation import compute_metrics, generate_naive_baseline_predictions, generate_moving_average_baseline_predictions

PARAMS = dict(n_estimators=100, max_depth=4, learning_rate=0.05,
              subsample=0.8, colsample_bytree=0.8, random_state=42,
              objective="reg:squarederror", eval_metric="mae", n_jobs=1)


def synthetic_dataset():
    """Fixed seed and formula, selected before evaluating holdout."""
    rng = np.random.default_rng(20260924)
    dates = pd.date_range("2026-01-01", periods=180, freq="D")
    values = (1_000_000 + np.arange(180) * 4500
              + np.where(dates.dayofweek >= 5, 350_000, 0)
              + rng.normal(0, 120_000, 180)).round(0)
    return pd.DataFrame({"target": np.maximum(values, 0)}, index=dates)


def validate_dataset(frame):
    if list(frame.columns) != ["target"] or len(frame) < 90:
        raise ValueError("Require at least 90 daily rows and exactly one target column.")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Dates must be unique and chronological.")
    if not frame.index.equals(pd.date_range(frame.index[0], periods=len(frame), freq="D")):
        raise ValueError("Missing days must be resolved explicitly, not silently zero-filled.")
    if not np.isfinite(frame.target.to_numpy(dtype=float)).all() or (frame.target < 0).any():
        raise ValueError("Revenue must be finite and nonnegative.")


def run(output, dataset=None):
    frame = pd.read_csv(dataset, index_col="date", parse_dates=True) if dataset else synthetic_dataset()
    validate_dataset(frame)
    features = build_features(frame, DEFAULT_FEATURE_CONFIG)
    columns = get_feature_column_names(features)
    # Locked split: 60% training, 20% calibration, remaining 20% test.
    train_end, calibration_end = int(len(features) * .6), int(len(features) * .8)
    model = xgb.XGBRegressor(**PARAMS)
    model.fit(features.iloc[:train_end][columns], features.iloc[:train_end].target, verbose=False)
    calibration_pred = np.maximum(model.predict(features.iloc[train_end:calibration_end][columns]), 0)
    scale = float(np.sqrt(np.mean((features.iloc[train_end:calibration_end].target.to_numpy() - calibration_pred) ** 2)))
    test = features.iloc[calibration_end:]
    prediction = np.maximum(model.predict(test[columns]), 0)
    lag7 = generate_naive_baseline_predictions(features.target.to_numpy(), calibration_end, 7)
    ma7 = generate_moving_average_baseline_predictions(features.target.to_numpy(), calibration_end, 7)
    lower, upper = prediction - 1.96 * scale, prediction + 1.96 * scale
    covered = (test.target.to_numpy() >= lower) & (test.target.to_numpy() <= upper)
    results = {
        "model": compute_metrics(test.target.to_numpy(), prediction),
        "lag7": compute_metrics(test.target.to_numpy(), lag7),
        "moving_average7": compute_metrics(test.target.to_numpy(), ma7),
        "interval": {"scale_source": "earlier_calibration_partition_rmse", "scale": scale,
                     "z": 1.96, "covered": int(covered.sum()), "total": len(test),
                     "coverage": float(covered.mean()), "certified_calibration": False},
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    frame.to_csv(output / "dataset.csv", index_label="date")
    model.save_model(output / "model.json")
    pd.DataFrame({"actual": test.target, "prediction": prediction, "lag7": lag7, "ma7": ma7,
                  "lower": lower, "upper": upper, "covered": covered}).to_csv(output / "test_predictions.csv", index_label="date")
    pd.DataFrame({"actual": features.iloc[train_end:calibration_end].target,
                  "prediction": calibration_pred}).to_csv(output / "calibration_predictions.csv", index_label="date")
    (output / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False), encoding="utf-8")
    config = {"model": PARAMS, "features": DEFAULT_FEATURE_CONFIG,
              "split": {"train": train_end, "calibration": calibration_end-train_end, "test": len(test)},
              "feature_columns": columns, "evaluation": "one_step_observed_history", "unit": "VND",
              "validation": "calibration only, no hyperparameter search; test never used in fit"}
    (output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    manifest = {
        "dataset_kind": "synthetic_formula_v1" if dataset is None else "explicit_snapshot_replay",
        "seed": 20260924 if dataset is None else None, "rows": len(frame),
        "start": str(frame.index.min().date()), "end": str(frame.index.max().date()),
        "missing_policy": "reject missing days; no implicit fill",
        "scope": "offline revenue experiment; not production, not reproduction of Batch 44",
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "xgboost": xgb.__version__},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (Path(__file__), ROOT / "apps/forecasting/features.py", ROOT / "apps/forecasting/evaluation.py")},
        "files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.dataset), indent=2))
