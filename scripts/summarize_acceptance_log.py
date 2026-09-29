"""Summarize one actual unittest run. Discovery and repeated runs are not passes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def summarize(text):
    summaries = list(re.finditer(r"^Ran (\d+) tests? in ([\d.]+)s\s*$", text, re.M))
    if len(summaries) != 1:
        raise ValueError("Expected exactly one completed test run; never combine runs.")
    summary = summaries[0]
    tail = text[summary.end():]
    result = re.search(r"^(OK|FAILED)(?: \(([^\n]*)\))?\s*$", tail, re.M)
    if not result:
        raise ValueError("Missing final unittest outcome.")
    counts = dict((name.strip(), int(count)) for name, count in re.findall(r"([a-zA-Z ]+)=(\d+)", result[2] or ""))
    incidents = [{"status": m[1], "description": m[2], "test_id": m[3]}
                 for m in re.finditer(r"^(FAIL|ERROR): (.*?) \(([^\n]+)\)\s*$", text, re.M)]
    incident_counts = Counter(row["status"] for row in incidents)
    for key, status in (("failures", "FAIL"), ("errors", "ERROR")):
        if incident_counts[status] != counts.get(key, 0):
            raise ValueError(f"Incomplete incident list for {key}.")
    # stdout migration output can precede stderr's first test on the same line.
    # Match the full verbose test record, not arbitrary parenthesized log text.
    ids = sorted(set(re.findall(r"\btest\w+ \((tests\.[\w.]+)\)(?: \.\.\.|\r?\n)", text)))
    return {
        "tests_run": int(summary[1]), "seconds": float(summary[2]),
        "outcome": result[1], "failures": counts.get("failures", 0),
        "errors": counts.get("errors", 0), "skipped": counts.get("skipped", 0),
        "expected_failures": counts.get("expected failures", 0),
        "unexpected_successes": counts.get("unexpected successes", 0),
        "incidents": incidents, "unique_incident_test_ids": sorted({r["test_id"] for r in incidents}),
        "observed_test_ids": ids, "observed_unique_ids": len(ids),
        "passes": None,
        "pass_count_note": "Not inferred by subtraction: cleanup/subtest errors may repeat test IDs.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    raw = (args.run_directory / "django.log").read_bytes()
    data = summarize(raw.decode("utf-8", errors="replace"))
    manifest = json.loads((args.run_directory / "result.json").read_text(encoding="utf-8"))
    data.update(log_sha256=hashlib.sha256(raw).hexdigest(), run_manifest=manifest)
    (args.run_directory / "test_summary.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k not in ("incidents", "observed_test_ids", "run_manifest")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
