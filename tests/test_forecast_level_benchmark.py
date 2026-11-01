"""V2 evidence/chronology tests; mocked fitting never measures ML accuracy."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd


class LevelBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_level_benchmark'),
                             'Level-adaptive benchmark is missing')
        self.api = importlib.import_module('scripts.forecast_level_benchmark')

    def test_frozen_bundle_has_fresh_disjoint_seeds_and_refuses_source_runtime_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'v2'
            manifest = self.api.freeze(root)
            self.assertEqual(len(manifest['cases']), 40)
            self.assertEqual(sum(c['cohort'] == 'final' for c in manifest['cases']), 25)
            seeds = {c['seed'] for c in manifest['cases']}
            self.assertTrue(seeds.isdisjoint({2026101601, 2026101602, 2026101603, 2026101611, 2026101612, 2026101613}))
            self.api.verify(root)
            with patch.object(self.api, 'runtime_identity', return_value={'different': True}):
                with self.assertRaises(ValueError):
                    self.api.verify(root)
            with patch.object(self.api, 'sources', return_value={'different': True}):
                with self.assertRaises(ValueError):
                    self.api.verify(root)
            with self.assertRaises(FileExistsError):
                self.api.freeze(root)

    def test_direct_horizons_and_baselines_use_only_observed_origin(self):
        frame = self.api.make_series('weekly_calendar', 12345)
        history, partition = frame.iloc[:584], frame.iloc[584:]
        class SmallResidual:
            def predict(self, features):
                return features.day_of_week.to_numpy() / 100
        first = self.api.evaluate(SmallResidual(), history, partition, alphas=(.5, 1.))
        changed = partition.copy()
        changed.target += 100_000_000
        other = self.api.evaluate(SmallResidual(), history, changed, alphas=(.5, 1.))
        origin = first.origin.min()
        fields = ['method', 'origin', 'date', 'step', 'prediction', 'anchor', 'scale']
        pd.testing.assert_frame_equal(first.loc[first.origin == origin, fields],
                                      other.loc[other.origin == origin, fields])
        self.assertEqual(first.origin.nunique(), 10)
        self.assertEqual(first.date.nunique(), 140)
        self.assertEqual(first.groupby('method').size().to_list(), [140] * 5)
        for _, group in first.groupby(['method', 'origin']):
            self.assertEqual(group.step.to_list(), list(range(1, 15)))

    def test_metrics_and_gates_use_unrounded_errors_and_preserve_losses(self):
        rows = pd.DataFrame({'method': ['ma7', 'adaptive'], 'actual': [1., 1.],
                             'prediction': [1.004, 1.004001], 'origin': ['2024-01-01'] * 2,
                             'date': ['2024-01-02'] * 2, 'step': [1, 1]})
        scores = self.api.score_rows(rows)
        self.assertGreater(scores['adaptive']['mae_ratio_to_ma7'], 1)
        self.assertAlmostEqual(scores['adaptive']['mae_unrounded'], .004001)
        expected = [{'id': 'a', 'scenario': 'noise_control', 'seed': 1},
                    {'id': 'b', 'scenario': 'level_shift', 'seed': 2}]
        cases = [{**expected[0], 'status': 'OK', 'ratio': 1.11},
                 {**expected[1], 'status': 'OK', 'ratio': .5}]
        gate = self.api.performance_gate(cases, expected_cases=expected)
        self.assertFalse(gate['passed'])  #Good overall does not hide family regression.
        self.assertFalse(self.api.performance_gate(cases[:1], expected_cases=expected)['passed'])
        cases[0]['ratio'] = .9
        self.assertTrue(self.api.performance_gate(cases, expected_cases=expected)['passed'])

    def test_mismatched_truth_or_origin_cannot_produce_a_score(self):
        rows = pd.DataFrame({'method': ['ma7', 'adaptive'], 'actual': [10., 10.],
                             'prediction': [9., 10.], 'origin': ['2024-01-01'] * 2,
                             'date': ['2024-01-02'] * 2, 'step': [1, 1]})
        for field, value in (('actual', 99.), ('origin', '2023-12-31'),
                             ('date', '2024-01-03'), ('step', 2)):
            changed = rows.copy()
            changed.loc[1, field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.api.score_rows(changed)
        duplicated = pd.concat([rows, rows], ignore_index=True)
        with self.assertRaises(ValueError):
            self.api.score_rows(duplicated)

    def test_duplicate_or_mislabelled_cases_cannot_pass_complete_gate(self):
        expected = [{'id': 'a', 'scenario': 'noise_control', 'seed': 1},
                    {'id': 'b', 'scenario': 'level_shift', 'seed': 2}]
        case = {**expected[1], 'status': 'OK', 'ratio': .5}
        self.assertFalse(self.api.performance_gate([case, case.copy()], expected_cases=expected)['passed'])
        wrong = {**expected[0], 'scenario': 'level_shift', 'status': 'OK', 'ratio': .5}
        self.assertFalse(self.api.performance_gate([wrong, case], expected_cases=expected)['passed'])

    def test_failed_development_does_not_open_final_or_fake_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'failed'
            with patch.object(self.api, 'validation', side_effect=ValueError('private detail')):
                with self.assertRaises(ValueError):
                    self.api.run(root)
            self.assertFalse((root / 'selection.json').exists())
            self.assertFalse((root / 'final').exists())
            self.assertEqual(json.loads((root / 'checkpoint.json').read_text())['phase'], 'FAILED')
            trials = json.loads((root / 'trials.json').read_text())
            self.assertEqual(len(trials), 8)
            self.assertTrue(all(len(t['failures']) == 15 for t in trials))
            self.assertNotIn('private detail', json.dumps(trials))
            with self.assertRaises(ValueError):
                self.api.run(root, resume=True)

    def test_interrupted_selection_resumes_without_refit_and_changed_receipt_fails(self):
        #Only persistence orchestration is mocked; real model replay has separate tests.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'interrupted'
            def finish(attempt, frame, candidate):
                return {'scores': {'0.5': .7, '1.0': .8}}
            write = self.api.immutable_json
            def stop(path, value):
                write(path, value)
                if Path(path).name == 'selection.json':
                    raise KeyboardInterrupt()
            with patch.object(self.api, 'validation', side_effect=finish), \
                 patch.object(self.api, 'immutable_json', side_effect=stop):
                with self.assertRaises(KeyboardInterrupt):
                    self.api.run(root)
            self.assertFalse((root / 'final').exists())
            selection = json.loads((root / 'selection.json').read_text())
            self.assertEqual(selection['alpha'], .5)
            receipt = next((root / 'development').rglob('result.json'))
            changed = json.loads(receipt.read_text())
            changed['payload']['scores']['0.5'] = .001
            receipt.write_text(json.dumps(changed))
            with patch.object(self.api, 'validation', side_effect=AssertionError('Must not refit')):
                with self.assertRaises(ValueError):
                    self.api.run(root, resume=True)


if __name__ == '__main__':
    unittest.main()
