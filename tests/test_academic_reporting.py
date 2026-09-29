"""Pure reporting regressions: no database, API or email required."""
from unittest import TestCase

from apps.forecasting.academic_reporting import improvement, measured, render_report


class AcademicReportingTests(TestCase):
    def row(self, **changes):
        row = dict(id=1, workspace='retail', config=1, target='RETAIL_REVENUE',
                   status='COMPLETED', train=61, test=15, metrics={'mae': 12, 'r2': -3.374},
                   baseline={'naive_mae': 10}, start='2026-01-01', end='2026-03-01', parameters={})
        row.update(changes)
        return row

    def report(self, rows):
        return render_report(rows, dict(recommendations=4, approvals=3, statuses={'PENDING': 3}), 'fixed-time')

    def test_invalid_metrics_are_unmeasured(self):
        for value in (None, True, '1', -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.assertIsNone(measured(value))
                self.assertIsNone(improvement(value, 10))
        self.assertIsNone(improvement(1, 0))
        self.assertIsNone(improvement(1, None))
        self.assertEqual(improvement(0, 10), 100)

    def test_regression_and_negative_r2_are_reported(self):
        result = self.report([self.row()])
        self.assertIn('Kém baseline', result)
        self.assertIn('-20.0000', result)
        self.assertIn('R² âm', result)
        self.assertNotIn('vượt trội', result)

    def test_missing_metrics_not_zero(self):
        self.assertIn('Chưa đo', self.report([self.row(metrics={}, baseline={})]))

    def test_provenance_is_explicit_and_legacy_is_not_invented(self):
        result = self.report([self.row(parameters={'private_key': 'DO-NOT-EXPORT'})])
        self.assertIn('Chưa ghi nhận provenance', result)
        self.assertNotIn('DO-NOT-EXPORT', result)
        result = self.report([self.row(parameters={'provenance': {
            'dataset': {'missing_period_count': 0, 'unit': 'VND'},
            'split': {'validation': 'no_separate_validation_partition'},
            'training_config': {'random_state': 42}, 'runtime': {'xgboost': 'test-version'},
        }})])
        self.assertIn('| dataset.missing_period_count | 0 |', result)
        self.assertIn('| dataset.unit | VND |', result)
        self.assertIn('no_separate_validation_partition', result)
        self.assertIn('test-version', result)
        self.assertIn('| artifact_sha256 | Chưa ghi nhận |', result)

    def test_failed_run_does_not_publish_stale_metrics(self):
        result = self.report([self.row(status='FAILED')])
        self.assertIn('FAILED', result)
        self.assertNotIn('-3.3740', result)

    def test_empty_test_set_and_malformed_metrics_are_unmeasured(self):
        for changes in ({'test': 0}, {'test': None}, {'metrics': ['invalid'], 'baseline': 'invalid'}):
            with self.subTest(changes=changes):
                result = self.report([self.row(**changes)])
                self.assertIn('Chưa đo', result)
                self.assertNotIn('-3.3740', result)

    def test_each_run_kept(self):
        result = self.report([self.row(), self.row(id=2, config=2)])
        self.assertIn('Run 1:', result)
        self.assertIn('Run 2:', result)

    def test_empty_and_unmeasured_sections(self):
        result = self.report([])
        self.assertIn('Chưa có run', result)
        self.assertIn('Tuân thủ phê duyệt: CHƯA ĐO', result)
        self.assertIn('CHƯA ĐÁNH GIÁ', result)
        self.assertNotIn('100%', result)

    def test_precision_and_zero_baseline_preserved(self):
        result = self.report([self.row(metrics={'mae': 0.61}, baseline={'naive_mae': 1})])
        self.assertIn('0.6100', result)
        self.assertIn('39.0000', result)
        result = self.report([self.row(baseline={'naive_mae': 0, 'mae': 10})])
        self.assertIn('Chưa đủ dữ liệu', result)
