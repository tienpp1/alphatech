from django.test import SimpleTestCase
from scripts.summarize_acceptance_log import summarize


class AcceptanceLogSummaryTests(SimpleTestCase):
    def test_migration_stdout_can_prefix_first_verbose_test(self):
        data = summarize('Applying sessions.0001_initial...test_a (tests.demo.C.test_a) ... ok\nRan 1 test in 0.1s\nOK\n')
        self.assertEqual(data['observed_test_ids'], ['tests.demo.C.test_a'])

    def test_verbose_docstring_can_follow_header_on_next_line(self):
        data = summarize('test_a (tests.demo.C.test_a)\nDescription ... ok\nRan 1 test in 0.1s\nOK\n')
        self.assertEqual(data['observed_test_ids'], ['tests.demo.C.test_a'])

    def test_discovery_is_not_completion(self):
        with self.assertRaises(ValueError):
            summarize("Found 1067 test(s).\n")

    def test_rejects_combined_runs(self):
        with self.assertRaises(ValueError):
            summarize("Ran 2 tests in 1.2s\nOK\nRan 2 tests in 1.3s\nOK\n")

    def test_duplicate_cleanup_errors_not_subtracted_as_passes(self):
        data = summarize("test_x (tests.demo.C.test_x) ... ERROR\nERROR: test_x (tests.demo.C.test_x)\nERROR: test_x (tests.demo.C.test_x)\nRan 1 test in 0.1s\nFAILED (errors=2)\n")
        self.assertEqual(data["errors"], 2)
        self.assertEqual(len(data["unique_incident_test_ids"]), 1)
        self.assertIsNone(data["passes"])

    def test_tracks_skipped_without_claiming_execution(self):
        data = summarize("Ran 3 tests in 1.1s\nOK (skipped=1)\n")
        self.assertEqual(data["skipped"], 1)
        self.assertEqual(data["tests_run"], 3)

    def test_missing_incident_details_rejected(self):
        with self.assertRaises(ValueError):
            summarize("Ran 3 tests in 1.1s\nFAILED (failures=1)\n")

    def test_multiple_counts_with_spaces(self):
        data = summarize("FAIL: test_a (tests.C.test_a)\nERROR: test_b (tests.C.test_b)\nRan 3 tests in 1.1s\nFAILED (failures=1, errors=1, skipped=1)\n")
        self.assertEqual((data["failures"], data["errors"], data["skipped"]), (1, 1, 1))
