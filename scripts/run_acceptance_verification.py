"""Run the complete Django suite on an isolated local DB and retain evidence.

No credentials are serialized. Source fingerprints detect concurrent agent edits.
This does not certify external services or production deployment.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def fingerprint():
    files = {}
    for directory in ("apps", "config", "tests"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def main():
    destination = ROOT / "output" / "acceptance_verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination.mkdir(parents=True, exist_ok=False)
    before = fingerprint()
    (destination / "source_before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    command = [sys.executable, "manage.py", "test", "tests", "--settings=config.settings_evidence_test", "--noinput", "-v", "2"]
    started = datetime.now(timezone.utc).isoformat()
    print(f"Evidence directory: {destination}", flush=True)
    with (destination / "django.log").open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    after = fingerprint()
    changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
    report = {"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "command": command[1:], "exit_code": result.returncode,
              "source_unchanged": not changed, "changed_source_paths": changed,
              "scope": "local isolated PostgreSQL/PostGIS; no production certification"}
    (destination / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return result.returncode or (2 if changed else 0)


if __name__ == "__main__":
    raise SystemExit(main())
