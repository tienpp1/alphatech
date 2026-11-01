"""Frozen-study lifecycle/arithmetic, not model-accuracy assertions from mocks."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class GuardedStudyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_guarded_benchmark'),
                             'Guarded frozen study is not implemented')
        self.api = importlib.import_module('scripts.forecast_guarded_benchmark')

    def test_freeze_is_complete_create_only_and_rejects_input_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'study'
            manifest = self.api.freeze(root)
            self.assertEqual(len(manifest['cases']), 20)
            self.assertEqual({c['seed'] for c in manifest['cases']},
                             {2026110121, 2026110122, 2026110123, 2026110124})
            self.api.verify(root)
            with self.assertRaises(FileExistsError):
                self.api.freeze(root)
            path = root / manifest['cases'][0]['dataset_path']
            path.write_bytes(path.read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                self.api.verify(root)

    def test_complete_identity_and_finite_numeric_gates_not_just_average(self):
        expected = self.api.expected_cases()
        records = [{**c, 'status': 'OK', 'ratio': .8} for c in expected]
        self.assertTrue(self.api.gates(records, expected)['passed'])
        self.assertFalse(self.api.gates(records[:-1], expected)['passed'])
        self.assertFalse(self.api.gates(records[:-1] + [records[0]], expected)['passed'])
        high = [dict(c) for c in records]
        high[0]['ratio'] = 1.2
        self.assertFalse(self.api.gates(high, expected)['checks']['worst_case'])
        for bad in (True, float('nan'), float('inf'), -.1):
            changed = [dict(c) for c in records]
            changed[0]['ratio'] = bad
            with self.subTest(bad=bad):
                self.assertFalse(self.api.gates(changed, expected)['passed'])

    def test_arithmetic_audit_pairs_observed_truth_and_defines_zero_tie(self):
        rows = [{'actual': 10., 'prediction': 8., 'ma7': 6., 'observed': True},
                {'actual': 20., 'prediction': 24., 'ma7': 22., 'observed': True},
                {'actual': 999., 'prediction': 0., 'ma7': 0., 'observed': False}]
        summary = self.api.audit_rows(rows)
        self.assertEqual(summary['selected_mae'], 3.)
        self.assertEqual(summary['ma7_mae'], 3.)
        self.assertEqual(summary['ratio'], 1.)
        self.assertEqual(summary['observed_count'], 2)
        self.assertEqual(self.api.audit_rows([{'actual': 0., 'prediction': 0., 'ma7': 0.,
                                               'observed': True}])['ratio'], 1.)
        with self.assertRaises(ValueError):
            self.api.audit_rows([dict(rows[0], prediction=float('nan'))])

    def test_holdout_coverage_rejects_omission_duplicate_and_boundary_overlap(self):
        import pandas as pd
        frame = pd.DataFrame({'target': [1.] * 730}, index=pd.date_range('2024-01-01', periods=730))
        fmt = lambda i: frame.index[i].date().isoformat()
        parts = {'initial_fit': [fmt(0), fmt(437)], 'validation': [fmt(438), fmt(583)],
                 'holdout': [fmt(584), fmt(729)]}
        rows = [{'origin': fmt(origin), 'date': fmt(origin + step), 'step': step, 'observed': True}
                for origin in range(583, 716, 14) for step in range(1, 15)]
        blocks = [{'origin': fmt(i)} for i in range(437, 570, 14)]
        self.api.audit_coverage(frame, rows, parts, blocks)
        for invalid in (rows[:-1], rows + [rows[0]], rows[:-1] + [rows[0]]):
            with self.subTest(length=len(invalid)), self.assertRaises(ValueError):
                self.api.audit_coverage(frame, invalid, parts, blocks)
        with self.assertRaises(ValueError):
            self.api.audit_coverage(frame, rows, parts, [{'origin': fmt(580)}])
        for omitted in ([], blocks[:-1]):
            with self.subTest(omitted=len(omitted)), self.assertRaises(ValueError):
                self.api.audit_coverage(frame, rows, parts, omitted)

    def test_seen_diagnostic_identity_rejects_arbitrary_csv_before_freezing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'dataset.csv'
            path.write_text('date,target\n2024-01-01,1\n', encoding='utf-8')
            path.with_name('metadata.json').write_text(json.dumps({
                'scenario': 'noise_control', 'seed': 2026102236, 'row_count': 730,
                'dataset_sha256': self.api.sha(path)}), encoding='utf-8')
            with self.assertRaises(ValueError):
                self.api.verify_seen(path)


if __name__ == '__main__':
    unittest.main()
