"""Pure normalized MA7-anchored direct-horizon XGBoost helpers."""

import json
from datetime import timedelta

import numpy as np
import pandas as pd
import xgboost as xgb


FORMAT = 'alphatech_guarded_forecast_v1'
FULL_COLUMNS = (
    'lag_1', 'lag_7', 'lag_14', 'lag_28', 'mean_7', 'mean_14', 'mean_28',
    'mean_56', 'std_7', 'std_28', 'anchor_ratio', 'trend_28', 'trend_14',
    'horizon', 'day_of_week', 'day_of_month', 'month', 'is_weekend',
)
PARAM_DEFAULTS = {
    'objective': 'reg:absoluteerror', 'max_depth': 2, 'n_estimators': 200,
    'learning_rate': .05, 'subsample': 1., 'colsample_bytree': 1.,
    'reg_lambda': 1., 'random_state': 42, 'n_jobs': 1, 'eval_metric': 'mae',
}


def validate_history(history, granularity='DAILY', minimum=56):
    freq = 'D' if granularity == 'DAILY' else '7D' if granularity == 'WEEKLY' else None
    if (freq is None or not isinstance(history, pd.DataFrame) or list(history.columns) != ['target']
            or len(history) < minimum or not isinstance(history.index, pd.DatetimeIndex)
            or history.index.has_duplicates or not history.index.is_monotonic_increasing
            or not history.index.equals(pd.date_range(history.index[0], periods=len(history), freq=freq))):
        raise ValueError(f'Require at least {minimum} unique consecutive {granularity.lower()} target periods')
    values = history.target.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('History must contain finite nonnegative values')
    return values


def columns_for(mode):
    if mode not in ('none', 'full'):
        raise ValueError('Calendar mode must be none or full')
    return list(FULL_COLUMNS if mode == 'full' else FULL_COLUMNS[:-4])


def model_params(overrides=None):
    params = dict(PARAM_DEFAULTS)
    overrides = {} if overrides is None else overrides
    if not isinstance(overrides, dict):
        raise ValueError('params must be a mapping')
    if set(overrides) - {'n_estimators', 'max_depth', 'learning_rate'}:
        raise ValueError('Only n_estimators, max_depth and learning_rate may be overridden')
    for name, value in overrides.items():
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f'{name} must be numeric, not boolean')
        if name in ('n_estimators', 'max_depth'):
            if not isinstance(value, (int, np.integer)):
                raise ValueError(f'{name} must be an integer')
            low, high = (1, 500) if name == 'n_estimators' else (1, 10)
            if not low <= value <= high:
                raise ValueError(f'{name} is outside the supported range')
            value = int(value)
        else:
            if not isinstance(value, (int, float, np.number)) or not np.isfinite(value) or not .001 <= value <= 1:
                raise ValueError('learning_rate must be in [0.001, 1]')
            value = float(value)
        params[name] = value
    return params


def origin_features(values, origin_date, dates, granularity='DAILY', mode='full'):
    values = np.asarray(values, dtype=float)
    if len(values) < 56 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Features require 56 finite nonnegative history periods')
    freq = 'D' if granularity == 'DAILY' else '7D' if granularity == 'WEEKLY' else None
    dates = pd.DatetimeIndex(dates)
    delta = pd.Timedelta(days=1) if granularity == 'DAILY' else pd.Timedelta(days=7)
    expected = pd.date_range(pd.Timestamp(origin_date) + delta, periods=len(dates), freq=freq)
    if freq is None or not 1 <= len(dates) <= 14 or not dates.equals(expected):
        raise ValueError('Require 1..14 consecutive forecast dates after origin')
    means = {w: float(values[-w:].mean()) for w in (7, 14, 28, 56)}
    anchor = means[7]
    scale = max(anchor, means[28] / 4, 1.)
    row = {f'lag_{lag}': float(values[-lag]) / scale for lag in (1, 7, 14, 28)}
    row.update({f'mean_{window}': value / scale for window, value in means.items()})
    row.update({f'std_{window}': float(np.std(values[-window:])) / scale for window in (7, 28)})
    row.update(anchor_ratio=anchor / scale, trend_28=(anchor - means[28]) / scale,
               trend_14=(anchor - means[14]) / scale)
    frame = pd.DataFrame([dict(row) for _ in dates])
    frame['horizon'] = np.arange(1, len(dates) + 1)
    frame['day_of_week'] = dates.dayofweek
    frame['day_of_month'] = dates.day
    frame['month'] = dates.month
    frame['is_weekend'] = (dates.dayofweek >= 5).astype(int)
    return frame[columns_for(mode)], anchor, scale


def supervised_pairs(history, granularity='DAILY'):
    values = validate_history(history, granularity)
    frames, targets, weights = [], [], []
    for position in range(55, len(values) - 1):
        count = min(14, len(values) - position - 1)
        dates = history.index[position + 1:position + 1 + count]
        frame, anchor, scale = origin_features(values[:position + 1], history.index[position], dates,
                                               granularity, 'full')
        frames.append(frame)
        targets.extend((values[position + 1:position + 1 + count] - anchor) / scale)
        weights.extend([scale] * count)
    if not frames:
        raise ValueError('Training needs at least one target after a 56-period origin')
    weights = np.asarray(weights, dtype=float)
    weights /= float(np.median(weights))
    return pd.concat(frames, ignore_index=True), np.asarray(targets), weights


def fit_direct(history, mode='full', params=None, granularity='DAILY'):
    frame, target, weights = supervised_pairs(history, granularity)
    columns = columns_for(mode)
    model = xgb.XGBRegressor(**(model_params() if params is None else params))
    model.fit(frame[columns], target, sample_weight=weights, verbose=False)
    return model


def predict_direct(model, values, origin_date, dates, granularity='DAILY', mode='full'):
    frame, anchor, scale = origin_features(values, origin_date, dates, granularity, mode)
    residual = np.asarray(model.predict(frame), dtype=float)
    if residual.shape != (len(frame),) or not np.isfinite(residual).all():
        raise ValueError('Residual model must produce finite predictions for each horizon')
    result = np.maximum(0., anchor + scale * residual)
    if not np.isfinite(result).all():
        raise ValueError('Reconstructed predictions must be finite')
    return result


def booster_to_json_dict(model):
    raw = model.get_booster().save_raw(raw_format='json')
    return json.loads(bytes(raw).decode('utf-8'))


def booster_from_json_dict(payload, params=None):
    if not isinstance(payload, dict):
        raise ValueError('Booster JSON must be an object')
    model = xgb.XGBRegressor(**(model_params() if params is None else params))
    model.load_model(bytearray(json.dumps(payload, allow_nan=False, separators=(',', ':')).encode('utf-8')))
    return model
