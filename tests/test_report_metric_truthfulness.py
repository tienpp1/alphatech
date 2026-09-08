from django.test import SimpleTestCase

from config.views import _forecast_improvement


class ReportMetricTruthfulnessTests(SimpleTestCase):
    def test_measured_improvement_and_regression(self):
        self.assertEqual(_forecast_improvement(6, 10), 40.0)
        self.assertEqual(_forecast_improvement(12, 10), -20.0)
        self.assertEqual(_forecast_improvement(0, 10), 100.0)

    def test_unmeasured_or_invalid_is_not_perfect_accuracy(self):
        for mae, baseline in ((None, 10), (1, None), (1, 0), (-1, 10),
                              (True, 10), (float("nan"), 10), (1, float("inf"))):
            self.assertIsNone(_forecast_improvement(mae, baseline))
