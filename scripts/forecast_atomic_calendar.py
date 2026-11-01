"""Full-or-none calendar ablation; offline model selection, not runtime promotion."""
from numbers import Real

import numpy as np

from scripts.forecast_calendar_selection import fit_mode, load_mode

MODES = ('none', 'full')


def fit_atomic(history, mode, params=None):
    if mode not in MODES:
        raise ValueError('Atomic calendar must be full or none')
    return fit_mode(history, mode, params)


def load_atomic(path):
    model = load_mode(path)
    if model.mode not in MODES:
        raise ValueError('Partial calendar schemas are not atomic models')
    return model


def choose_atomic(losses):
    """One-SE simplicity heuristic on two atomic modes; no confidence guarantee."""
    if not isinstance(losses, dict) or set(losses) != set(MODES):
        raise ValueError('Require complete full/none evidence')
    means = {}
    with np.errstate(over='ignore', invalid='ignore'):
        for mode in MODES:
            values = losses[mode]
            if (not isinstance(values, (list, tuple)) or len(values) != 10 or
                    any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real)
                        or not np.isfinite(v) or v < 0 for v in values)):
                raise ValueError('Require ten finite nonnegative numeric block losses')
            means[mode] = float(np.mean(values))
        if not all(np.isfinite(value) for value in means.values()):
            raise ValueError('Validation aggregates overflowed')
        best = min(MODES, key=lambda mode: means[mode])
        sem = float(np.std(losses[best], ddof=1) / np.sqrt(10))
        threshold = means[best] + sem
    if not np.isfinite(sem) or not np.isfinite(threshold):
        raise ValueError('Validation uncertainty overflowed')
    selected = next(mode for mode in MODES if means[mode] <= threshold)
    return {'best_mode': best, 'selected_mode': selected, 'best_mean_mae': means[best],
            'best_sem': sem, 'threshold': threshold, 'mean_mae_by_mode': means,
            'blocks': 10, 'rule': 'atomic_calendar_one_SE_simplicity_order',
            'statistical_guarantee': False}
