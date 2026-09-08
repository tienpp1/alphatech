"""
Evaluation metrics and Naive Baseline benchmarking for time-series forecasting.
Computes MAE, RMSE, MAPE, R2, and relative performance gain over naive persistence.
"""

from typing import Dict, Tuple
import numpy as np


def rolling_origin_backtest(feature_df, model_factory, folds=3):
    """Expanding-window, one-step observed-history evaluation, never shuffled.

    Lag features use only prior observed values; this is not an evaluation of
    a recursive multi-day horizon. The final holdout remains excluded by caller.
    """
    from .features import get_feature_column_names
    columns = get_feature_column_names(feature_df)
    block = max(1, len(feature_df) // (folds + 2))
    results = []
    for fold in range(folds):
        end = len(feature_df) - (folds - fold - 1) * block
        start = end - block
        if start < 5:
            continue
        train, test = feature_df.iloc[:start], feature_df.iloc[start:end]
        model = model_factory()
        model.fit(train[columns], train["target"])
        predicted = np.maximum(model.predict(test[columns]), 0)
        results.append({"train_end": str(train.index[-1].date()),
                        "test_start": str(test.index[0].date()), "test_end": str(test.index[-1].date()),
                        "train_rows": len(train), "test_rows": len(test),
                        "metrics": compute_metrics(test["target"].values, predicted)})
    return {"method": "expanding_window_one_step_observed_history", "folds": results}


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error: mean(|y_true - y_pred|)"""
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)))


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error: sqrt(mean((y_true - y_pred)^2))"""
    if len(y_true) == 0:
        return 0.0
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def compute_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Mean Absolute Percentage Error calculated over non-zero actual points
    to avoid infinite/skewed percentage distortions on zero-activity days.
    """
    if len(y_true) == 0:
        return 0.0
    non_zero = np.abs(y_true) > 1e-3
    if np.any(non_zero):
        return float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100.0)
    return 0.0



def compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination R^2."""
    if len(y_true) <= 1:
        return 0.0
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0.0:
        return 0.0
    ss_res = np.sum((y_true - y_pred) ** 2)
    return float(1.0 - (ss_res / ss_tot))


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes standard evaluation suite."""
    return {
        "mae": round(compute_mae(y_true, y_pred), 2),
        "rmse": round(compute_rmse(y_true, y_pred), 2),
        "mape": round(compute_mape(y_true, y_pred), 2),
        "r2": round(compute_r2(y_true, y_pred), 4),
    }


def generate_naive_baseline_predictions(
    y_full: np.ndarray,
    test_start_idx: int,
    seasonality_lag: int = 7,
) -> np.ndarray:
    """
    Generates naive persistence predictions for test set indices.
    For each test point t, uses y[t - seasonality_lag] (or y[t-1] if lag not available).
    """
    n_total = len(y_full)
    test_len = n_total - test_start_idx
    if test_len <= 0:
        return np.array([])

    preds = []
    for idx in range(test_start_idx, n_total):
        target_lag_idx = idx - seasonality_lag
        if target_lag_idx >= 0:
            preds.append(y_full[target_lag_idx])
        elif idx - 1 >= 0:
            preds.append(y_full[idx - 1])
        else:
            preds.append(y_full[0])

    return np.array(preds)


def compare_model_against_baseline(
    model_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
) -> Dict[str, float]:
    """
    Calculates percentage improvement of model metrics compared to naive baseline.
    Positive value indicates model outperforms baseline (e.g. +25.4% lower MAE).
    """
    comp = {}
    for metric_name in ["mae", "rmse", "mape"]:
        base_val = baseline_metrics.get(metric_name) or baseline_metrics.get(f"naive_{metric_name}", 0.0)
        mod_val = model_metrics.get(metric_name, 0.0)
        if base_val and base_val > 0:
            # Reduction in error is positive improvement
            improvement = ((base_val - mod_val) / base_val) * 100.0
            comp[f"{metric_name}_improvement_pct"] = round(improvement, 2)
        else:
            comp[f"{metric_name}_improvement_pct"] = 0.0
    return comp
