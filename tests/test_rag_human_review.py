import copy
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from django.core.management import call_command, CommandError
from apps.knowledge.human_review import create_review, summarize_review, CRITERIA


class HumanReviewTests(SimpleTestCase):
    def setUp(self):
        self.report = {"details": [
            {"id": "A", "status": "SCORED", "answer": "Doanh thu 100 đồng", "proxy_pass": True},
            {"id": "B", "status": "SCORED", "answer": "Thiếu ý"},
            {"id": "C", "status": "ERROR"},
        ]}
        self.review = create_review(self.report)

    def complete(self):
        row = self.review["reviews"][0]
        row.update({name: True for name in CRITERIA})
        row.update(reviewer="Reviewer 1", reviewed_at="2026-09-16T10:00:00+07:00",
                   reference_evidence="Fixture sales snapshot: 200 đồng", notes="Answer says 100; incorrect.")
        row["numbers_correct"] = False
        return row

    def test_blank_forms_do_not_infer_pass_from_proxy(self):
        result = summarize_review(self.report, self.review)
        self.assertEqual(result["reviewed_cases"], 0)
        self.assertIsNone(result["pass_rate_reviewed_percent"])

    def test_wrong_numbers_fail_and_missing_reviews_remain_visible(self):
        self.complete()
        result = summarize_review(self.report, self.review)
        self.assertEqual(result["failed_cases"], 1)
        self.assertEqual(result["unreviewed_cases"], 1)
        self.assertEqual(result["execution_error_cases"], 1)
        self.assertEqual(result["review_coverage_percent"], 50)
        self.assertFalse(result["all_cases_reviewed_without_execution_errors"])

    def test_changed_answer_rejects_stale_review(self):
        self.report["details"][0]["answer"] = "Doanh thu 200 đồng"
        with self.assertRaises(ValueError):
            summarize_review(self.report, self.review)

    def test_duplicate_and_failed_ids_rejected(self):
        for key in ("A", "C", "UNKNOWN"):
            review = copy.deepcopy(self.review)
            review["reviews"].append({"id": key})
            with self.subTest(key=key), self.assertRaises(ValueError):
                summarize_review(self.report, review)

    def test_completed_judgments_need_evidence_and_boolean_types(self):
        self.complete()
        for key, value in (("reference_evidence", ""), ("facts_correct", "true"), ("facts_correct", 1), ("reviewed_at", "2026-09-16")):
            changed = copy.deepcopy(self.review)
            changed["reviews"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                summarize_review(self.report, changed)

    def test_command_exports_and_preserves_existing_files(self):
        with TemporaryDirectory() as directory:
            source, output = Path(directory) / "report.json", Path(directory) / "review.json"
            source.write_text(json.dumps(self.report), encoding="utf-8")
            call_command("review_rag_evidence", report=str(source), output=str(output), stdout=StringIO())
            original = output.read_bytes()
            with self.assertRaises(CommandError):
                call_command("review_rag_evidence", report=str(source), output=str(output), stdout=StringIO())
            self.assertEqual(output.read_bytes(), original)
            summary = Path(directory) / "summary.json"
            call_command("review_rag_evidence", report=str(source), review=str(output),
                         output=str(summary), stdout=StringIO())
            result = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(result["reviewed_cases"], 0)
            self.assertIsNone(result["pass_rate_reviewed_percent"])
