"""Leakage-conscious MA7 versus normalized direct-XGBoost selection."""

import math

import numpy as np
import pandas as pd

from . import adaptive


def _freq(granularity):
    if granularity == 'DAILY':
        return 'D'
    if granularity == 'WEEKLY':
        return '7D'
    raise ValueError('granularity must be DAILY or WEEKLY')


def _baseline(values, horizon, seasonal=False):
    history = list(map(float, values))
    out = []
    for step in range(horizon):
        value = history[-7] if seasonal else float(np.mean(history[-7:]))
        value = max(0., value)
        out.append(value)
        history.append(value)
    return np.asarray(out, dtype=float)


def _metrics(actual, predicted):
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    if actual.shape != predicted.shape or actual.ndim != 1:
        raise ValueError('Metrics require paired one-dimensional actual and prediction arrays')
    if not len(actual):
        return {'mae': None, 'rmse': None, 'mape': None, 'r2': None, 'bias': None, 'count': 0}
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError('Metrics require finite actual and prediction values')
    errors = predicted - actual
    nonzero = np.abs(actual) > 1e-3
    mape = (float(np.mean(np.abs(errors[nonzero] / actual[nonzero])) * 100.)
            if nonzero.any() else None)
    return {
        'mae': float(np.mean(np.abs(errors))),
        'rmse': float(np.sqrt(np.mean(np.square(errors)))),
        'mape': mape,
        'r2': float(1. - np.sum(np.square(errors)) / np.sum(np.square(actual - np.mean(actual))))
        if len(actual) >= 2 and np.var(actual) else None,
        'bias': float(np.mean(errors)),
        'count': int(len(actual)),
    }


def _paired_gates(model_losses, baseline_losses):
    """Apply fixed paired improvement, sample-SE and block-win gates."""
    if (not isinstance(model_losses, (list, tuple, np.ndarray)) or
            not isinstance(baseline_losses, (list, tuple, np.ndarray)) or
            len(model_losses) != len(baseline_losses) or len(model_losses) < 2):
        raise ValueError('At least two paired model and baseline block losses are required')
    model = np.asarray(model_losses, dtype=float)
    baseline = np.asarray(baseline_losses, dtype=float)
    if (not np.isfinite(model).all() or not np.isfinite(baseline).all() or
            (model < 0).any() or (baseline < 0).any()):
        raise ValueError('Paired losses must be finite and nonnegative')
    gains = baseline - model
    mean_gain = float(np.mean(gains))
    sample_se = float(np.std(gains, ddof=1) / math.sqrt(len(gains)))
    baseline_mean = float(np.mean(baseline))
    improvement = mean_gain / baseline_mean if baseline_mean else 0.
    wins = int(np.count_nonzero(model < baseline))
    strict_three_se = mean_gain > 3 * sample_se and not math.isclose(
        mean_gain, 3 * sample_se, rel_tol=1e-12, abs_tol=1e-12)
    return {
        'xgb_mean_mae': float(np.mean(model)), 'ma7_mean_mae': baseline_mean,
        'mean_paired_gain': mean_gain, 'paired_gain_sample_se': sample_se,
        'relative_improvement': improvement, 'win_fraction': wins / len(model),
        'usable_blocks': int(len(model)), 'minimum_blocks': 2,
        'improvement_at_least_10_percent': improvement >= .10,
        'paired_gain_exceeds_3_sample_se': strict_three_se,
        'wins_at_least_80_percent': wins / len(model) >= .80,
    }


def _rows(values, index, origin_pos, horizon, observed, model_predictions=None):
    dates = index[origin_pos + 1:origin_pos + 1 + horizon]
    actual_values = values[origin_pos + 1:origin_pos + 1 + horizon]
    known = values[:origin_pos + 1]
    ma7 = _baseline(known, horizon)
    naive = _baseline(known, horizon, seasonal=True)
    if model_predictions is None:
        model_predictions = ma7
    return [{
        'date': date.date().isoformat(), 'origin': index[origin_pos].date().isoformat(),
        'step': step, 'actual': float(actual), 'prediction': float(prediction),
        'ma7': float(baseline), 'naive': float(seasonal),
        'observed': date.date() in observed,
    } for step, (date, actual, prediction, baseline, seasonal) in enumerate(
        zip(dates, actual_values, model_predictions, ma7, naive), 1)]


def _loss(rows, field):
    chosen = [row for row in rows if row['observed']]
    if not chosen:
        return None
    return float(np.mean([abs(row['actual'] - row[field]) for row in chosen]))


