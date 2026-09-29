from io import StringIO
from django.test import SimpleTestCase
from apps.accounts.management.commands.seed_demo import Command


class SeedDemoReportingTests(SimpleTestCase):
    def test_incomplete_stages_never_report_complete(self):
        stream = StringIO()
        Command(stdout=stream)._report_completion(["retail_revenue_forecast", "recommendations"])
        self.assertIn("DEMO PARTIAL:", stream.getvalue())
        self.assertIn("retail_revenue_forecast", stream.getvalue())
        self.assertNotIn("DEMO COMPLETE:", stream.getvalue())

    def test_completed_seed_is_not_production_certification(self):
        stream = StringIO()
        Command(stdout=stream)._report_completion([])
        self.assertIn("DEMO COMPLETE:", stream.getvalue())
        self.assertIn("not production acceptance", stream.getvalue())
