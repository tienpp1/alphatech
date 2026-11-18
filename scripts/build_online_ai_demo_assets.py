"""Offline-only: recreate the exact pre-holdout demo model from the frozen study."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from apps.forecasting import adaptive, demo_lab as lab, guarded
from apps.forecasting.artifacts import _decode_artifact
from scripts.forecast_guarded_benchmark import audit_coverage, audit_rows, runtime, write_json


REFERENCE_SHA256 = {
    'dataset.csv': lab.HISTORY_SHA256,
    'holdout.csv': '64a6636379bf1648fa41245e4d6baffcb0e948915909ed40f1fdcc19960ae91d',
    'result.json': 'f3356c0aecf3bc8398fc08e507794f8a084d2d5a0fe375af94ad013fa0673610',
}
ENGINE_SOURCES = (
    'apps/forecasting/adaptive.py', 'apps/forecasting/guarded.py', 'apps/forecasting/artifacts.py',
    'scripts/forecast_guarded_benchmark.py',
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _reference_bytes(path):
    raw = path.read_bytes()
    if _sha(raw) != REFERENCE_SHA256[path.name]:
        raise ValueError(f'Frozen {path.name} SHA-256 differs')
    return raw


def _require_paired_parity(actual, expected):
    if len(actual) != len(expected):
        raise ValueError('Reference holdout length differs')
    for index, (row, reference) in enumerate(zip(actual, expected), start=1):
        if any(row[key] != reference[key] for key in ('date', 'origin', 'step', 'observed')):
            raise ValueError(f'Reference holdout grid differs at row {index}')
        if any(not math.isclose(row[key], reference[key], rel_tol=1e-12, abs_tol=1e-6)
               for key in ('actual', 'prediction', 'ma7', 'naive')):
            raise ValueError(f'Reference holdout numeric parity differs at row {index}')


def build(archive_root, output):
    archive_case = archive_root / 'cases' / lab.CASE_ID
    history_raw = _reference_bytes(archive_root / 'inputs' / lab.CASE_ID / 'dataset.csv')
    reference_rows = pd.read_csv(io.BytesIO(_reference_bytes(archive_case / 'holdout.csv')),
                                 float_precision='round_trip').to_dict('records')
    reference = json.loads(_reference_bytes(archive_case / 'result.json'))
    frame = pd.read_csv(io.BytesIO(history_raw), index_col='date', parse_dates=True)

    # Canonical selection is past-only. fit_guarded also creates a separate full-history
    # serving fit internally; discard that artifact and use only its selection/evaluation.
    run = guarded.fit_guarded(frame, horizon=lab.HORIZON, test_size=.2)
    selection = run['selection']
    for key in ('effective_model', 'calendar_mode', 'reason', 'params'):
        if selection[key] != reference['selection'][key]:
            raise ValueError(f'Canonical selection differs from the frozen study: {key}')
    partitions = run['evaluation']['partitions']
    if (len(frame) != lab.HISTORY_ROWS or tuple(partitions['holdout']) != lab.HOLDOUT
            or partitions['validation'][1] != lab.TRAINING_CUTOFF
            or frame.index[lab.TRAINING_ROWS - 1].date().isoformat() != lab.TRAINING_CUTOFF
            or (selection['effective_model'], selection['calendar_mode']) != (lab.MODEL, lab.CALENDAR_MODE)):
        raise ValueError('Unexpected cutoff or model for this pinned study case')
    audit_coverage(frame, reference_rows, reference['evaluation']['partitions'],
                   reference['selection']['validation_blocks'])
    audit_coverage(frame, run['holdout_rows'], partitions, selection['validation_blocks'])
    _require_paired_parity(run['holdout_rows'], reference_rows)

    model = adaptive.fit_direct(frame.iloc[:lab.TRAINING_ROWS], selection['calendar_mode'], selection['params'])
    artifact = guarded._new_artifact(selection['effective_model'], selection['params'],
                                     selection['calendar_mode'], model)
    artifact['scope'] = lab.MODEL_SCOPE
    model_raw = json.dumps(artifact, allow_nan=False, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    if len(model_raw) > 262_144:
        raise ValueError('Evaluation model exceeds its web read budget')
    rows = lab._holdout_rows(frame, _decode_artifact(model_raw, lab.MODEL_SCOPE))
    audit_coverage(frame, rows, partitions, selection['validation_blocks'])
    _require_paired_parity(rows, reference_rows)
    arithmetic = audit_rows(rows)
    for key in ('selected_mae', 'ma7_mae', 'observed_count'):
        if not math.isclose(arithmetic[key], reference['arithmetic'][key], rel_tol=1e-12, abs_tol=1e-6):
            raise ValueError(f'Independent replay arithmetic differs: {key}')
    model_sha = _sha(model_raw)
    if model_sha != lab.EVALUATION_MODEL_SHA256:
        raise ValueError('Rebuilt evaluation model differs from the pinned web asset')

    manifest = {
        **lab.MANIFEST_FIELDS,
        'files_sha256': {'history.csv': _sha(history_raw), 'evaluation_model.json': model_sha},
        'build_runtime': runtime(),
        'engine_source_sha256': {name: _sha((ROOT / name).read_bytes().replace(b'\r\n', b'\n'))
                                 for name in ENGINE_SOURCES},
        'archived_reference_sha256': REFERENCE_SHA256,
        'validation_blocks': len(selection['validation_blocks']),
        'selection_reason': selection['reason'],
        'archived_holdout_parity_rows': len(rows),
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'history.csv').open('xb') as stream:
        stream.write(history_raw)
    with (output / 'evaluation_model.json').open('xb') as stream:
        stream.write(model_raw)
    write_json(output / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path, required=True, help='Frozen guarded study directory')
    parser.add_argument('--output', type=Path, required=True, help='New directory for the audited assets')
    args = parser.parse_args()
    print(json.dumps(build(args.archive_root, args.output), indent=2, sort_keys=True))
