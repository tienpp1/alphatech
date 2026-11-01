"""Offline MA7-anchored, level-normalized direct-horizon XGBoost.

This is an experimental residual model, NOT a change to production forecasting.
Each forecast horizon uses the same observed origin snapshot, never future truth.
"""
import numpy as np
import pandas as pd
import xgboost as xgb

MIN_HISTORY = 56
MAX_HORIZON = 14


def model_params():
    return {'objective': 'reg:absoluteerror', 'max_depth': 2, 'n_estimators': 200,
            'learning_rate': .05, 'subsample': 1., 'colsample_bytree': 1.,
            'reg_lambda': 1., 'random_state': 42, 'n_jobs': 1, 'eval_metric': 'mae'}


def validate_history(history):
    if (not isinstance(history, pd.DataFrame) or list(history.columns) != ['target']
            or len(history) < MIN_HISTORY or not isinstance(history.index, pd.DatetimeIndex)
            or history.index.has_duplicates or not history.index.is_monotonic_increasing
            or not history.index.equals(pd.date_range(history.index[0], periods=len(history), freq='D'))):
        raise ValueError('Require at least56 unique consecutive daily target observations')
    values = history.target.to_numpy(float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('History must be finite nonnegative observations')
    return values


def origin_features(history, dates):
    """Dimensionless features and reconstruction units, using only known history."""
    values = validate_history(history)
    dates = pd.DatetimeIndex(dates)
    if (not 1 <= len(dates) <= MAX_HORIZON or not dates.equals(pd.date_range(
            history.index[-1] + pd.Timedelta(days=1), periods=len(dates), freq='D'))):
        raise ValueError('Require1..14 consecutive dates immediately after origin')
    means = {window: float(np.mean(values[-window:])) for window in (7, 14, 28, 56)}
    anchor = means[7]
    scale = max(anchor, means[28] / 4., 1.)
    features = {f'lag_{lag}': float(values[-lag]) / scale for lag in (1, 7, 14, 28)}
    features.update({f'mean_{window}': value / scale for window, value in means.items()})
    features.update({f'std_{window}': float(np.std(values[-window:])) / scale for window in (7, 28)})
    features.update(anchor_ratio=anchor / scale, trend_28=(anchor - means[28]) / scale,
                    trend_14=(anchor - means[14]) / scale)
    frame = pd.DataFrame([features.copy() for _ in dates])
    frame['horizon'] = np.arange(1, len(dates) + 1)
    frame['day_of_week'] = dates.dayofweek
    frame['day_of_month'] = dates.day
    frame['month'] = dates.month
    frame['is_weekend'] = (dates.dayofweek >= 5).astype(int)
    return frame, anchor, scale


def supervised_pairs(history, horizon=MAX_HORIZON):
    """Expand available origin→target pairs; both ends lie inside fit history."""
    values = validate_history(history)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= MAX_HORIZON:
        raise ValueError('Training horizon must be1..14')
    frames, targets, scales, trace = [], [], [], []
    for position in range(MIN_HISTORY - 1, len(history) - 1):
        count = min(horizon, len(history) - position - 1)
        dates = history.index[position + 1:position + 1 + count]
        features, anchor, scale = origin_features(history.iloc[:position + 1], dates)
        frames.append(features)
        targets.extend((values[position + 1:position + 1 + count] - anchor) / scale)
        scales.extend([scale] * count)
        trace.extend({'origin': str(history.index[position].date()), 'target_date': str(date.date()),
                      'horizon': step, 'anchor': anchor, 'scale': scale}
                     for step, date in enumerate(dates, 1))
    if not frames:
        raise ValueError('Training requires at least one known target after origin')
    weights = np.asarray(scales, float)
    weights /= float(np.median(weights))
    return (pd.concat(frames, ignore_index=True), np.asarray(targets, float), weights,
            pd.DataFrame(trace))


def fit_direct(history, params):
    features, target, weights, _ = supervised_pairs(history)
    model = xgb.XGBRegressor(**params)
    model.fit(features, target, sample_weight=weights, verbose=False)
    return model


def load_direct(path):
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model


def predict_direct(model, history, dates, alpha=1.):
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha <= 1:
        raise ValueError('Correction alpha must be in(0,1]; zero is not XGBoost')
    features, anchor, scale = origin_features(history, dates)
    residual = np.asarray(model.predict(features), float)
    if residual.shape != (len(features),) or not np.isfinite(residual).all():
        raise ValueError('Residual model must return one finite value per horizon')
    result = np.maximum(0., anchor + float(alpha) * scale * residual)
    if not np.isfinite(result).all():
        raise ValueError('Reconstructed predictions must remain finite')
    return result
