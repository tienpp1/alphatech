"""Frozen V2 synthetic study: anchored direct-residual XGB, not production ML."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from apps.forecasting.features import DEFAULT_FEATURE_CONFIG, recursive_feature_predictions
from scripts.forecast_level_adaptive import (fit_direct, model_params, origin_features,
                                             predict_direct, supervised_pairs)
from scripts.forecast_synthetic_data import (SCENARIOS, FORMULAS, digest, make_series,
                                            runtime_identity, write_json)
from scripts.forecast_synthetic_benchmark import (checkpoint, exclusive_run, fit_xgb,
    immutable_json, origin_blocks, read_checkpoint, recursive_baselines, reference_params,
    run_case, safe_metrics, select_from_scores, verify_files)

COHORTS = {'development': (2026101901, 2026101902, 2026101903),
           'final': (2026101911, 2026101912, 2026101913, 2026101914, 2026101915)}
ALPHAS = (.5, 1.)


def candidates():
    return [{'id': f'direct_{index:02d}', 'params': {**model_params(), 'objective': objective,
            'max_depth': depth}} for index, (objective, depth) in enumerate(
                (('reg:squarederror', 2), ('reg:squarederror', 4),
                 ('reg:absoluteerror', 2), ('reg:absoluteerror', 4)))]


def protocol():
    return {'version': 'level_adaptive_direct_v2_20261019', 'rows': 730,
            'partition_rows': [438, 146, 146], 'horizon': 14, 'origin_stride': 14,
            'scored_days': 140, 'omitted_tail_days': 6,
            'scenarios': list(SCENARIOS), 'formulas': FORMULAS,
            'cohorts': {name: list(seeds) for name, seeds in COHORTS.items()},
            'candidates': candidates(), 'alphas': list(ALPHAS),
            'anchor': 'mean7', 'scale': 'max(mean7,mean28/4,1VND)',
            'target': '(future_actual-anchor)/scale',
            'reconstruction': 'max(0,anchor+alpha*scale*XGB_residual)',
            'pair_weight': 'scale/median_training_pair_scales',
            'fit': 'development438;final584;no_refit_at_origins;all_pairs_inside_fit_cutoff',
            'selection': 'equal_case_mean_unrounded_MAE_ratio_to_MA7_development_only',
            'ties': 'fixed_candidate_order', 'final_targets_used_in_selection': False,
            'gates': {'overall_ratio_lt': 1., 'level_shift_ratio_lt': 1.,
                      'each_family_ratio_lte': 1.10, 'each_case_ratio_lte': 1.50},
            'scope': 'same_known_mechanisms_fresh_seeds_not_blind_external_validation',
            'business_writes': False, 'production_changed': False, 'promotion': False}


def sources():
    names = ('scripts/forecast_level_adaptive.py', 'scripts/forecast_level_benchmark.py',
             'scripts/forecast_synthetic_data.py', 'scripts/forecast_synthetic_benchmark.py',
             'apps/forecasting/features.py', 'apps/forecasting/evaluation.py')
    return {name: digest(ROOT / name) for name in names}


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
                write_json(directory / 'metadata.json', {
                    'dataset_kind': 'synthetic_simulation_not_business_observations',
                    'cohort': cohort, 'scenario': scenario, 'seed': seed, 'row_count': 730,
                    'unit': 'VND', 'business_writes': False, 'contains_PII': False,
                    'formula': FORMULAS[scenario], 'dataset_sha256': digest(directory / 'dataset.csv')})
                cases.append({'id': case_id, 'cohort': cohort, 'scenario': scenario, 'seed': seed,
                              'dataset_path': (directory / 'dataset.csv').relative_to(root).as_posix()})
    manifest = {'cases': cases, 'source_sha256': sources(), 'runtime': runtime_identity(),
                'files_sha256': {p.relative_to(root).as_posix(): digest(p)
                                 for p in sorted(root.rglob('*')) if p.is_file()}}
    write_json(root / 'input_manifest.json', manifest)
    return manifest


def verify(root):
    root = Path(root)
    try:
        manifest = json.loads((root / 'input_manifest.json').read_text(encoding='utf-8'))
        verify_files(root, manifest['files_sha256'])
        if (manifest['source_sha256'] != sources() or manifest['runtime'] != runtime_identity()
                or json.loads((root / 'protocol.json').read_text(encoding='utf-8')) != protocol()):
            raise ValueError('Frozen source/runtime/protocol mismatch')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid V2 input evidence') from error
    return manifest, digest(root / 'input_manifest.json')


def evaluate(model, history, partition, alphas=(1.,), raw_model=None):
    rows = []
    for block in origin_blocks(partition):
        known = pd.concat([history, partition.loc[partition.index < block.index[0]]])
        _, anchor, scale = origin_features(known, block.index)
        predictions = recursive_baselines(known, block.index)
        for alpha in alphas:
            name = 'adaptive' if len(alphas) == 1 else f'adaptive_{alpha}'
            predictions[name] = predict_direct(model, known, block.index, alpha)
        if raw_model is not None:
            raw, columns = raw_model
            predictions['raw_v1_xgb'] = recursive_feature_predictions(
                raw, known, block.index, DEFAULT_FEATURE_CONFIG, columns)
        for name, predicted in predictions.items():
            for step, (date, actual, value) in enumerate(zip(block.index, block.target, predicted), 1):
                rows.append({'method': name, 'origin': str(known.index[-1].date()),
                             'date': str(date.date()), 'step': step, 'actual': float(actual),
                             'prediction': float(value), 'anchor': anchor, 'scale': scale})
    return pd.DataFrame(rows)


def score_rows(rows):
    keys = ['origin', 'date', 'step']
    if not set(keys + ['method', 'actual', 'prediction']).issubset(rows.columns):
        raise ValueError('Paired origin/date/horizon/truth required')
    base = rows.loc[rows.method == 'ma7'].sort_values(keys).reset_index(drop=True)
    if base.duplicated(keys).any():
        raise ValueError('Baseline observations must be unique')
    base_mae = float(np.mean(np.abs(base.actual - base.prediction)))
    if not len(base) or not np.isfinite(base_mae) or base_mae <= 0:
        raise ValueError('Undefined MA7 comparison; do not invent improvement')
    scores = {}
    for name, group in rows.groupby('method'):
        group = group.sort_values(keys).reset_index(drop=True)
        if (len(group) != len(base) or group.duplicated(keys).any()
                or not group[keys + ['actual']].equals(base[keys + ['actual']])):
            raise ValueError('Methods must share paired observations')
        mae = float(np.mean(np.abs(group.actual - group.prediction)))
        scores[name] = {**safe_metrics(group.actual, group.prediction),
                        'mae_unrounded': mae, 'mae_ratio_to_ma7': mae / base_mae}
    return scores


def validation(attempt, frame, candidate):
    history, held = frame.iloc[:438], frame.iloc[438:584]
    model = fit_direct(history, candidate['params'])
    model.save_model(attempt / 'model.json')
    rows = evaluate(model, history, held, alphas=ALPHAS)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    metrics = score_rows(rows)
    return {'scores': {str(alpha): metrics[f'adaptive_{alpha}']['mae_ratio_to_ma7'] for alpha in ALPHAS},
            'metrics': metrics, 'fit_rows': len(history), 'fit_end': str(history.index[-1].date())}


def final(attempt, frame, selection):
    history, held = frame.iloc[:584], frame.iloc[584:]
    model = fit_direct(history, selection['params'])
    raw_model = fit_xgb(history, {**reference_params(), 'objective': 'reg:absoluteerror',
                                 'max_depth': 2, 'n_estimators': 250})
    model.save_model(attempt / 'adaptive_model.json')
    raw_model[0].save_model(attempt / 'raw_v1_model.json')
    features, _, _, trace = supervised_pairs(history)
    trace.to_csv(attempt / 'training_pair_trace.csv', index=False, lineterminator='\n')
    rows = evaluate(model, history, held, alphas=(selection['alpha'],), raw_model=raw_model)
    rows.to_csv(attempt / 'predictions.csv', index=False, lineterminator='\n')
    return {'metrics': score_rows(rows), 'fit_end': str(history.index[-1].date()),
            'fit_rows': len(history), 'training_pairs': len(trace), 'feature_columns': list(features.columns),
            'by_horizon': {str(step): score_rows(group) for step, group in rows.groupby('step')},
            'origins': rows.origin.nunique(), 'scored_days': rows.date.nunique()}


def performance_gate(cases, expected_cases):
    expected = {c['id']: (c['scenario'], c['seed']) for c in expected_cases}
    actual = {c['id']: (c['scenario'], c['seed']) for c in cases}
    complete = (len(cases) == len(expected_cases) == len(expected) == len(actual)
                and actual == expected and all(c.get('status') == 'OK' for c in cases))
    ratios = [c['ratio'] for c in cases if c.get('status') == 'OK']
    finite = bool(ratios) and np.isfinite(ratios).all() and min(ratios) >= 0
    family = {name: float(np.mean([c['ratio'] for c in cases if c.get('status') == 'OK'
                                   and c['scenario'] == name])) for name in sorted(
                                       {c['scenario'] for c in cases if c.get('status') == 'OK'})}
    mean = float(np.mean(ratios)) if ratios and finite else None
    checks = {'complete': complete, 'finite': bool(finite),
              'overall': mean is not None and mean < 1.,
              'level_shift': family.get('level_shift', float('inf')) < 1.,
              'families': bool(family) and all(value <= 1.10 for value in family.values()),
              'cases': bool(finite) and max(ratios) <= 1.50}
    return {'passed': bool(all(checks.values())), 'checks': checks,
            'mean_mae_ratio_to_ma7': mean, 'family_mean_mae_ratio': family}


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
                raise ValueError('Failed study retained; no automatic tuning/retry')
        else:
            state = {'identity': identity, 'phase': 'INPUTS_FROZEN'}
            checkpoint(root, state)
        def case_run(directory, worker):
            key = directory.relative_to(root).as_posix()
            receipt = directory / 'result.json'
            anchored = state.setdefault('receipt_sha256', {})
            if key in anchored and (not receipt.is_file() or digest(receipt) != anchored[key]):
                raise ValueError('Checkpoint-bound receipt changed')
            result = run_case(directory, identity, worker, case_key=key)
            anchored[key] = digest(receipt)
            checkpoint(root, state)
            return result
        try:
            development = [c for c in manifest['cases'] if c['cohort'] == 'development']
            trials = []
            for candidate in candidates():
                scores = {str(alpha): {} for alpha in ALPHAS}
                failures = {}
                for case in development:
                    frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                    result = case_run(root / 'development' / candidate['id'] / case['id'],
                                      lambda attempt: validation(attempt, frame, candidate))
                    if result['status'] == 'OK':
                        for alpha in ALPHAS:
                            scores[str(alpha)][case['id']] = result['payload']['scores'][str(alpha)]
                    else:
                        failures[case['id']] = result['error_class']
                    state.update(phase='VALIDATING', candidate=candidate['id'], current_case=case['id'])
                    checkpoint(root, state)
                for alpha in ALPHAS:
                    trials.append({**candidate, 'id': f"{candidate['id']}_a{alpha}", 'alpha': alpha,
                                   'scores': scores[str(alpha)], 'failures': failures.copy()})
                print(f"Development {candidate['id']}: {len(development)} cases", flush=True)
            immutable_json(root / 'trials.json', trials)
            selected = select_from_scores(trials, [c['id'] for c in development])
            selection = {key: selected[key] for key in ('id', 'params', 'alpha', 'selection_mean_mae_ratio')}
            selection.update(identity=identity, final_targets_used=False)
            immutable_json(root / 'selection.json', selection)
            state.update(phase='SELECTED', selection_sha256=digest(root / 'selection.json'))
            checkpoint(root, state)
            cases = []
            final_inputs = [c for c in manifest['cases'] if c['cohort'] == 'final']
            for case in final_inputs:
                frame = pd.read_csv(root / case['dataset_path'], index_col='date', parse_dates=True)
                result = case_run(root / 'final' / case['id'],
                                  lambda attempt: final(attempt, frame, selection))
                record = {key: case[key] for key in ('id', 'scenario', 'seed')}
                record['status'] = result['status']
                if result['status'] == 'OK':
                    record.update(result['payload'])
                    record['ratio'] = result['payload']['metrics']['adaptive']['mae_ratio_to_ma7']
                else:
                    record['error_class'] = result['error_class']
                cases.append(record)
                state.update(phase='EVALUATING', final_completed=len(cases), current_case=case['id'])
                checkpoint(root, state)
                print(f"Final {len(cases)}/{len(final_inputs)}: {case['scenario']} {result['status']}", flush=True)
            result = {'identity': identity, 'selection': selection, 'cases': cases,
                      'gate': performance_gate(cases, expected_cases=final_inputs),
                      'wins_vs_ma7': sum(c.get('ratio', float('inf')) < 1 for c in cases),
                      'production_changed': False, 'old_result_changed': False,
                      'scope': protocol()['scope']}
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
    print(json.dumps({'selection': result['selection'], 'gate': result['gate'],
                      'wins_vs_ma7': result['wins_vs_ma7']}, indent=2))
    raise SystemExit(0 if result['gate']['passed'] else 3)
