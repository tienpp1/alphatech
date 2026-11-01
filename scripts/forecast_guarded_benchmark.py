"""Create-only offline deployment-policy study; never writes business records."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from numbers import Real
from pathlib import Path
import platform
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from apps.forecasting.guarded import fit_guarded, predict_artifact
from scripts.forecast_synthetic_data import make_series

SCENARIOS = ('noise_control', 'weekly_calendar', 'gradual_trend',
             'intermittent_spikes', 'level_shift')
SEEDS = (2026110121, 2026110122, 2026110123, 2026110124)
SOURCES = ('apps/forecasting/adaptive.py', 'apps/forecasting/guarded.py',
           'apps/forecasting/artifacts.py', 'scripts/forecast_synthetic_data.py',
           'scripts/forecast_guarded_benchmark.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def runtime():
    return {'python': platform.python_version(), **{name: version(name) for name in
            ('numpy', 'pandas', 'xgboost', 'scikit-learn')}}


def expected_cases():
    return [{'id': f'{scenario}__{seed}', 'scenario': scenario, 'seed': seed,
             'dataset_path': f'inputs/{scenario}__{seed}/dataset.csv'}
            for scenario in SCENARIOS for seed in SEEDS]


def protocol():
    return {'version': 'guarded_release_20261101', 'strategy': 'guarded_direct_v1',
            'rows': 730, 'cases': 20, 'seeds': list(SEEDS), 'scenarios': list(SCENARIOS),
            'horizon': 14, 'test_size': .2, 'minimum_relative_gain': .10,
            'paired_gain_se_multiplier': 3, 'minimum_block_win_fraction': .8,
            'minimum_initial_fit': 70, 'minimum_usable_blocks': 2,
            'gate': {'mean_ratio_ma7_lte': 1., 'worst_case_lte': 1.15,
                     'weekly_and_trend_mean_lt': 1.},
            'scope': 'known_synthetic_mechanisms_fresh_seeds_not_business_or_external_blind',
            'each_selection_before_own_holdout': True, 'holdout_used_for_selection': False,
            'serving_refit_not_used_for_holdout_score': True, 'business_writes': False}


def freeze(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / 'protocol.json', protocol())
    for case in expected_cases():
        path = root / case['dataset_path']
        path.parent.mkdir(parents=True)
        make_series(case['scenario'], case['seed']).to_csv(path, index_label='date', lineterminator='\n')
        write_json(path.with_name('metadata.json'), {**case, 'kind': 'synthetic_not_business',
                   'rows': 730, 'contains_PII': False, 'dataset_sha256': sha(path)})
    manifest = {'cases': expected_cases(), 'runtime': runtime(),
                'source_sha256': {name: sha(ROOT / name) for name in SOURCES},
                'files_sha256': {p.relative_to(root).as_posix(): sha(p)
                                 for p in sorted(root.rglob('*')) if p.is_file()}}
    write_json(root / 'input_manifest.json', manifest)
    return manifest


def verify(root):
    root = Path(root)
    manifest = json.loads((root / 'input_manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('cases') != expected_cases() or manifest.get('runtime') != runtime()
            or manifest.get('source_sha256') != {name: sha(ROOT / name) for name in SOURCES}
            or json.loads((root / 'protocol.json').read_text()) != protocol()):
        raise ValueError('Frozen protocol, source, runtime or expected cohort differs')
    expected = {'protocol.json'} | {c['dataset_path'] for c in expected_cases()} | {
        str(Path(c['dataset_path']).with_name('metadata.json')).replace('\\', '/') for c in expected_cases()}
    if set(manifest['files_sha256']) != expected:
        raise ValueError('Frozen input inventory differs')
    for name, digest in manifest['files_sha256'].items():
        if sha(root / name) != digest:
            raise ValueError('Frozen input differs')
    return manifest


def audit_rows(rows):
    chosen = []
    for row in rows:
        if type(row.get('observed')) is not bool:
            raise ValueError('Observed mask must be boolean')
        values = [row.get(k) for k in ('actual', 'prediction', 'ma7')]
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real)
               or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('Paired values must be finite nonnegative numbers')
        if row['observed']:
            chosen.append(row)
    if not chosen:
        raise ValueError('No observed truth')
    selected = statistics.fmean(abs(r['actual'] - r['prediction']) for r in chosen)
    baseline = statistics.fmean(abs(r['actual'] - r['ma7']) for r in chosen)
    if baseline == 0 and selected != 0:
        raise ValueError('Positive loss against perfect baseline has no finite ratio')
    return {'selected_mae': selected, 'ma7_mae': baseline,
            'ratio': selected / baseline if baseline else 1., 'observed_count': len(chosen)}


def audit_coverage(frame, rows, partitions, validation_blocks):
    """Independently require the complete, unique daily block grid."""
    n = len(frame)
    test_len = max(14, int(n * .2))
    validation_len = max(28, int((n - test_len) * .25))
    holdout_start = n - test_len
    initial_end = holdout_start - validation_len
    day = lambda i: frame.index[i].date().isoformat()
    expected_partitions = {'initial_fit': [day(0), day(initial_end - 1)],
                           'validation': [day(initial_end), day(holdout_start - 1)],
                           'holdout': [day(holdout_start), day(n - 1)]}
    expected = [(day(origin), day(origin + step), step)
                for origin in range(holdout_start - 1, n - 14, 14)
                for step in range(1, 15)]
    actual = [(r['origin'], r['date'], r['step']) for r in rows]
    if (partitions != expected_partitions or actual != expected
            or any(r['observed'] is not True for r in rows)):
        raise ValueError('Missing, duplicate, reordered or unobserved heldout grid')
    allowed_origins = [day(i) for i in range(initial_end - 1, holdout_start - 14, 14)]
    origins = [block['origin'] for block in validation_blocks]
    if origins != allowed_origins:
        raise ValueError('Missing, duplicate or boundary-crossing validation window')


def verify_seen(path):
    """Only the archived identity may receive the specific old2236 label."""
    metadata = json.loads(Path(path).with_name('metadata.json').read_text(encoding='utf-8'))
    expected = '75184768cdc9de5e5ec11d4860c2bb4a6867b5b0b9eda3f8035cbe50398b8d75'
    if (sha(path) != expected or metadata.get('dataset_sha256') != expected
            or metadata.get('scenario') != 'noise_control' or metadata.get('seed') != 2026102236
            or metadata.get('row_count') != 730 or metadata.get('cohort') != 'final'):
        raise ValueError('Diagnostic input is not the verified archived V4 noise2236 case')


def gates(records, expected):
    keys = ('id', 'scenario', 'seed', 'dataset_path')
    complete = (len(records) == len(expected)
                and len({c.get('id') for c in records}) == len(expected)
                and {tuple(c.get(k) for k in keys) for c in records}
                == {tuple(c[k] for k in keys) for c in expected}
                and all(c.get('status') == 'OK' for c in records))
    ratios = [c.get('ratio') for c in records]
    finite = bool(ratios) and all(not isinstance(v, (bool, np.bool_)) and isinstance(v, Real)
                                 and math.isfinite(v) and v >= 0 for v in ratios)
    mean = statistics.fmean(ratios) if finite else None
    families = {s: statistics.fmean(c['ratio'] for c in records if c['scenario'] == s)
                for s in SCENARIOS if finite and any(c['scenario'] == s for c in records)}
    checks = {'complete': complete, 'finite': finite,
              'overall': bool(finite and mean <= 1.),
              'worst_case': bool(finite and max(ratios) <= 1.15),
              'structured': all(families.get(s, math.inf) < 1 for s in ('weekly_calendar', 'gradual_trend'))}
    return {'passed': all(checks.values()), 'checks': checks,
            'mean_ratio_to_ma7': mean, 'family_mean_ratio': families}


def evaluate_case(directory, frame):
    directory.mkdir(parents=True, exist_ok=False)
    result = fit_guarded(frame, horizon=14, test_size=.2)
    rows = result['holdout_rows']
    arithmetic = audit_rows(rows)
    if not math.isclose(arithmetic['selected_mae'], result['model_metrics']['mae'], rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError('Independent paired arithmetic differs from engine metrics')
    partitions = result['evaluation']['partitions']
    audit_coverage(frame, rows, partitions, result['selection']['validation_blocks'])
    if not partitions['initial_fit'][1] < partitions['validation'][0] <= partitions['validation'][1] < partitions['holdout'][0]:
        raise ValueError('Partition chronology differs')
    for block in result['selection']['validation_blocks']:
        if not block['origin'] < partitions['holdout'][0]:
            raise ValueError('Selection crossed the holdout boundary')
    baseline_cache = {}
    for row in rows:
        if not row['origin'] < row['date'] or row['date'] < partitions['holdout'][0]:
            raise ValueError('Invalid heldout origin or target')
        if row['actual'] != float(frame.loc[pd.Timestamp(row['date']), 'target']):
            raise ValueError('Scored target differs from frozen input')
        origin = row['origin']
        if origin not in baseline_cache:
            history = list(map(float, frame.loc[:pd.Timestamp(origin), 'target']))
            predictions = []
            for _ in range(14):
                value = statistics.fmean(history[-7:]); history.append(value); predictions.append(value)
            baseline_cache[origin] = predictions
        if not math.isclose(row['ma7'], baseline_cache[origin][row['step'] - 1], rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError('Baseline uses different history or recursion')
    with (directory / 'holdout.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write_json(directory / 'serving_artifact.json', result['artifact'])
    loaded = json.loads((directory / 'serving_artifact.json').read_text())
    future = predict_artifact(loaded, frame, horizon=14)
    repeated = predict_artifact(result['artifact'], frame, horizon=14)
    if not np.isfinite(future).all() or (future < 0).any() or not np.array_equal(future, repeated):
        raise ValueError('Serving JSON roundtrip differs')
    write_json(directory / 'future_predictions.json', list(map(float, future)))
    payload = {key: result[key] for key in ('selection', 'model_metrics', 'baseline_metrics', 'evaluation')}
    payload.update(arithmetic=arithmetic, serving_artifact_sha256=sha(directory / 'serving_artifact.json'),
                   future_roundtrip_equal=True, scope='synthetic_offline_not_production')
    write_json(directory / 'result.json', payload)
    return payload


def run(root, seen_csv=None):
    if seen_csv is not None:
        verify_seen(seen_csv)
    root = Path(root); freeze(root); verify(root)
    records = []
    for case in expected_cases():
        try:
            frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
            payload = evaluate_case(root / 'cases' / case['id'], frame)
            record = {**case, 'status': 'OK', **payload['arithmetic'],
                      'selected_model': payload['selection']['effective_model']}
        except Exception as error:
            record = {**case, 'status': 'FAILED', 'error_class': type(error).__name__}
        records.append(record)
        print(f"Case {len(records)}/20 {case['id']}: {record['status']}", flush=True)
    verify(root)
    quality = gates(records, expected_cases())
    result = {'identity': sha(root / 'input_manifest.json'), 'cases': records, 'gate': quality,
              'outcomes': {'wins': sum(c.get('ratio', math.inf) < 1 for c in records),
                           'ties': sum(c.get('ratio') == 1 for c in records),
                           'losses': sum(c.get('ratio', -1) > 1 for c in records)},
              'business_writes': False, 'old_V4_changed': False}
    write_json(root / 'results.json', result)
    if seen_csv is not None:
        seen = pd.read_csv(seen_csv, index_col='date', parse_dates=True)
        diagnostic = evaluate_case(root / 'SEEN_v4_noise2236', seen)
        write_json(root / 'seen_diagnostic.json', {'input_sha256': sha(seen_csv),
                   'fresh_holdout': False, 'previously_evaluated_v4_final_case': True,
                   'policy_changed_after_this_run': False, 'result': diagnostic})
    write_json(root / 'result_manifest.json', {'files_sha256': {p.relative_to(root).as_posix(): sha(p)
               for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'result_manifest.json'}})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seen-case-csv', type=Path)
    args = parser.parse_args()
    result = run(args.output, args.seen_case_csv)
    print(json.dumps({'gate': result['gate'], 'outcomes': result['outcomes']}, indent=2))
    raise SystemExit(0 if result['gate']['passed'] else 3)
