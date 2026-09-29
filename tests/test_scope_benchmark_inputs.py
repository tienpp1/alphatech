from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from apps.knowledge.scope_benchmark import APPROVED_SCOPE_CASES


class ApprovedScopeBenchmarkInputTests(SimpleTestCase):
    def test_case_ids_are_unique_and_sources_exist(self):
        ids = [case["id"] for case in APPROVED_SCOPE_CASES]
        self.assertEqual(len(ids), len(set(ids)))
        for case in APPROVED_SCOPE_CASES:
            source = Path(settings.BASE_DIR) / case["source_path"]
            self.assertTrue(source.is_file(), case["source_path"])

    def test_expected_facts_are_present_in_the_declared_sop(self):
        for case in APPROVED_SCOPE_CASES:
            source = Path(settings.BASE_DIR) / case["source_path"]
            content = source.read_text(encoding="utf-8")
            for fact in case["required_facts"]:
                self.assertIn(fact, content, f"{fact!r} missing from {case['source_path']}")
