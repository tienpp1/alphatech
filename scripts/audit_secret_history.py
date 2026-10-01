"""Read-only pattern scan of reachable Git history; never print secret values."""
import argparse
import json
import subprocess
from pathlib import Path
from check_release_secrets import PATTERNS, ROOT


def scan_history():
    process = subprocess.Popen(
        ['git', 'log', '--all', '--format=AUDIT_COMMIT:%H', '--no-ext-diff',
         '--no-renames', '--unified=0', '-p'],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace',
    )
    findings = set()
    commits = set()
    commit, path = '', ''
    for line in process.stdout:
        if line.startswith('AUDIT_COMMIT:'):
            commit = line.strip().split(':', 1)[1]
            commits.add(commit)
        elif line.startswith('+++ b/'):
            path = line[6:].strip()
        elif line.startswith('+') and not line.startswith('+++'):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.add((commit, path, kind))
    _, error = process.communicate(timeout=30)
    if process.returncode:
        raise RuntimeError('GIT_HISTORY_SCAN_FAILED')
    return {
        'scope': 'Added text in all reachable local Git commits; no remote fetch',
        'commits_scanned': len(commits),
        'findings': [dict(commit=c, path=p, kind=k) for c,p,k in sorted(findings)],
        'limitations': 'Known patterns only; excludes unreachable objects, binary content and provider rotation verification.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = scan_history()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['findings']))