def _choose_mode(losses):
    means = {mode: float(np.mean(losses[mode])) for mode in ('none', 'full')}
    best = min(('none', 'full'), key=lambda mode: means[mode])
    vals = losses[best]
    sem = float(np.std(vals, ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else 0.
    limit = means[best] + sem
    selected = next(mode for mode in ('none', 'full') if means[mode] <= limit)
    return selected, {'best_mode': best, 'selected_mode': selected,
                      'mean_mae_by_mode': means, 'best_sem': sem, 'simplicity_limit': limit,
                      'rule': 'one_SE_simplicity_order_none_then_full'}


def _new_artifact(effective, params=None, mode=None, model=None):
    return {
        'format': adaptive.FORMAT, 'effective_model': effective,
        'calendar_mode': mode if effective == 'XGBOOST_DIRECT' else None,
        'columns': adaptive.columns_for(mode) if effective == 'XGBOOST_DIRECT' else [],
        'params': dict(params or {}),
        'booster': adaptive.booster_to_json_dict(model) if model is not None else None,
    }


def fit_guarded(series, *, horizon=14, granularity='DAILY', params=None, test_size=.20,
                observed_dates=None):
    """Select XGBoost only from validation evidence and separately score holdout."""
    values = adaptive.validate_history(series, granularity, minimum=49)
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError('horizon must be a positive integer')
    if isinstance(test_size, bool) or not isinstance(test_size, (int, float)) or not .05 <= test_size <= .5:
        raise ValueError('test_size must be in the supported range [0.05, 0.5]')
    params = adaptive.model_params(params)
    dates = set(series.attrs.get('observed_period_dates', series.index)) if observed_dates is None else set(observed_dates)
    observed = {pd.Timestamp(date).date() for date in dates}
    freq = _freq(granularity)
    n = len(series)
    test_len = max(14, int(n * test_size))
    if test_len >= n:
        raise ValueError('test partition leaves no training history')
    validation_len = max(28, int((n - test_len) * .25))
    initial_end = n - test_len - validation_len
    holdout_start = n - test_len
    if initial_end < 7:
        raise ValueError('At least seven initial fit periods are required')

    eligible = granularity == 'DAILY' and horizon <= 14 and initial_end >= 70
    validation_blocks = []
    candidate_models = {}
    mode_losses = {'none': [], 'full': []}
    if eligible:
        initial = series.iloc[:initial_end]
        for mode in ('none', 'full'):
            candidate_models[mode] = adaptive.fit_direct(initial, mode, params, granularity)
        for origin in range(initial_end - 1, holdout_start - 14, 14):
            if origin + 14 >= holdout_start:
                continue
            target_dates = series.index[origin + 1:origin + 15]
            block_by_mode = {}
            for mode in ('none', 'full'):
                pred = adaptive.predict_direct(candidate_models[mode], values[:origin + 1],
                                               series.index[origin], target_dates, granularity, mode)
                rows = _rows(values, series.index, origin, 14, observed, pred)
                block_by_mode[mode] = rows
                loss = _loss(rows, 'prediction')
                if loss is not None:
                    mode_losses[mode].append(loss)
            validation_blocks.append(block_by_mode)

    valid_count = min(len(mode_losses['none']), len(mode_losses['full']))
    mode_details = None
    selection = {
        'effective_model': 'MA7', 'reason': 'xgboost_ineligible',
        'eligible': bool(eligible), 'eligibility': {
            'granularity_daily': granularity == 'DAILY', 'horizon_at_most_14': horizon <= 14,
            'initial_fit_periods': initial_end, 'minimum_initial_fit_periods': 70,
        }, 'validation_blocks': [], 'criteria': {}, 'params': params,
    }
    selected_mode = None
    if eligible and valid_count >= 2:
        usable = [block for block in validation_blocks if all(_loss(block[m], 'prediction') is not None for m in ('none', 'full'))]
        losses = {mode: [_loss(block[mode], 'prediction') for block in usable] for mode in ('none', 'full')}
        selected_mode, mode_details = _choose_mode(losses)
        selected_model = candidate_models[selected_mode]
        model_losses, baseline_losses = [], []
        for block in usable:
            model_losses.append(_loss(block[selected_mode], 'prediction'))
            baseline_losses.append(_loss(block[selected_mode], 'ma7'))
        criteria = _paired_gates(model_losses, baseline_losses)
        passed = (criteria['improvement_at_least_10_percent'] and
                  criteria['paired_gain_exceeds_3_sample_se'] and criteria['wins_at_least_80_percent'])
        selection.update({
            'effective_model': 'XGBOOST_DIRECT' if passed else 'MA7',
            'reason': 'validation_gates_passed' if passed else 'validation_gates_not_met',
            'calendar_mode': selected_mode, 'calendar_selection': mode_details,
            'validation_losses': losses, 'criteria': criteria,
            'validation_blocks': [{'origin': block[selected_mode][0]['origin'],
                                   'ma7_mae': _loss(block[selected_mode], 'ma7'),
                                   'xgb_mae': _loss(block[selected_mode], 'prediction')}
                                  for block in usable],
        })
    elif eligible:
        selection.update({'reason': 'insufficient_observed_validation_blocks', 'validation_blocks': []})

    use_xgb = selection['effective_model'] == 'XGBOOST_DIRECT'
    holdout_rows = []
    holdout_model = None
    if use_xgb:
        holdout_model = adaptive.fit_direct(series.iloc[:holdout_start], selected_mode, params, granularity)
    for origin in range(holdout_start - 1, n - 14, 14):
        if origin + 14 >= n:
            continue
        target_dates = series.index[origin + 1:origin + 15]
        pred = (adaptive.predict_direct(holdout_model, values[:origin + 1], series.index[origin],
                                        target_dates, granularity, selected_mode)
                if use_xgb else _baseline(values[:origin + 1], 14))
        holdout_rows.extend(_rows(values, series.index, origin, 14, observed, pred))
    if not any(row['observed'] for row in holdout_rows):
        raise ValueError('Holdout contains no observed truth; metrics cannot be fabricated')

    scored = [row for row in holdout_rows if row['observed']]
    model_metrics = _metrics([r['actual'] for r in scored], [r['prediction'] for r in scored])
    baseline_metrics = {
        'ma7': _metrics([r['actual'] for r in scored], [r['ma7'] for r in scored]),
        'seasonal_naive_7': _metrics([r['actual'] for r in scored], [r['naive'] for r in scored]),
    }
    final_model = adaptive.fit_direct(series, selected_mode, params, granularity) if use_xgb else None
    artifact = _new_artifact(selection['effective_model'], params, selected_mode, final_model)
    evaluation = {
        'method': 'chronological_validation_selection_then_separate_rolling_holdout',
        'granularity': granularity, 'horizon': horizon,
        'partitions': {'initial_fit': [series.index[0].date().isoformat(), series.index[initial_end - 1].date().isoformat()],
                       'validation': [series.index[initial_end].date().isoformat(), series.index[holdout_start - 1].date().isoformat()],
                       'holdout': [series.index[holdout_start].date().isoformat(), series.index[-1].date().isoformat()]},
        'counts': {'history': n, 'initial_fit': initial_end, 'validation': validation_len,
                   'holdout': test_len, 'observed_holdout': len(scored)},
        'observed_dates_count': len(observed.intersection({d.date() for d in series.index})),
        'holdout_scored_blocks': len(holdout_rows) // 14,
        'intervals_calibrated': False,
    }
    feature_importances = (dict(zip(artifact['columns'], map(float, final_model.feature_importances_)))
                           if final_model is not None else {})
    return {'artifact': artifact, 'selection': selection, 'model_metrics': model_metrics,
            'baseline_metrics': baseline_metrics, 'feature_importances': feature_importances,
            'evaluation': evaluation, 'holdout_rows': holdout_rows}


def predict_artifact(artifact, history, horizon=14, granularity='DAILY'):
    values = adaptive.validate_history(history, granularity, minimum=7)
    if not isinstance(artifact, dict) or artifact.get('format') != adaptive.FORMAT:
        raise ValueError('Unsupported guarded forecast artifact')
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError('horizon must be a positive integer')
    if artifact.get('effective_model') == 'MA7':
        return _baseline(values, horizon)
    if artifact.get('effective_model') != 'XGBOOST_DIRECT' or horizon > 14 or granularity != 'DAILY':
        raise ValueError('XGBoost artifact is only valid for DAILY horizons up to 14')
    mode = artifact.get('calendar_mode')
    if mode not in ('none', 'full') or artifact.get('columns') != adaptive.columns_for(mode):
        raise ValueError('Artifact feature schema does not match its calendar mode')
    model = adaptive.booster_from_json_dict(artifact.get('booster'), artifact.get('params'))
    freq = _freq(granularity)
    delta = pd.Timedelta(days=1) if granularity == 'DAILY' else pd.Timedelta(days=7)
    dates = pd.date_range(history.index[-1] + delta, periods=horizon, freq=freq)
    return adaptive.predict_direct(model, values, history.index[-1], dates, granularity, mode)
