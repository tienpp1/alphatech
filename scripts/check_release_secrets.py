"""Bounded high-confidence scan of Git tracked and proposed source files.

Reports paths/line numbers/types only, never matching secret values. This is not
an exhaustive entropy/history scan or evidence of provider-side key rotation.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'google_oauth_secret': re.compile(r'GOCSPX-[A-Za-z0-9_-]{20,}'),
    'github_token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'brevo_key': re.compile(r'xkeysib-[A-Za-z0-9_-]{30,}'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'credential_url': re.compile(r'(?:postgres(?:ql)?|mysql|redis)://[^\s/:]+:[^\s/@]{12,}@'),
}
SOURCE_SUFFIXES = {'.py', '.js', '.ts', '.html', '.md', '.txt', '.yaml', '.yml', '.toml', '.json', '.ini', '.cfg', '.sh', '.ps1'}


def decode_source(raw):
    # PowerShell-generated tracked reports can be UTF-16 with a BOM.
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def scan_text(path, text):
    return [{'path': path, 'line': number, 'kind': kind}
            for number, line in enumerate(text.splitlines(), 1)
            for kind, pattern in PATTERNS.items() if pattern.search(line)]


def scan_repository():
    listed = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    paths = sorted(set(listed.decode('utf-8').split('\0')) - {''})
    findings, scanned, excluded = [], 0, 0
    for name in paths:
        path = ROOT / name
        if path.name.startswith('.env') and path.name != '.env.example':
            findings.append({'path': name, 'line': None, 'kind': 'environment_file_in_release_candidates'})
            continue
        if not path.is_file() or path.is_symlink() or (path.suffix not in SOURCE_SUFFIXES and path.name != '.env.example'):
            excluded += 1
            continue
        if path.stat().st_size > 2_000_000:
            findings.append({'path': name, 'line': None, 'kind': 'oversize_source_not_scanned'})
            continue
        try:
            text = decode_source(path.read_bytes())
        except UnicodeError:
            findings.append({'path': name, 'line': None, 'kind': 'source_encoding_not_scanned'})
            continue
        findings.extend(scan_text(name, text))
        scanned += 1
    return {'scope': 'Tracked and unignored proposed source, not Git history or deployment environment',
            'files_scanned': scanned, 'non_source_entries_excluded': excluded,
            'findings': findings, 'provider_rotation_verified': False,
            'limitations': 'Known token patterns only; no exhaustive secret detection guarantee.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = scan_repository()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['findings']))
