"""Offline human adjudication. Never infer judgments from lexical scores."""
import hashlib
import json


CRITERIA = ("facts_correct", "numbers_correct", "complete", "citations_support_claims")


def fingerprint(report):
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def details_by_id(report):
    rows = report.get("details")
    if not isinstance(rows, list):
        raise ValueError("Report must contain a details list.")
    indexed = {}
    for row in rows:
        key = row.get("id") if isinstance(row, dict) else None
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError("Each case needs a unique, nonempty string id.")
        indexed[key] = row
    return indexed


def create_review(report):
    rows = details_by_id(report)
    return {
        "schema_version": 1,
        "report_sha256": fingerprint(report),
        "reviews": [{
            "id": key, "question": row.get("question"), "answer": row.get("answer"),
            "sources": row.get("sources", []), "tools_used": row.get("tools_used", []),
            "reference_documents": row.get("reference_documents", []),
            "expected": row.get("expected"),
            "reviewer": "", "reviewed_at": "",
            "reference_evidence": "", "notes": "",
            **{name: None for name in CRITERIA},
        } for key, row in rows.items() if row.get("status", "SCORED") == "SCORED"],
    }


def prepare_adversarial_review(observations):
    """Adapt recorded offline observations, never manufacture semantic grades.

    Paraphrases share a fixture id, so index each recorded question separately.
    Denied cases remain visible outside the answer-quality denominator.
    """
    records = observations.get('details')
    if not isinstance(records, list) or not records:
        raise ValueError('Missing recorded observations.')
    details, excluded = [], []
    for index, row in enumerate(records):
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id']:
            raise ValueError('Invalid fixture id.')
        key = f"{row['id']}@{index + 1}"
        if row.get('status') == 'DENIED':
            excluded.append({'id': key, 'fixture_id': row['id'], 'question': row.get('question'),
                             'status': 'DENIED', 'reason': 'Access denial is not a generated answer to grade.'})
            continue
        response = row.get('response')
        if row.get('status') != 'ANSWERED' or not isinstance(response, dict) or not isinstance(response.get('answer'), str) or not response['answer'].strip():
            raise ValueError('Expected an actual recorded answer or denial.')
        details.append({'id': key, 'fixture_id': row['id'], 'question': row.get('question'),
                        'answer': response['answer'], 'sources': response.get('sources', []),
                        'tools_used': response.get('tools_used', []), 'status': 'SCORED',
                        'reference_documents': row.get('fixture_documents', []),
                        'expected': row.get('expected'), 'environment': row.get('environment')})
    return {'details': details, 'excluded_cases': excluded,
            'original_observations_sha256': fingerprint(observations),
            'scope': 'Recorded answer review only; SCORED means eligible, not semantically correct. Denials excluded explicitly.'}


def summarize_review(report, review):
    from datetime import datetime

    rows = details_by_id(report)
    if review.get("schema_version") != 1 or review.get("report_sha256") != fingerprint(report):
        raise ValueError("Review version or report fingerprint mismatch.")
    entries = review.get("reviews")
    if not isinstance(entries, list):
        raise ValueError("Review must contain a reviews list.")
    seen, judgments = set(), []
    for entry in entries:
        key = entry.get("id")
        if key not in rows or key in seen or rows[key].get("status", "SCORED") != "SCORED":
            raise ValueError("Unknown, duplicate or failed case cannot be reviewed.")
        seen.add(key)
        values = [entry.get(name) for name in CRITERIA]
        if any(value is not None and type(value) is not bool for value in values):
            raise ValueError("Judgments must be true, false or null.")
        if any(value is None for value in values):
            continue
        if not all(isinstance(entry.get(name), str) and entry[name].strip()
                   for name in ("reviewer", "reviewed_at", "reference_evidence", "notes")):
            raise ValueError("Completed reviews require reviewer, timestamp, reference evidence and notes.")
        try:
            reviewed_at = datetime.fromisoformat(entry["reviewed_at"])
            if reviewed_at.utcoffset() is None:
                raise ValueError()
        except ValueError:
            raise ValueError("reviewed_at must be an ISO timestamp with timezone.") from None
        judgments.append({"id": key, "passed": all(values), **{name: entry[name] for name in CRITERIA},
                          **{name: entry[name] for name in ("reviewer", "reviewed_at", "reference_evidence", "notes")}})
    total = len(rows)
    eligible = sum(row.get("status", "SCORED") == "SCORED" for row in rows.values())
    passed = sum(row["passed"] for row in judgments)
    return {
        "metric_kind": "HUMAN_REVIEW_REPORTED_JUDGMENTS",
        "report_sha256": fingerprint(report),
        "total_cases": total, "execution_error_cases": total - eligible,
        "reviewed_cases": len(judgments), "unreviewed_cases": eligible - len(judgments),
        "passed_cases": passed, "failed_cases": len(judgments) - passed,
        "review_coverage_percent": round(100 * len(judgments) / eligible, 2) if eligible else None,
        "pass_rate_reviewed_percent": round(100 * passed / len(judgments), 2) if judgments else None,
        "all_cases_reviewed_without_execution_errors": len(judgments) == total and total > 0,
        "limitations": "Human-entered judgments; reviewer identity and evidence authenticity are not verified by this tool.",
        "judgments": judgments,
    }
