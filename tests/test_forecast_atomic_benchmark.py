"""V4 chronology/evidence/gates; lifecycle doubles are never accuracy evidence."""
from contextlib import redirect_stdout
import importlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class AtomicBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_atomic_benchmark'),
                             'Atomic benchmark implementation is missing')
        self.api = importlib.import_module('scripts.forecast_atomic_benchmark')

    def test_fresh_115_case_freeze_and_runtime_dataset_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'v4'
            manifest = self.api.freeze(root)
            self.assertEqual(len(manifest['cases']), 115)
            self.assertEqual(sum(c['cohort'] == 'final' for c in manifest['cases']), 100)
            self.assertEqual(len(manifest['source_sha256']), 10)
            self.assertTrue({c['seed'] for c in manifest['cases']}.isdisjoint(
                {2026101601, 2026101602, 2026101603, 2026101611, 2026101612, 2026101613,
                 2026101901, 2026101902, 2026101903, *range(2026101911, 2026101916),
                 2026101931, 2026101932, 2026101933, *range(2026101941, 2026101951)}))
            self.api.verify(root)
            with patch.object(self.api, 'runtime_identity', return_value={'changed': True}):
                with self.assertRaises(ValueError):
                    self.api.verify(root)
            path = root / manifest['cases'][0]['dataset_path']
            path.write_bytes(path.read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                self.api.verify(root)

    def test_real_calibration_excludes_final_truth_and_never_refits_584_history(self):
        frame = self.api.make_series('noise_control', 12345)
        changed = frame.copy()
        changed.iloc[584:, 0] += 1_000_000_000
        params = {**self.api.model_params(), 'n_estimators': 5}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / 'a', root / 'b'
            a.mkdir(); b.mkdir()
            first, second = self.api.calibrate(a, frame, params), self.api.calibrate(b, changed, params)
            self.assertEqual(first, second)
            self.assertEqual(first['fit_rows'], 438)
            self.assertEqual(first['fit_end'], '2025-03-13')
            self.assertEqual(first['selection_target_end'], '2025-07-31')
            self.assertEqual(set(first['metrics']), {'none', 'full', 'ma7', 'seasonal7', 'naive1'})
            for name in ('none_model.json', 'full_model.json', 'predictions.csv'):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
            self.assertFalse((a / 'weekly_model.json').exists())

    def test_failed_calibrations_are_retained_and_forbid_final(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            root = Path(temporary) / 'failed'
            with patch.object(self.api, 'calibrate', side_effect=ValueError('private exception detail')):
                with self.assertRaises(ValueError):
                    self.api.run(root)
            self.assertFalse((root / 'final').exists())
            self.assertFalse((root / 'selections.json').exists())
            receipts = list((root / 'calibration').rglob('result.json'))
            self.assertEqual(len(receipts), 115)
            self.assertTrue(all(json.loads(p.read_text())['status'] == 'FAILED' for p in receipts))
            self.assertNotIn('private exception detail', (root / 'calibration_summary.json').read_text())
            with self.assertRaises(ValueError):
                self.api.run(root, resume=True)

    def test_all_115_choices_precede_final_and_changed_selection_cannot_resume(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            parent = Path(temporary)
            fixture = parent / 'fixture'
            fixture.mkdir()
            payload = self.api.calibrate(fixture, self.api.make_series('noise_control', 54321),
                                         {**self.api.model_params(), 'n_estimators': 5})
            root = parent / 'interrupted'
            writer = self.api.immutable_json
            def stop(path, value):
                writer(path, value)
                if Path(path).name == 'selections.json':
                    raise KeyboardInterrupt()
            with patch.object(self.api, 'calibrate', return_value=payload), \
                 patch.object(self.api, 'immutable_json', side_effect=stop):
                with self.assertRaises(KeyboardInterrupt):
                    self.api.run(root)
            self.assertFalse((root / 'final').exists())
            choices = json.loads((root / 'selections.json').read_text())
            self.assertEqual(len(choices['by_case']), 115)
            selected = next(iter(choices['by_case'].values()))
            selected['selected_mode'] = 'full' if selected['selected_mode'] == 'none' else 'none'
            (root / 'selections.json').write_text(json.dumps(choices))
            with patch.object(self.api, 'calibrate', side_effect=AssertionError('Never refit receipt')):
                with self.assertRaises(ValueError):
                    self.api.run(root, resume=True)

    def test_overall_v2_and_finite_gates_cannot_be_hidden_by_ma7_gains(self):
        scenarios = ('noise_control', 'weekly_calendar', 'gradual_trend', 'intermittent_spikes', 'level_shift')
        expected = [{'id': f'final__{name}__1', 'scenario': name, 'seed': 1} for name in scenarios]
        cases = [{**case, 'status': 'OK', 'ratio': .8, 'ratio_vs_v2': .9} for case in expected]
        self.assertTrue(self.api.gates(cases, expected)['passed'])
        self.assertAlmostEqual(self.api.gates(cases, expected)['mean_ratio_vs_v2'], .9)
        worse = [{**case, 'ratio_vs_v2': 1.5 if case['scenario'] == 'intermittent_spikes' else .9} for case in cases]
        gate = self.api.gates(worse, expected)
        self.assertFalse(gate['passed'])
        self.assertFalse(gate['checks']['overall_v2'])
        for invalid in (-.2, float('nan'), float('inf'), True):
            bad = [{**case, 'ratio_vs_v2': invalid if case['scenario'] == 'intermittent_spikes' else .9} for case in cases]
            with self.subTest(invalid=invalid):
                self.assertFalse(self.api.gates(bad, expected)['passed'])
                self.assertFalse(self.api.gates(bad, expected)['checks']['v2_finite'])

    def test_boolean_or_malformed_ma7_ratios_are_rejected_before_scoring(self):
        scenarios = ('noise_control', 'weekly_calendar', 'gradual_trend', 'intermittent_spikes', 'level_shift')
        expected = [{'id': f'final__{name}__1', 'scenario': name, 'seed': 1} for name in scenarios]
        for value in (False, True, '0', float('nan'), float('inf'), -1., None):
            cases = [{**case, 'status': 'OK', 'ratio': value, 'ratio_vs_v2': .9} for case in expected]
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.api.gates(cases, expected)

    def test_completed_resume_rejects_empty_or_subset_result_manifest(self):
        # Real payload shape once; slow batch fits doubled ONLY to test durability.
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            parent = Path(temporary)
            cal, final = parent / 'cal', parent / 'final'
            cal.mkdir(); final.mkdir()
            params = {**self.api.model_params(), 'n_estimators': 2}
            with patch.object(self.api, 'model_params', return_value=params):
                frame = self.api.make_series('noise_control', 54321)
                calibration = self.api.calibrate(cal, frame)
                evaluation = self.api.outer(final, frame, calibration['selection'])
                root = parent / 'study'
                with patch.object(self.api, 'calibrate', return_value=calibration), \
                     patch.object(self.api, 'outer', return_value=evaluation):
                    original = self.api.run(root)
                self.assertEqual(self.api.run(root, resume=True), original)
                manifest_path, result_path = root / 'result_manifest.json', root / 'results.json'
                manifest_bytes, result_bytes = manifest_path.read_bytes(), result_path.read_bytes()
                forged = {**original, 'wins_vs_ma7': 999, 'gate': {**original['gate'], 'passed': True}}
                for files in ({}, {'protocol.json': self.api.digest(root / 'protocol.json')}):
                    result_path.write_text(json.dumps(forged))
                    manifest_path.write_text(json.dumps({'files_sha256': files,
                                                         'source_sha256': self.api.sources()}))
                    with self.subTest(files=files), self.assertRaises(ValueError):
                        self.api.run(root, resume=True)
                    manifest_path.write_bytes(manifest_bytes)
                    result_path.write_bytes(result_bytes)
                self.assertEqual(self.api.run(root, resume=True), original)
