"""Verify referenced source/test files and join to one completed test manifest.

This audits traceability only, not adequacy of tests or business acceptance.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(matrix, summary=None):
    rows = []
    observed = summary.get('observed_test_ids', []) if summary else []
    incidents = summary.get('incidents', []) if summary else []
    for line in matrix.read_text(encoding='utf-8').splitlines():
        if not re.match(r'\| UC\d+ \|', line):
            continue
        cells = [value.strip() for value in line.split('|')[1:-1]]
        paths = re.findall(r'(?:apps|config|tests)/[\w/]+\.py', ' '.join(cells))
        tests = [p for p in paths if p.startswith('tests/')]
        prefixes = [p[:-3].replace('/', '.') + '.' for p in tests]
        covered = [t for t in observed if any(t.startswith(p) for p in prefixes)]
        rows.append({'id': cells[0], 'requirement': cells[1], 'paths': paths,
                     'missing_files': [p for p in paths if not (ROOT / p).is_file()],
                     'test_files_without_observed_ids': [p for p, prefix in zip(tests, prefixes)
                                                        if summary and not any(t.startswith(prefix) for t in observed)],
                     'observed_test_ids': covered,
                     'incidents': [i for i in incidents if any(i['test_id'].startswith(p) for p in prefixes)],
                     'limitations': cells[-1]})
    ids = [r['id'] for r in rows]
    if not rows or len(ids) != len(set(ids)):
        raise ValueError('Empty or duplicate use-case matrix')
    return {'scope': 'Reference existence and observed execution only; no semantic/visual/live certification',
            'matrix_sha256': hashlib.sha256(matrix.read_bytes()).hexdigest(),
            'source_test_execution': summary.get('log_sha256') if summary else None,
            'rows': rows,
            'missing_files': sorted({p for r in rows for p in r['missing_files']}),
            'unobserved_test_files': sorted({p for r in rows for p in r['test_files_without_observed_ids']})}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--matrix', type=Path, default=ROOT / 'docs/ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md')
    parser.add_argument('--test-summary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.test_summary.read_text(encoding='utf-8')) if args.test_summary else None
    report = audit(args.matrix, summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'use_cases': len(report['rows']), 'missing_files': report['missing_files'],
                      'unobserved_test_files': report['unobserved_test_files']}))
    raise SystemExit(bool(report['missing_files'] or report['unobserved_test_files']))
