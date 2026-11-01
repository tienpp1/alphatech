"""Frozen offline V3 feature-selection study; preserves all prior experiment sources."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from scripts.forecast_calendar_selection import MODES, choose_mode, columns_for, fit_mode
from scripts.forecast_level_adaptive import model_params
from scripts.forecast_level_benchmark import evaluate, performance_gate, score_rows, sources as v2_sources
from scripts.forecast_synthetic_data import (FORMULAS, SCENARIOS, digest, make_series,
                                            runtime_identity, write_json)
from scripts.forecast_synthetic_benchmark import (checkpoint, exclusive_run, immutable_json,
                                                read_checkpoint, run_case, verify_files)

COHORTS = {'development': (2026101931, 2026101932, 2026101933),
           'final': tuple(range(2026101941, 2026101951))}


def protocol():
    return {'version': 'calendar_selection_v3_20261019', 'rows': 730,
            'cohorts': {name: list(seeds) for name, seeds in COHORTS.items()},
            'scenarios': list(SCENARIOS), 'formulas': FORMULAS,
            'partition_rows': [438, 146, 146], 'horizon': 14, 'scored_days': 140,
            'complete_blocks': 10, 'omitted_tail_days': 6, 'modes': list(MODES),
            'columns': {mode: columns_for(mode) for mode in MODES}, 'params': model_params(), 'alpha': 1.,
            'selection': 'per_series_one_SE_of_best_absolute_block_MAE_simplicity_order',
            'sem': 'sample_SD_best_10_block_losses/sqrt(10)', 'statistical_guarantee': False,
            'fit': 'shadow438_then_validate438:584;freeze_all_selections;refit584_then_final584:730',
            'final_targets_used_in_selection': False, 'online_mode_switching': False,
            'gates': {'overall_ma7_lt': 1., 'noise_ma7_lt': 1., 'noise_v2_lte': 1.,
                      'family_ma7_lte': 1.10, 'case_ma7_lte': 1.50,
                      'structured_families': ['weekly_calendar', 'gradual_trend', 'level_shift'],
                      'structured_ma7_lt': 1., 'structured_v2_lte': 1.05},
            'scope': 'pure_XGB_known_synthetic_mechanisms_fresh_seeds_not_blind_external_validation',
            'business_writes': False, 'production_changed': False, 'promotion': False}


def sources():
    return {**v2_sources(), **{name: digest(ROOT / name) for name in (
        'scripts/forecast_calendar_selection.py', 'scripts/forecast_calendar_benchmark.py')}}


def freeze(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / 'protocol.json', protocol())
    cases = []
    for cohort, seeds in COHORTS.items():
        for scenario in SCENARIOS:
            for seed in seeds:
                case_id = f'{cohort}__{scenario}__{seed}'
                directory = root / 'inputs' / case_id
                directory.mkdir(parents=True)
                make_series(scenario, seed).to_csv(directory / 'dataset.csv', index_label='date', lineterminator='\n')
                write_json(directory / 'metadata.json', {'dataset_kind': 'synthetic_simulation_not_business_observations',
                    'cohort': cohort, 'scenario': scenario, 'seed': seed, 'row_count': 730,
                    'unit': 'VND', 'formula': FORMULAS[scenario], 'business_writes': False, 'contains_PII': False,
                    'dataset_sha256': digest(directory / 'dataset.csv')})
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
            raise ValueError('Frozen source/runtime/protocol changed')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid V3 frozen evidence') from error
    return manifest, digest(root / 'input_manifest.json')


def calibrate(attempt, frame, params=None):
    params = model_params() if params is None else params
    history, validation = frame.iloc[:438], frame.iloc[438:584]
    pieces = []
    for mode in MODES:
        model = fit_mode(history, mode, params)
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
    selection = choose_mode(losses)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    return {'selection': selection, 'block_losses': losses, 'metrics': metrics,
            'fit_rows': len(history), 'fit_end': str(history.index[-1].date()),
            'selection_target_end': rows.date.max(), 'heldout_targets_used': False}


def outer(attempt, frame, selection):
    history, held = frame.iloc[:584], frame.iloc[584:]
    mode = selection['selected_mode']
    selected = fit_mode(history, mode)
    reference = selected if mode == 'full' else fit_mode(history, 'full')
    selected.save_model(attempt / 'selected_model.json')
    reference.save_model(attempt / 'v2_full_model.json')
    rows = evaluate(selected, history, held)
    rows.loc[rows.method == 'adaptive', 'method'] = 'v3'
    ref = evaluate(reference, history, held)
    ref = ref.loc[ref.method == 'adaptive'].copy()
    ref['method'] = 'v2'
    rows = pd.concat([rows, ref], ignore_index=True)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    metrics = score_rows(rows)
    v2_mae = metrics['v2']['mae_unrounded']
    if v2_mae <= 0:
        raise ValueError('Undefined V2 ratio; do not invent gain')
    return {'metrics': metrics, 'ratio': metrics['v3']['mae_ratio_to_ma7'],
            'ratio_vs_v2': metrics['v3']['mae_unrounded'] / v2_mae,
            'selected_mode': mode, 'feature_columns': selected.columns,
            'fit_rows': len(history), 'fit_end': str(history.index[-1].date()),
            'refit_count': 1 if mode == 'full' else 2, 'full_model_reused': mode == 'full',
            'origins': rows.origin.nunique(), 'scored_days': rows.date.nunique(),
            'by_horizon': {str(step): score_rows(group) for step, group in rows.groupby('step')}}


def gates(cases, expected_cases):
    base = performance_gate(cases, expected_cases)
    valid = [c for c in cases if c['status'] == 'OK']
    family_v2 = {name: float(np.mean([c['ratio_vs_v2'] for c in valid if c['scenario'] == name]))
                 for name in sorted({c['scenario'] for c in valid})}
    noise = base['family_mean_mae_ratio'].get('noise_control', float('inf'))
    checks = {**base['checks'], 'noise': noise < 1. and family_v2.get('noise_control', float('inf')) <= 1.,
              'preservation': all(base['family_mean_mae_ratio'].get(name, float('inf')) < 1.
                                  and family_v2.get(name, float('inf')) <= 1.05 for name in
                                  ('weekly_calendar', 'gradual_trend', 'level_shift'))}
    return {**base, 'passed': bool(all(checks.values())), 'checks': checks,
            'family_mean_ratio_vs_v2': family_v2}


def run(root, resume=False):
    root = Path(root)
    if not resume:
        freeze(root)
    manifest, identity = verify(root)
    with exclusive_run(root):
        if resume:
            state = read_checkpoint(root, identity)
            if state['phase'] == 'COMPLETED':
                verify_files(root, json.loads((root / 'result_manifest.json').read_text())['files_sha256'])
                return json.loads((root / 'results.json').read_text())
            if state['phase'] == 'FAILED':
                raise ValueError('Failed run retained, no automatic retry/tuning')
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
            calibrated, summary = {}, []
            for case in manifest['cases']:
                frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                result = execute(root / 'calibration' / case['id'], lambda attempt: calibrate(attempt, frame))
                summary.append({'id': case['id'], 'status': result['status'], **(
                    {'selection': result['payload']['selection']} if result['status'] == 'OK'
                    else {'error_class': result['error_class']})})
                if result['status'] == 'OK':
                    calibrated[case['id']] = result['payload']['selection']
                state.update(phase='VALIDATING', calibrated_cases=len(summary), current_case=case['id'])
                checkpoint(root, state)
                print(f"Calibration {len(summary)}/{len(manifest['cases'])}: {case['id']} {result['status']}", flush=True)
            immutable_json(root / 'calibration_summary.json', summary)
            if len(calibrated) != len(manifest['cases']):
                raise ValueError('Incomplete calibration; final evaluation forbidden')
            selections = {'identity': identity, 'by_case': calibrated, 'final_targets_used': False}
            immutable_json(root / 'selections.json', selections)
            state.update(phase='SELECTED', selections_sha256=digest(root / 'selections.json'))
            checkpoint(root, state)
            cases = []
            final_inputs = [c for c in manifest['cases'] if c['cohort'] == 'final']
            for case in final_inputs:
                frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                result = execute(root / 'final' / case['id'],
                                 lambda attempt: outer(attempt, frame, calibrated[case['id']]))
                record = {key: case[key] for key in ('id', 'scenario', 'seed')}
                record['status'] = result['status']
                if result['status'] == 'OK':
                    record.update(result['payload'])
                else:
                    record['error_class'] = result['error_class']
                cases.append(record)
                state.update(phase='EVALUATING', final_completed=len(cases), current_case=case['id'])
                checkpoint(root, state)
                print(f"Final {len(cases)}/{len(final_inputs)}: {case['scenario']} {result['status']}", flush=True)
            result = {'identity': identity, 'cases': cases, 'gate': gates(cases, final_inputs),
                      'wins_vs_ma7': sum(c.get('ratio', float('inf')) < 1 for c in cases),
                      'selection_sha256': digest(root / 'selections.json'),
                      'selected_mode_counts': {mode: sum(c.get('selected_mode') == mode for c in cases) for mode in MODES},
                      'production_changed': False, 'old_results_changed': False, 'scope': protocol()['scope']}
            verify(root)
            immutable_json(root / 'results.json', result)
            files = {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*'))
                     if p.is_file() and p.name not in ('.run.lock', 'checkpoint.json', 'result_manifest.json')
                     and not p.name.endswith('.tmp')}
            immutable_json(root / 'result_manifest.json', {'files_sha256': files, 'source_sha256': sources()})
            state.update(phase='COMPLETED', performance_passed=result['gate']['passed'])
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
