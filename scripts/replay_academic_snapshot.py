"""Replay the three packaged synthetic suites using local-only evidence settings.

Credentials stay in process environment, never copied into the evidence package.
Does not replay all UI tests: the package intentionally excludes static/templates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main(package, output):
    package = package.resolve()
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files_sha256'].items():
        path = (package / name).resolve()
        if not path.is_relative_to(package) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Package integrity mismatch: ' + name)
    output.mkdir(parents=True, exist_ok=False)
    local = dotenv_values(ROOT / '.env')
    env = os.environ.copy()
    for suffix, default in [('HOST', '127.0.0.1'), ('PORT', '5432'), ('USER', 'postgres'), ('PASSWORD', '')]:
        key = 'EVIDENCE_DB_' + suffix
        env[key] = env.get(key) or local.get(key) or env.get('DB_' + suffix) or local.get('DB_' + suffix) or default
    if env['EVIDENCE_DB_HOST'] not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Replay requires a local database')
    env['SENTRY_DSN'] = ''
    env['OTEL_EXPORTER_OTLP_ENDPOINT'] = ''
    labels = ['tests.test_adversarial_rag_execution', 'tests.test_approval_state_integrity', 'tests.test_approval_concurrency_evidence']
    command = [sys.executable, 'manage.py', 'test', *labels, '--settings=config.settings_evidence_test', '--noinput', '-v', '2']
    started = datetime.now(timezone.utc).isoformat()
    with (output / 'django.log').open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, cwd=package / 'source', env=env, stdout=stream, stderr=subprocess.STDOUT)
    report = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
              'exit_code': result.returncode, 'package_manifest_sha256': hashlib.sha256((package / 'manifest.json').read_bytes()).hexdigest(),
              'command': command[1:], 'source': str(package / 'source'), 'live_providers': False}
    (output / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.package, args.output))
