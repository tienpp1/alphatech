"""Bounded offline synthetic benchmark. No Django, database, network or promotion."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import xgboost as xgb

from apps.forecasting.features import (build_features, get_feature_column_names,
                                       DEFAULT_FEATURE_CONFIG, recursive_feature_predictions)
from apps.forecasting.evaluation import (compute_metrics, generate_naive_baseline_predictions,
                                         generate_moving_average_baseline_predictions)
from scripts.forecast_synthetic_data import (build_protocol, freeze_inputs, digest, write_json,
                                               source_hashes, runtime_identity)


def reference_params():
    return {**build_protocol()['fixed_params'], 'n_estimators': 100,
            'max_depth': 4, 'objective': 'reg:squarederror'}


def candidates():
    grid = build_protocol()['candidate_grid']
    values = []
    for objective in grid['objective']:
        for depth in grid['depth']:
            for trees in grid['trees']:
                values.append({'id': f'xgb_{len(values):02d}', 'params': {
                    **reference_params(), 'objective': objective, 'max_depth': depth, 'n_estimators': trees}})
    return values


def origin_blocks(partition, horizon=14):
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError('Positive integer horizon required')
    return [partition.iloc[start:start + horizon].copy()
            for start in range(0, len(partition) - horizon + 1, horizon)]


def fit_xgb(history, params):
    if (list(history.columns) != ['target'] or len(history) < 30 or history.index.has_duplicates
            or not history.index.equals(pd.date_range(history.index[0], periods=len(history), freq='D'))
            or not np.isfinite(history.target.to_numpy(float)).all() or (history.target < 0).any()):
        raise ValueError('Require finite nonnegative continuous daily training history')
    features = build_features(history, DEFAULT_FEATURE_CONFIG)
    columns = get_feature_column_names(features)
    model = xgb.XGBRegressor(**params)
    model.fit(features[columns], features.target, verbose=False)
    return model, columns


def recursive_baselines(history, dates):
    histories = {name: history.target.to_list() for name in ('naive1', 'seasonal7', 'ma7')}
    values = {name: [] for name in histories}
    for _ in dates:
        for name, known in histories.items():
            if name == 'ma7':
                value = float(generate_moving_average_baseline_predictions(
                    np.asarray(known + [np.nan]), len(known), 7)[0])
            else:
                value = float(known[-1] if name == 'naive1' else known[-7])
            values[name].append(value)
            known.append(value)
    return values


def evaluate_methods(models, history, partition):
    rows = []
    for block in origin_blocks(partition):
        known = pd.concat([history, partition.loc[partition.index < block.index[0]]])
        predictions = recursive_baselines(known, block.index)
        for name, (model, columns) in models.items():
            predictions[name] = recursive_feature_predictions(model, known, block.index,
                                                               DEFAULT_FEATURE_CONFIG, columns)
        for name, predicted in predictions.items():
            for step, (date, actual, value) in enumerate(zip(block.index, block.target, predicted), 1):
                rows.append({'method': name, 'origin': str(known.index[-1].date()),
                             'date': str(date.date()), 'step': step,
                             'actual': float(actual), 'prediction': float(value)})
    return pd.DataFrame(rows)


def safe_metrics(actual, prediction):
    actual, prediction = np.asarray(actual, float), np.asarray(prediction, float)
    if (actual.ndim != 1 or prediction.ndim != 1 or not len(actual) or len(actual) != len(prediction)
            or not np.isfinite(actual).all() or not np.isfinite(prediction).all()):
        raise ValueError('Require paired nonempty finite predictions')
    metrics = compute_metrics(actual, prediction)
    if len(actual) <= 1 or np.var(actual) == 0:
        metrics['r2'] = None
    if not np.any(np.abs(actual) > 1e-3):
        metrics['mape'] = None
    return {**metrics, 'bias': float(np.mean(prediction - actual)), 'count': len(actual)}


def relative_score(rows, name):
    base, model = rows[rows.method == 'ma7'], rows[rows.method == name]
    base_mae = float(np.mean(np.abs(base.actual - base.prediction)))
    model_mae = float(np.mean(np.abs(model.actual - model.prediction)))
    if not len(base) or len(base) != len(model) or not np.isfinite([base_mae, model_mae]).all() or base_mae <= 0:
        raise ValueError('MA7 relative MAE is undefined; do not invent improvement')
    return model_mae / base_mae


def select_from_scores(trials, expected_case_ids):
    expected = set(expected_case_ids)
    valid = []
    for position, trial in enumerate(trials):
        scores = trial.get('scores', {})
        if (expected and not trial.get('failures') and set(scores) == expected
                and all(isinstance(value, (float, int)) and not isinstance(value, bool)
                        and np.isfinite(value) and value >= 0 for value in scores.values())):
            valid.append((float(np.mean(list(scores.values()))), position, trial))
    if not valid:
        raise ValueError('No complete valid candidate; final evaluation forbidden')
    score, _, trial = min(valid, key=lambda value: (value[0], value[1]))
    return {**trial, 'selection_mean_mae_ratio': score}


def evaluate_one_step(models, history, partition):
    full = pd.concat([history, partition])
    features = build_features(full, DEFAULT_FEATURE_CONFIG).loc[partition.index]
    predictions = {'ma7': generate_moving_average_baseline_predictions(full.target.to_numpy(), len(history), 7),
                   'naive1': generate_naive_baseline_predictions(full.target.to_numpy(), len(history), 1),
                   'seasonal7': generate_naive_baseline_predictions(full.target.to_numpy(), len(history), 7)}
    for name, (model, columns) in models.items():
        predictions[name] = np.maximum(model.predict(features[columns]), 0)
    return pd.DataFrame([{'method': name, 'date': str(date.date()), 'actual': float(actual),
                          'prediction': float(value)} for name, predicted in predictions.items()
                         for date, actual, value in zip(partition.index, partition.target, predicted)])


def verify_files(root, files):
    root = Path(root).resolve()
    for name, expected in files.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path) != expected:
            raise ValueError('Evidence artifact missing, unsafe or changed')


def verify_inputs(root):
    root = Path(root)
    try:
        manifest = json.loads((root / 'input_manifest.json').read_text(encoding='utf-8'))
        verify_files(root, manifest['files_sha256'])
        if manifest['source_sha256'] != source_hashes():
            raise ValueError('Source changed; resume would mix experiments')
        if manifest['runtime'] != runtime_identity():
            raise ValueError('Runtime changed; resume would mix library/thread configurations')
        if json.loads((root / 'protocol.json').read_text(encoding='utf-8')) != build_protocol():
            raise ValueError('Protocol changed')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid frozen input manifest') from error
    return manifest, digest(root / 'input_manifest.json')


def read_checkpoint(root, identity):
    try:
        state = json.loads((Path(root) / 'checkpoint.json').read_text(encoding='utf-8'))
        if state.get('identity') != identity or state.get('phase') not in {
                'INPUTS_FROZEN', 'VALIDATING', 'SELECTED', 'EVALUATING', 'COMPLETED', 'FAILED'}:
            raise ValueError('Checkpoint identity or phase mismatch')
    except (OSError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid or incomplete checkpoint') from error
    return state


def checkpoint(root, state):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root,
                                     prefix='checkpoint_', suffix='.tmp', delete=False) as stream:
        json.dump(state, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    Path(temporary).replace(Path(root) / 'checkpoint.json')


@contextmanager
def exclusive_run(root):
    """OS releases this advisory lock if the interpreter is killed."""
    with (Path(root) / '.run.lock').open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def immutable_json(path, value):
    path = Path(path)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError('Invalid existing immutable evidence') from error
        if existing != value:
            raise ValueError('Existing immutable evidence disagrees with verified computation')
    else:
        write_json(path, value)


def run_case(directory, identity, worker, case_key=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    case_key = case_key or f'{directory.parent.name}/{directory.name}'
    receipt = directory / 'result.json'
    if receipt.exists():
        result = json.loads(receipt.read_text(encoding='utf-8'))
        if (result['identity'] != identity or result.get('case_key') != case_key
                or result['status'] not in ('OK', 'FAILED')):
            raise ValueError('Case receipt identity/status mismatch')
        verify_files(directory, result['files_sha256'])
        expected = {key: result[key] for key in ('status', 'payload', 'error_class') if key in result}
        outcome = directory / result['attempt'] / 'outcome.json'
        if json.loads(outcome.read_text(encoding='utf-8')) != expected:
            raise ValueError('Case receipt payload differs from hashed outcome')
        return result
    number = len(list(directory.glob('attempt_*'))) + 1
    attempt = directory / f'attempt_{number:04d}'
    attempt.mkdir(exist_ok=False)
    result = {'identity': identity, 'case_key': case_key, 'attempt': attempt.name}
    try:
        result.update(status='OK', payload=worker(attempt))
    except (ValueError, xgb.core.XGBoostError) as error:
        result.update(status='FAILED', error_class=type(error).__name__)
    write_json(attempt / 'outcome.json', {key: result[key] for key in
                                        ('status', 'payload', 'error_class') if key in result})
    result['files_sha256'] = {path.relative_to(directory).as_posix(): digest(path)
                              for path in sorted(attempt.rglob('*')) if path.is_file()}
    write_json(receipt, result)
    return result


def metrics_by_method(rows):
    return {name: safe_metrics(group.actual, group.prediction) for name, group in rows.groupby('method')}


def final_case(frame, selected_params, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    history, holdout = frame.iloc[:584], frame.iloc[584:]
    models = {'selected_xgb': fit_xgb(history, selected_params),
              'reference_xgb': fit_xgb(history, reference_params())}
    for name, (model, _) in models.items():
        model.save_model(output / f'{name}.json')
    recursive = evaluate_methods(models, history, holdout)
    one_step = evaluate_one_step(models, history, holdout)
    recursive.to_csv(output / 'recursive_predictions.csv', index=False, lineterminator='\n')
    one_step.to_csv(output / 'one_step_predictions.csv', index=False, lineterminator='\n')
    result = {'fit_end': str(history.index[-1].date()), 'fit_rows': len(history),
              'recursive': metrics_by_method(recursive), 'one_step': metrics_by_method(one_step),
              'unique_recursive_dates': recursive.date.nunique(),
              'origins': recursive.origin.nunique(), 'omitted_tail_days': len(holdout) % 14,
              'by_horizon': {str(step): metrics_by_method(group) for step, group in recursive.groupby('step')}}
    write_json(output / 'metrics.json', result)
    return result


def validation_case(frame, candidate, output):
    history, validation = frame.iloc[:438], frame.iloc[438:584]
    model, columns = fit_xgb(history, candidate['params'])
    rows = evaluate_methods({'candidate': (model, columns)}, history, validation)
    rows.to_csv(output / 'predictions.csv', index=False, lineterminator='\n')
    model.save_model(output / 'model.json')
    return {'score': relative_score(rows, 'candidate'), 'metrics': metrics_by_method(rows),
            'fit_end': str(history.index[-1].date()), 'fit_rows': len(history)}


def summarize(finals):
    comparisons = []
    for case, result in finals:
        record = {key: case[key] for key in ('id', 'scenario', 'seed')}
        record['status'] = result['status']
        if result['status'] == 'OK':
            metrics = result['payload']['recursive']
            base = metrics['ma7']['mae']
            record.update(metrics=metrics, one_step=result['payload']['one_step'],
                          improvement_vs_ma7_pct=100 * (1 - metrics['selected_xgb']['mae'] / base) if base > 0 else None)
        else:
            record['error_class'] = result['error_class']
        comparisons.append(record)
    groups = {}
    for scenario in build_protocol()['scenarios']:
        values = [case['improvement_vs_ma7_pct'] for case in comparisons
                  if case['scenario'] == scenario and case['status'] == 'OK'
                  and case['improvement_vs_ma7_pct'] is not None]
        groups[scenario] = {'expected_cases': 3, 'scored_cases': len(values),
                            'wins': sum(value > 0 for value in values),
                            'losses': sum(value < 0 for value in values), 'ties': sum(value == 0 for value in values),
                            'mean_mae_improvement_pct': float(np.mean(values)) if values else None,
                            'median_mae_improvement_pct': float(np.median(values)) if values else None}
    return {'cases': comparisons, 'scenarios': groups,
            'all_final_cases_successful': all(case['status'] == 'OK' for case in comparisons),
            'historical_result_changed': False, 'production_model_changed': False,
            'commercial_superiority_established': False, 'blinded_external_evaluation': False,
            'interpretation': 'Synthetic outcomes under declared generators only; all losses retained.'}


def run(output, resume=False):
    output = Path(output)
    if not resume:
        freeze_inputs(output)
    manifest, identity = verify_inputs(output)
    with exclusive_run(output):
        if resume:
            state = read_checkpoint(output, identity)
            if state['phase'] == 'COMPLETED':
                verify_files(output, json.loads((output / 'result_manifest.json').read_text())['files_sha256'])
                return json.loads((output / 'results.json').read_text())
            if state['phase'] == 'FAILED':
                raise ValueError('Failed run retained; no automatic retry or tuning')
        else:
            state = {'identity': identity, 'phase': 'INPUTS_FROZEN'}
            checkpoint(output, state)
        def execute_case(directory, worker):
            key = directory.relative_to(output).as_posix()
            receipt = directory / 'result.json'
            anchored = state.setdefault('receipt_sha256', {})
            if key in anchored and (not receipt.is_file() or digest(receipt) != anchored[key]):
                raise ValueError('Checkpoint-bound case receipt changed')
            result = run_case(directory, identity, worker, case_key=key)
            anchored[key] = digest(receipt)
            return result
        try:
            development = [case for case in manifest['cases'] if case['cohort'] == 'development']
            trials = []
            for candidate in candidates():
                trial = {**candidate, 'scores': {}, 'failures': {}}
                for case in development:
                    frame = pd.read_csv(output / case['dataset_path'], index_col='date', parse_dates=True)
                    result = execute_case(output / 'development' / candidate['id'] / case['id'],
                                          lambda attempt: validation_case(frame, candidate, attempt))
                    destination = 'scores' if result['status'] == 'OK' else 'failures'
                    trial[destination][case['id']] = result['payload']['score'] if destination == 'scores' else result['error_class']
                    state.update(phase='VALIDATING', current_candidate=candidate['id'], current_case=case['id'])
                    checkpoint(output, state)
                trials.append(trial)
                print(f"Validation {candidate['id']}: {len(trial['scores'])}/15 cases", flush=True)
            immutable_json(output / 'trials.json', trials)
            selected = select_from_scores(trials, [case['id'] for case in development])
            selection = {'identity': identity, 'selected_id': selected['id'], 'params': selected['params'],
                         'selection_mean_mae_ratio': selected['selection_mean_mae_ratio'],
                         'final_targets_used': False}
            selection_path = output / 'selection.json'
            if selection_path.exists():
                if json.loads(selection_path.read_text()) != selection:
                    raise ValueError('Frozen selection changed')
            else:
                write_json(selection_path, selection)
            state.update(phase='SELECTED', selection_sha256=digest(selection_path))
            checkpoint(output, state)
            finals = []
            for case in [item for item in manifest['cases'] if item['cohort'] == 'final']:
                frame = pd.read_csv(output / case['dataset_path'], index_col='date', parse_dates=True)
                result = execute_case(output / 'final' / case['id'],
                                      lambda attempt: final_case(frame, selected['params'], attempt / 'evaluation'))
                finals.append((case, result))
                state.update(phase='EVALUATING', final_completed=len(finals), current_case=case['id'])
                checkpoint(output, state)
                print(f"Final {len(finals)}/15: {case['scenario']} {case['seed']} {result['status']}", flush=True)
            results = summarize(finals)
            results.update(selected=selection, runtime=manifest['runtime'])
            verify_inputs(output)
            immutable_json(output / 'results.json', results)
            files = {path.relative_to(output).as_posix(): digest(path) for path in sorted(output.rglob('*'))
                     if path.is_file() and path.name not in ('.run.lock', 'checkpoint.json', 'result_manifest.json')
                     and not path.name.endswith('.tmp')}
            immutable_json(output / 'result_manifest.json', {'files_sha256': files, 'source_sha256': source_hashes()})
            state.update(phase='COMPLETED', all_final_cases_successful=results['all_final_cases_successful'])
            checkpoint(output, state)
            return results
        except Exception as error:
            state.update(phase='FAILED', error_class=type(error).__name__)
            checkpoint(output, state)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    result = run(args.output, args.resume)
    print(json.dumps({'selected': result['selected'], 'scenarios': result['scenarios'],
                      'all_final_cases_successful': result['all_final_cases_successful']}, indent=2))
