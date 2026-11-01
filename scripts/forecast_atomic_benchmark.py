"""Frozen offline V4: atomic calendar ablation, no production/data promotion."""
import argparse
import json
from numbers import Real
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from scripts.forecast_atomic_calendar import MODES, choose_atomic, fit_atomic
from scripts.forecast_calendar_selection import columns_for
from scripts.forecast_calendar_benchmark import (gates as previous_gates,
                                                protocol as previous_protocol, sources as previous_sources)
from scripts.forecast_level_adaptive import model_params
from scripts.forecast_level_benchmark import evaluate, score_rows
from scripts.forecast_synthetic_data import digest, make_series, runtime_identity, write_json
from scripts.forecast_synthetic_benchmark import (checkpoint, exclusive_run, immutable_json,
                                                read_checkpoint, run_case, verify_files)

COHORTS = {'development': (2026102211, 2026102212, 2026102213),
           'final': tuple(range(2026102221, 2026102241))}


def protocol():
    old = previous_protocol()
    return {**old, 'version': 'atomic_calendar_v4_20261019',
            'cohorts': {name: list(seeds) for name, seeds in COHORTS.items()},
            'modes': list(MODES), 'columns': {mode: columns_for(mode) for mode in MODES},
            'selection': 'per_series_atomic_calendar_one_SE_best_absolute_block_MAE',
            'calendar_grouping': 'all_four_calendar_columns_present_together_or_absent',
            'series_count': 115, 'final_case_count': 100,
            'gates': {**old['gates'], 'overall_v2_lte': 1., 'finite_nonnegative_v2_ratios': True},
            'old_cohorts': 'SEEN_not_new_holdouts',
            'scope': 'pure_XGB_atomic_calendar_known_synthetic_fresh_seeds_not_external_blind'}


def sources():
    return {**previous_sources(), **{name: digest(ROOT / name) for name in (
        'scripts/forecast_atomic_calendar.py', 'scripts/forecast_atomic_benchmark.py')}}


