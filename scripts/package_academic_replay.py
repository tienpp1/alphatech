"""Package completed local test evidence and source snapshot without .env or DB data.

Requires unchanged source fingerprints; never turns failed runs into success.
Only apps/config/tests Python files recorded by the runner are included.
"""
import argparse
import hashlib
import json
import shutil
import platform
import importlib.metadata
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main(run_dir, rag_report, destination):
    result = json.loads((run_dir / 'result.json').read_text(encoding='utf-8'))
    before = json.loads((run_dir / 'source_before.json').read_text(encoding='utf-8'))
    if not result['source_unchanged']:
        raise ValueError('Source changed during run; do not certify this snapshot.')
    for name, expected in before.items():
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT) or source.suffix != '.py':
            raise ValueError('Invalid source path')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Source changed since completed run: ' + name)
    observations = json.loads(rag_report.read_text(encoding='utf-8'))
    if not observations.get('details') or any(r.get('environment') != 'OFFLINE_SYNTHETIC' for r in observations['details']):
        raise ValueError('Only explicit synthetic RAG observations may be bundled.')
    destination.mkdir(parents=True, exist_ok=False)
    for name in before:
        target = destination / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for name in ('manage.py', 'requirements.txt'):
        shutil.copyfile(ROOT / name, destination / 'source' / name)
    for name in ('django.log', 'result.json', 'source_before.json', 'test_summary.json'):
        shutil.copyfile(run_dir / name, destination / name)
    shutil.copyfile(rag_report, destination / 'rag_observations.json')
    data = [{'case_id': r['id'], 'question_index': i, 'kind': r['kind'],
             'question': r['question'], 'documents': r['fixture_documents'],
             'expected': r['expected']} for i, r in enumerate(observations['details'])]
    (destination / 'rag_dataset.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'python': platform.python_version(),
                'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions() if d.metadata['Name']},
                'run_started_utc': result['started_utc'], 'run_finished_utc': result['finished_utc'],
                'runner_exit_code': result['exit_code'], 'source_unchanged': True,
                'rag_source_path': rag_report.relative_to(ROOT).as_posix(),
                'scope': 'Synthetic local pipeline and functional approval assertions; no live LLM or human semantic grade',
                'replay': 'Use isolated local PostgreSQL/PostGIS. Install repository requirements. Run manage.py test tests.test_adversarial_rag_execution tests.test_approval_state_integrity tests.test_approval_concurrency_evidence --settings=config.settings_evidence_test --noinput -v 2',
                'limitations': 'Fresh DB IDs/timestamps may differ. Snapshot includes fixture builders, not production data. No .env or live credential files copied; synthetic test credentials remain. Full-run failures retained.',
                'files_sha256': {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'files': len(manifest['files_sha256']), 'rag_rows': len(data), 'runner_exit_code': result['exit_code']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--rag-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.run_directory.resolve(), args.rag_report.resolve(), args.output.resolve())
