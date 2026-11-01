"""V3 calibration/final separation and evidence contracts, not a guarantee of wins."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class CalendarBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_calendar_benchmark'),
                             'Calendar benchmark is missing')
        self.api = importlib.import_module('scripts.forecast_calendar_benchmark')

    def test_fresh_population_is_frozen_and_tampered_runtime_or_dataset_refuses_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'v3'
            manifest = self.api.freeze(root)
            self.assertEqual(len(manifest['cases']), 65)
            self.assertEqual(sum(c['cohort'] == 'final' for c in manifest['cases']), 50)
            self.assertTrue({c['seed'] for c in manifest['cases']}.isdisjoint(
                {2026101601, 2026101602, 2026101603, 2026101611, 2026101612, 2026101613,
                 2026101901, 2026101902, 2026101903, 2026101911, 2026101912, 2026101913,
                 2026101914, 2026101915}))
            self.api.verify(root)
            with patch.object(self.api, 'runtime_identity', return_value={'changed': True}):
                with self.assertRaises(ValueError):
                    self.api.verify(root)
            data = root / manifest['cases'][0]['dataset_path']
            data.write_bytes(data.read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                self.api.verify(root)

    def test_real_calibration_never_reads_heldout_targets_or_fits_refit_history(self):
        frame = self.api.make_series('noise_control', 12345)
        changed = frame.copy()
        changed.iloc[584:, 0] += 1_000_000_000
        params = {**self.api.model_params(), 'n_estimators': 5}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / 'original', root / 'changed'
            a.mkdir(); b.mkdir()
            first = self.api.calibrate(a, frame, params=params)
            second = self.api.calibrate(b, changed, params=params)
            self.assertEqual(first, second)
            self.assertEqual(first['fit_rows'], 438)
            self.assertEqual(first['fit_end'], '2025-03-13')
            self.assertEqual(first['selection_target_end'], '2025-07-31')
            for filename in ('none_model.json', 'weekly_model.json', 'full_model.json', 'predictions.csv'):
                self.assertEqual((a / filename).read_bytes(), (b / filename).read_bytes())

    def test_all_calibration_failures_forbid_final_and_survive_as_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'failed'
            with patch.object(self.api, 'calibrate', side_effect=ValueError('secret detail')):
                with self.assertRaises(ValueError):
                    self.api.run(root)
            self.assertFalse((root / 'final').exists())
            self.assertFalse((root / 'selections.json').exists())
            receipts = list((root / 'calibration').rglob('result.json'))
            self.assertEqual(len(receipts), 65)
            self.assertTrue(all(json.loads(p.read_text())['status'] == 'FAILED' for p in receipts))
            self.assertNotIn('secret detail', (root / 'calibration_summary.json').read_text())
            with self.assertRaises(ValueError):
                self.api.run(root, resume=True)

    def test_all_selections_are_immutable_before_any_final_and_resume_detects_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'interrupted'
            fake = {'selection': {'selected_mode': 'none'}}
            writer = self.api.immutable_json
            def stop(path, value):
                writer(path, value)
                if Path(path).name == 'selections.json':
                    raise KeyboardInterrupt()
            with patch.object(self.api, 'calibrate', return_value=fake), \
                 patch.object(self.api, 'immutable_json', side_effect=stop):
                with self.assertRaises(KeyboardInterrupt):
                    self.api.run(root)
            self.assertFalse((root / 'final').exists())
            selections = json.loads((root / 'selections.json').read_text())
            self.assertEqual(len(selections['by_case']), 65)
            selections['by_case'][next(iter(selections['by_case']))]['selected_mode'] = 'full'
            (root / 'selections.json').write_text(json.dumps(selections))
            with patch.object(self.api, 'calibrate', side_effect=AssertionError('Do not refit')):
                with self.assertRaises(ValueError):
                    self.api.run(root, resume=True)

    def test_noise_improvement_cannot_hide_regression_in_structured_family(self):
        expected = [{'id': 'a', 'scenario': 'noise_control', 'seed': 1},
                    {'id': 'b', 'scenario': 'level_shift', 'seed': 2},
                    {'id': 'c', 'scenario': 'weekly_calendar', 'seed': 3},
                    {'id': 'd', 'scenario': 'gradual_trend', 'seed': 4}]
        cases = [{**case, 'status': 'OK', 'ratio': .8, 'ratio_vs_v2': .9} for case in expected]
        self.assertTrue(self.api.gates(cases, expected)['passed'])
        cases[1]['ratio_vs_v2'] = 1.06
        self.assertFalse(self.api.gates(cases, expected)['passed'])
        cases[1]['ratio_vs_v2'] = .9
        cases[0]['ratio_vs_v2'] = 1.001
        self.assertFalse(self.api.gates(cases, expected)['passed'])


if __name__ == '__main__':
    unittest.main()