def freeze(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    plan = protocol()
    write_json(root / 'protocol.json', plan)
    cases = []
    for cohort, seeds in COHORTS.items():
        for scenario in plan['scenarios']:
            for seed in seeds:
                case_id = f'{cohort}__{scenario}__{seed}'
                directory = root / 'inputs' / case_id
                directory.mkdir(parents=True)
                make_series(scenario, seed).to_csv(directory / 'dataset.csv', index_label='date', lineterminator='\n')
                write_json(directory / 'metadata.json', {'dataset_kind': 'synthetic_simulation_not_business_observations',
                    'cohort': cohort, 'scenario': scenario, 'seed': seed, 'row_count': 730,
                    'unit': 'VND', 'formula': plan['formulas'][scenario], 'business_writes': False,
                    'contains_PII': False, 'dataset_sha256': digest(directory / 'dataset.csv')})
                cases.append({'id': case_id, 'cohort': cohort, 'scenario': scenario, 'seed': seed,
                              'dataset_path': (directory / 'dataset.csv').relative_to(root).as_posix()})
    manifest = {'cases': cases, 'source_sha256': sources(), 'runtime': runtime_identity(),
                'files_sha256': {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}}
    write_json(root / 'input_manifest.json', manifest)
    return manifest


def verify(root):
    root = Path(root)
    try:
        manifest = json.loads((root / 'input_manifest.json').read_text(encoding='utf-8'))
        verify_files(root, manifest['files_sha256'])
        if (manifest['source_sha256'] != sources() or manifest['runtime'] != runtime_identity()
                or json.loads((root / 'protocol.json').read_text(encoding='utf-8')) != protocol()):
            raise ValueError('Frozen V4 source/runtime/protocol changed')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid V4 frozen evidence') from error
    return manifest, digest(root / 'input_manifest.json')


def calibrate(attempt, frame, params=None):
    history, validation = frame.iloc[:438], frame.iloc[438:584]
    pieces = []
    for mode in MODES:
        model = fit_atomic(history, mode, model_params() if params is None else params)
        model.save_model(attempt / f'{mode}_model.json')
        rows = evaluate(model, history, validation)
        if mode != MODES[0]:
            rows = rows.loc[rows.method == 'adaptive'].copy()
        rows.loc[rows.method == 'adaptive', 'method'] = mode
        pieces.append(rows)
    rows = pd.concat(pieces, ignore_index=True)
    metrics = score_rows(rows)
    losses = {mode: [float(np.mean(np.abs(group.prediction - group.actual))) for _, group in
                    rows.loc[rows.method == mode].groupby('origin', sort=True)] for mode in MODES}
    selection = choose_atomic(losses)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    return {'selection': selection, 'block_losses': losses, 'metrics': metrics,
            'fit_rows': len(history), 'fit_end': str(history.index[-1].date()),
            'selection_target_end': rows.date.max(), 'heldout_targets_used': False}


def outer(attempt, frame, selection):
    history, held = frame.iloc[:584], frame.iloc[584:]
    mode = selection['selected_mode']
    selected = fit_atomic(history, mode)
    reference = selected if mode == 'full' else fit_atomic(history, 'full')
    selected.save_model(attempt / 'selected_model.json')
    reference.save_model(attempt / 'v2_full_model.json')
    rows = evaluate(selected, history, held)
    rows.loc[rows.method == 'adaptive', 'method'] = 'atomic'
    ref = evaluate(reference, history, held)
    ref = ref.loc[ref.method == 'adaptive'].copy()
    ref['method'] = 'v2'
    rows = pd.concat([rows, ref], ignore_index=True)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    metrics = score_rows(rows)
    v2_mae = metrics['v2']['mae_unrounded']
    if v2_mae <= 0:
        raise ValueError('Undefined V2 comparison; do not invent gain')
    return {'metrics': metrics, 'ratio': metrics['atomic']['mae_ratio_to_ma7'],
            'ratio_vs_v2': metrics['atomic']['mae_unrounded'] / v2_mae,
            'selected_mode': mode, 'feature_columns': selected.columns,
            'fit_rows': len(history), 'fit_end': str(history.index[-1].date()),
            'refit_count': 1 if mode == 'full' else 2, 'full_model_reused': mode == 'full',
            'origins': rows.origin.nunique(), 'scored_days': rows.date.nunique(),
            'by_horizon': {str(step): score_rows(group) for step, group in rows.groupby('step')}}


def gates(cases, expected_cases):
    primary = [case.get('ratio') for case in cases if case['status'] == 'OK']
    if any(isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
           or not np.isfinite(value) or value < 0 for value in primary):
        raise ValueError('MA7 ratios must be finite nonnegative real numbers, not booleans')
    old = previous_gates(cases, expected_cases)
    ratios = [case['ratio_vs_v2'] for case in cases if case['status'] == 'OK']
    finite = bool(ratios) and all(not isinstance(value, (bool, np.bool_)) and isinstance(value, Real)
                                and np.isfinite(value) and value >= 0 for value in ratios)
    overall = float(np.mean(ratios)) if finite else None
    checks = {**old['checks'], 'v2_finite': bool(finite),
              'overall_v2': bool(finite and overall <= 1.)}
    return {**old, 'passed': bool(all(checks.values())), 'checks': checks, 'mean_ratio_vs_v2': overall}


def run(root, resume=False):
    root = Path(root)
    if not resume:
        freeze(root)
    manifest, identity = verify(root)
    with exclusive_run(root):
        if resume:
            state = read_checkpoint(root, identity)
            if state['phase'] == 'COMPLETED':
                if state.get('result_manifest_sha256') != digest(root / 'result_manifest.json'):
                    raise ValueError('Completed result manifest changed')
                verify_files(root, json.loads((root / 'result_manifest.json').read_text())['files_sha256'])
                return json.loads((root / 'results.json').read_text())
            if state['phase'] == 'FAILED':
                raise ValueError('Failed V4 retained; no automatic retry or tuning')
        else:
            state = {'identity': identity, 'phase': 'INPUTS_FROZEN'}
            checkpoint(root, state)

        def execute(directory, worker):
            key = directory.relative_to(root).as_posix()
            receipt = directory / 'result.json'
            anchors = state.setdefault('receipt_sha256', {})
            if key in anchors and (not receipt.is_file() or digest(receipt) != anchors[key]):
                raise ValueError('Checkpoint-bound receipt changed')
            result = run_case(directory, identity, worker, case_key=key)
            anchors[key] = digest(receipt)
            checkpoint(root, state)
            return result

        try:
            choices, summary = {}, []
            for case in manifest['cases']:
                frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                result = execute(root / 'calibration' / case['id'], lambda attempt: calibrate(attempt, frame))
                summary.append({'id': case['id'], 'status': result['status'], **(
                    {'selection': result['payload']['selection']} if result['status'] == 'OK'
                    else {'error_class': result['error_class']})})
                if result['status'] == 'OK':
                    choices[case['id']] = result['payload']['selection']
                state.update(phase='VALIDATING', calibrated_cases=len(summary), current_case=case['id'])
                checkpoint(root, state)
                print(f"Calibration {len(summary)}/{len(manifest['cases'])}: {case['id']} {result['status']}", flush=True)
            immutable_json(root / 'calibration_summary.json', summary)
            if len(choices) != len(manifest['cases']):
                raise ValueError('Incomplete calibration; all final evaluation forbidden')
            selections = {'identity': identity, 'by_case': choices, 'final_targets_used': False}
            immutable_json(root / 'selections.json', selections)
            state.update(phase='SELECTED', selections_sha256=digest(root / 'selections.json'))
            checkpoint(root, state)
            cases = []
            expected = [case for case in manifest['cases'] if case['cohort'] == 'final']
            for case in expected:
                frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                result = execute(root / 'final' / case['id'], lambda attempt: outer(attempt, frame, choices[case['id']]))
                record = {key: case[key] for key in ('id', 'scenario', 'seed')}
                record['status'] = result['status']
                record.update(result['payload'] if result['status'] == 'OK' else {'error_class': result['error_class']})
                cases.append(record)
                state.update(phase='EVALUATING', final_completed=len(cases), current_case=case['id'])
                checkpoint(root, state)
                print(f"Final {len(cases)}/{len(expected)}: {case['id']} {result['status']}", flush=True)
            result = {'identity': identity, 'cases': cases, 'gate': gates(cases, expected),
                      'wins_vs_ma7': sum(case.get('ratio', float('inf')) < 1 for case in cases),
                      'selection_sha256': digest(root / 'selections.json'),
                      'selected_mode_counts': {mode: sum(case.get('selected_mode') == mode for case in cases) for mode in MODES},
                      'production_changed': False, 'old_results_changed': False, 'scope': protocol()['scope']}
            verify(root)
            immutable_json(root / 'results.json', result)
            files = {path.relative_to(root).as_posix(): digest(path) for path in sorted(root.rglob('*'))
                     if path.is_file() and path.name not in ('.run.lock', 'checkpoint.json', 'result_manifest.json')
                     and not path.name.endswith('.tmp')}
            immutable_json(root / 'result_manifest.json', {'files_sha256': files, 'source_sha256': sources()})
            state.update(phase='COMPLETED', performance_passed=result['gate']['passed'],
                         result_manifest_sha256=digest(root / 'result_manifest.json'))
            checkpoint(root, state)
            return result
        except Exception as error:
            state.update(phase='FAILED', error_class=type(error).__name__)
            checkpoint(root, state)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    result = run(args.output, args.resume)
    print(json.dumps({key: result[key] for key in ('gate', 'wins_vs_ma7', 'selected_mode_counts')}, indent=2))
    raise SystemExit(0 if result['gate']['passed'] else 3)
