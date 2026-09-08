"""
Feature Engineering for Time-Series Forecasting.
Constructs lag features, shifted rolling statistics, and calendar variables
with strict guarantees against future target leakage.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


DEFAULT_FEATURE_CONFIG = {
    "lags": [1, 7, 14],
    "rolling_windows": [7, 14],
    "calendar_features": True,
}


def build_features(
    df: pd.DataFrame,
    feature_config: Optional[dict] = None,
    drop_na: bool = True,
) -> pd.DataFrame:
    """
    Transforms a univariate time-series DataFrame with a 'target' column
    into a supervised tabular feature matrix.

    CRITICAL LEAKAGE GUARD:
    All rolling statistics are computed on df['target'].shift(1).
    A prediction at day t only ever sees historical data up to day t-1.
    """
    if df.empty or "target" not in df.columns:
        return pd.DataFrame()

    cfg = {**DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    out = df.copy()

    lags = cfg.get("lags", [1, 7, 14])
    rolling_windows = cfg.get("rolling_windows", [7, 14])
    include_calendar = cfg.get("calendar_features", True)

    # 1. Lag Features (values from previous periods)
    for lag in lags:
        out[f"lag_{lag}"] = out["target"].shift(lag)

    # 2. Shifted Rolling Statistics (moving average / volatility up to t-1)
    # Using shift(1) ensures the current day's target is NOT included in the window
    shifted_target = out["target"].shift(1)
    for win in rolling_windows:
        out[f"rolling_mean_{win}"] = shifted_target.rolling(window=win, min_periods=1).mean()
        if win <= 7:
            out[f"rolling_std_{win}"] = shifted_target.rolling(window=win, min_periods=2).std().fillna(0.0)

    # 3. Calendar & Temporal Features
    if include_calendar:
        out["day_of_week"] = out.index.dayofweek
        out["day_of_month"] = out.index.day
        out["month"] = out.index.month
        out["week_of_year"] = out.index.isocalendar().week.astype(int)
        out["is_weekend"] = (out.index.dayofweek >= 5).astype(int)

    # 4. Clean unpopulated initial lag rows
    if drop_na:
        max_lag = max(lags) if lags else 1
        out = out.iloc[max_lag:].copy()

    return out


def get_feature_column_names(df: pd.DataFrame) -> List[str]:
    """Returns all engineered feature column names excluding 'target'."""
    return [c for c in df.columns if c != "target"]
