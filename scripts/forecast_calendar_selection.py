"""Pure XGBoost calendar-subset selection. Offline only; no V2 source mutation."""
from numbers import Real

import numpy as np
import pandas as pd
import xgboost as xgb

from scripts.forecast_level_adaptive import model_params, supervised_pairs

MODES = ('none', 'weekly', 'full')
FULL_COLUMNS = ('lag_1', 'lag_7', 'lag_14', 'lag_28', 'mean_7', 'mean_14', 'mean_28',
                'mean_56', 'std_7', 'std_28', 'anchor_ratio', 'trend_28', 'trend_14',
                'horizon', 'day_of_week', 'day_of_month', 'month', 'is_weekend')


def columns_for(mode):
    if mode not in MODES:
        raise ValueError('Unknown calendar feature mode')
    omitted = ({'day_of_week', 'day_of_month', 'month', 'is_weekend'} if mode == 'none'
               else {'day_of_month', 'month'} if mode == 'weekly' else set())
    return [name for name in FULL_COLUMNS if name not in omitted]


class CalendarModel:
    """Preserve the fitted subset when the unchanged V2 forecaster sends fullX."""
    def __init__(self, estimator, mode):
        self.columns = columns_for(mode)
        if list(estimator.feature_names_in_) != self.columns:
            raise ValueError('Saved model feature schema does not match calendar mode')
        self.estimator, self.mode = estimator, mode

    def predict(self, features):
        if not isinstance(features, pd.DataFrame) or not set(self.columns).issubset(features.columns):
            raise ValueError('Missing required fitted features')
        selected = features[self.columns]
        if not np.isfinite(selected.to_numpy(float)).all():
            raise ValueError('Fitted feature subset must be finite')
        return self.estimator.predict(selected)

    def save_model(self, path):
        self.estimator.save_model(path)


def fit_mode(history, mode, params=None):
    columns = columns_for(mode)
    features, target, weights, _ = supervised_pairs(history)
    if tuple(features.columns) != FULL_COLUMNS:
        raise ValueError('V2 feature contract changed; do not silently remap model')
    estimator = xgb.XGBRegressor(**(model_params() if params is None else params))
    estimator.fit(features[columns], target, sample_weight=weights, verbose=False)
    return CalendarModel(estimator, mode)


def load_mode(path):
    estimator = xgb.XGBRegressor()
    estimator.load_model(path)
    names = list(estimator.feature_names_in_)
    for mode in MODES:
        if names == columns_for(mode):
            return CalendarModel(estimator, mode)
    raise ValueError('Unrecognized saved calendar schema')


def choose_mode(losses):
    """Fixed one-SE simplification heuristic; not a statistical guarantee."""
    if not isinstance(losses, dict) or set(losses) != set(MODES):
        raise ValueError('Require complete three-mode validation evidence')
    means = {}
    for mode in MODES:
        values = losses[mode]
        if (not isinstance(values, (list, tuple)) or len(values) != 10 or
                any(isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
                    or not np.isfinite(value) or value < 0 for value in values)):
            raise ValueError('Require ten finite nonnegative absolute block-MAE losses')
        means[mode] = float(np.mean(values))
    best = min(MODES, key=lambda mode: means[mode])
    sem = float(np.std(losses[best], ddof=1) / np.sqrt(10))
    threshold = means[best] + sem
    selected = next(mode for mode in MODES if means[mode] <= threshold)
    return {'best_mode': best, 'selected_mode': selected, 'best_mean_mae': means[best],
            'best_sem': sem, 'threshold': threshold, 'mean_mae_by_mode': means,
            'blocks': 10, 'rule': 'one_SE_best_absolute_block_losses_simplicity_order',
            'statistical_guarantee': False}
