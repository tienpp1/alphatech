"""Frozen synthetic revenue inputs; never business observations or DB records."""
import hashlib
import json
from importlib.metadata import version
import os
from pathlib import Path
import platform

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('noise_control', 'weekly_calendar', 'gradual_trend',
             'intermittent_spikes', 'level_shift')
COHORTS = {'development': (2026101601, 2026101602, 2026101603),
           'final': (2026101611, 2026101612, 2026101613)}
FORMULAS = {
    'noise_control': '20m + Normal(0,2m)',
    'weekly_calendar': '20m + 12m*weekend + 4m*(day<=5) + Normal(0,1m)',
    'gradual_trend': '20m + 20000*t + 8m*weekend + Normal(0,1m)',
    'intermittent_spikes': 'Bernoulli(.35)*(12m+2m*LogNormal(1.2,.8)) + Bernoulli(.025)*80m',
    'level_shift': '28m*(1 if t<365 else 1.2 if t<620 else .55) + 5m*weekend + Normal(0,1.5m)',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    """Create-only evidence. Existing artifacts, including failures, survive."""
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def build_protocol():
    return {
        'version': 'synthetic_revenue_v1_20261016', 'rows': 730,
        'start': '2024-01-01', 'unit': 'VND', 'partition_rows': [438, 146, 146],
        'scenarios': list(SCENARIOS), 'cohorts': {key: list(value) for key, value in COHORTS.items()},
        'generator_formulas': FORMULAS.copy(), 'rounding': 'nearest_integer_then_clamp_nonnegative',
        'horizon': 14, 'origin_stride': 14, 'complete_blocks': 10, 'omitted_tail_days': 6,
        'selection': 'equal_case_mean_recursive_validation_MAE_ratio_to_MA7_development_only',
        'tie_break': 'fixed_candidate_order', 'undefined_ratio': 'candidate_ineligible_no_gain_invented',
        'candidate_grid': {'objective': ['reg:squarederror', 'reg:absoluteerror'],
                           'depth': [2, 4], 'trees': [100, 250, 400]},
        'fixed_params': {'learning_rate': .05, 'subsample': .8, 'colsample_bytree': .8,
                         'random_state': 42, 'n_jobs': 1, 'eval_metric': 'mae', 'reg_lambda': 1},
        'fit': 'validation_selection_then_refit_final_case_train_plus_validation_no_eval_set',
        'final_targets_used_in_selection': False, 'promotion': False, 'business_writes': False,
        'scope': 'synthetic_mechanism_benchmark_not_commercial_or_blinded_independent_validation',
    }


def make_series(scenario, seed):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown synthetic scenario')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('Seed must be a nonnegative integer')
    rng = np.random.default_rng(seed)
    dates = pd.date_range('2024-01-01', periods=730, freq='D')
    t = np.arange(730)
    weekend = (dates.dayofweek >= 5).astype(float)
    if scenario == 'noise_control':
        values = 20_000_000 + rng.normal(0, 2_000_000, 730)
    elif scenario == 'weekly_calendar':
        values = 20_000_000 + 12_000_000 * weekend + 4_000_000 * (dates.day <= 5) + rng.normal(0, 1_000_000, 730)
    elif scenario == 'gradual_trend':
        values = 20_000_000 + 20_000 * t + 8_000_000 * weekend + rng.normal(0, 1_000_000, 730)
    elif scenario == 'intermittent_spikes':
        values = ((rng.random(730) < .35) * (12_000_000 + 2_000_000 * rng.lognormal(1.2, .8, 730))
                  + (rng.random(730) < .025) * 80_000_000)
    else:
        level = np.where(t < 365, 1., np.where(t < 620, 1.2, .55))
        values = 28_000_000 * level + 5_000_000 * weekend + rng.normal(0, 1_500_000, 730)
    return pd.DataFrame({'target': np.maximum(np.round(values), 0)}, index=dates)


def source_hashes():
    names = ('scripts/forecast_synthetic_data.py', 'scripts/forecast_synthetic_benchmark.py',
             'apps/forecasting/features.py', 'apps/forecasting/evaluation.py')
    return {name: digest(ROOT / name) for name in names if (ROOT / name).is_file()}


def runtime_identity():
    return {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
            'xgboost': version('xgboost'), 'threads': {name: os.getenv(name) for name in
            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}}


def freeze_inputs(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'protocol.json', build_protocol())
    cases = []
    for cohort, seeds in COHORTS.items():
        for scenario in SCENARIOS:
            for seed in seeds:
                case_id = f'{cohort}__{scenario}__{seed}'
                directory = output / 'inputs' / case_id
                directory.mkdir(parents=True)
                frame = make_series(scenario, seed)
                frame.to_csv(directory / 'dataset.csv', index_label='date', lineterminator='\n')
                metadata = {'dataset_kind': 'synthetic_simulation_not_business_observations',
                            'cohort': cohort, 'scenario': scenario, 'seed': seed, 'row_count': 730,
                            'period_start': str(frame.index[0].date()), 'period_end': str(frame.index[-1].date()),
                            'unit': 'VND', 'business_writes': False, 'contains_PII': False,
                            'missing_period_count': 0, 'formula': FORMULAS[scenario],
                            'dataset_sha256': digest(directory / 'dataset.csv')}
                write_json(directory / 'metadata.json', metadata)
                cases.append({'id': case_id, 'cohort': cohort, 'scenario': scenario, 'seed': seed,
                              'dataset_path': (directory / 'dataset.csv').relative_to(output).as_posix(),
                              'metadata_path': (directory / 'metadata.json').relative_to(output).as_posix()})
    manifest = {'cases': cases, 'source_sha256': source_hashes(), 'runtime': runtime_identity(),
                'files_sha256': {path.relative_to(output).as_posix(): digest(path)
                                 for path in sorted(output.rglob('*')) if path.is_file()}}
    write_json(output / 'input_manifest.json', manifest)
    return manifest
