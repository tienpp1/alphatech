"""Offline synthetic benchmark contracts, not a demand that XGB wins."""
import importlib
import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd


class SyntheticDataTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_synthetic_data'),
                             'Synthetic data implementation is missing')
        self.api = importlib.import_module('scripts.forecast_synthetic_data')

    def test_generator_repeats_seed_without_collapsing_to_constant_data(self):
        first = self.api.make_series('weekly_calendar', 2026101601)
        repeat = self.api.make_series('weekly_calendar', 2026101601)
        other = self.api.make_series('weekly_calendar', 2026101602)
        pd.testing.assert_frame_equal(first, repeat)
        self.assertFalse(first.equals(other))
        self.assertGreater(first.target.std(), 1_000_000)
        self.assertEqual(len(first), 730)
        self.assertEqual(list(first.columns), ['target'])
        self.assertTrue(first.index.equals(pd.date_range('2024-01-01', periods=730)))
        self.assertTrue(np.isfinite(first.target).all())
        self.assertTrue((first.target >= 0).all())

    def test_all_scenarios_have_valid_truth_and_unknown_scenario_is_rejected(self):
        for scenario in ('noise_control', 'weekly_calendar', 'gradual_trend',
                         'intermittent_spikes', 'level_shift'):
            frame = self.api.make_series(scenario, 2026101601)
            self.assertEqual(len(frame), 730)
            self.assertTrue(np.isfinite(frame.target).all())
            self.assertTrue((frame.target >= 0).all())
        with self.assertRaises(ValueError):
            self.api.make_series('unknown', 2026101601)

    def test_freeze_preserves_all_cases_with_synthetic_provenance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'new'
            manifest = self.api.freeze_inputs(root)
            self.assertEqual(len(manifest['cases']), 30)
            self.assertEqual(len({case['id'] for case in manifest['cases']}), 30)
            for case in manifest['cases']:
                frame = pd.read_csv(root / case['dataset_path'])
                meta = json.loads((root / case['metadata_path']).read_text())
                self.assertEqual(len(frame), 730)
                self.assertEqual(meta['dataset_kind'], 'synthetic_simulation_not_business_observations')
                self.assertFalse(meta['business_writes'])
                self.assertEqual(meta['cohort'], case['cohort'])
                self.assertEqual(meta['row_count'], 730)
            protocol = json.loads((root / 'protocol.json').read_text())
            self.assertEqual(protocol['partition_rows'], [438, 146, 146])
            before = (root / 'protocol.json').read_bytes()
            with self.assertRaises(FileExistsError):
                self.api.freeze_inputs(root)
            self.assertEqual((root / 'protocol.json').read_bytes(), before)


class SyntheticEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_synthetic_benchmark'),
                             'Synthetic evaluation implementation is missing')
        self.api = importlib.import_module('scripts.forecast_synthetic_benchmark')

    @staticmethod
    def frame(size=176):
        return pd.DataFrame({'target': np.arange(1., size + 1)},
                            index=pd.date_range('2024-01-01', periods=size))

    def test_complete_blocks_are_disjoint_and_omit_only_incomplete_tail(self):
        partition = self.frame().iloc[30:]
        blocks = self.api.origin_blocks(partition)
        self.assertEqual(len(blocks), 10)
        dates = [date for block in blocks for date in block.index]
        self.assertEqual(len(dates), 140)
        self.assertEqual(len(set(dates)), 140)
        self.assertEqual(dates[0], pd.Timestamp('2024-01-31'))
        self.assertEqual(dates[-1], partition.index[139])
        self.assertEqual(len(partition.index.difference(dates)), 6)

    def test_recursive_baselines_append_predictions_not_future_truth(self):
        history = self.frame(30)
        dates = pd.date_range('2024-01-31', periods=14)
        values = self.api.recursive_baselines(history, dates)
        self.assertEqual(values['naive1'], [30.] * 14)
        self.assertEqual(values['seasonal7'][:8], [24., 25., 26., 27., 28., 29., 30., 24.])
        self.assertEqual(values['ma7'][0], 27.)
        self.assertAlmostEqual(values['ma7'][1], 192 / 7)
        self.assertEqual(history.iloc[-1].target, 30.)

    def test_selection_uses_equal_case_ratios_and_rejects_partial_failures(self):
        trials = [
            {'id': 'a', 'scores': {'one': .2, 'two': 2.}, 'failures': {}},
            {'id': 'b', 'scores': {'one': .9, 'two': .9}, 'failures': {}},
            {'id': 'partial', 'scores': {'one': .01}, 'failures': {'two': 'ValueError'}},
        ]
        self.assertEqual(self.api.select_from_scores(trials, ['one', 'two'])['id'], 'b')
        with self.assertRaises(ValueError):
            self.api.select_from_scores(trials[2:], ['one', 'two'])

    def test_zero_denominator_never_becomes_invented_improvement(self):
        rows = pd.DataFrame({'method': ['ma7', 'candidate'], 'actual': [5., 5.],
                             'prediction': [5., 7.]})
        with self.assertRaises(ValueError):
            self.api.relative_score(rows, 'candidate')
        metrics = self.api.safe_metrics([0., 0.], [3., 4.])
        self.assertIsNone(metrics['r2'])
        self.assertIsNone(metrics['mape'])
        self.assertEqual(metrics['mae'], 3.5)

    def test_real_xgb_first_origin_is_invariant_to_future_target_mutation(self):
        frame = self.frame(90)
        history, partition = frame.iloc[:60], frame.iloc[60:]
        params = {**self.api.reference_params(), 'n_estimators': 5, 'max_depth': 2}
        model, columns = self.api.fit_xgb(history, params)
        before = self.api.evaluate_methods({'candidate': (model, columns)}, history, partition)
        changed = partition.copy()
        changed.target += 100_000
        after = self.api.evaluate_methods({'candidate': (model, columns)}, history, changed)
        first = before.origin.min()
        fields = ['method', 'origin', 'date', 'step', 'prediction']
        pd.testing.assert_frame_equal(before.loc[before.origin == first, fields],
                                      after.loc[after.origin == first, fields])
        self.assertFalse(before.actual.equals(after.actual))
        self.assertTrue((before.prediction >= 0).all())


class SyntheticEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module('scripts.forecast_synthetic_benchmark')

    def test_corrupt_inputs_or_source_identity_cannot_resume(self):
        self.assertTrue(callable(getattr(self.api, 'verify_inputs', None)), 'Missing input verification')
        data = importlib.import_module('scripts.forecast_synthetic_data')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            data.freeze_inputs(root)
            self.api.verify_inputs(root)
            case = json.loads((root / 'input_manifest.json').read_text())['cases'][0]
            dataset = root / case['dataset_path']
            dataset.write_bytes(dataset.read_bytes() + b'corruption')
            with self.assertRaises(ValueError):
                self.api.verify_inputs(root)

    def test_corrupt_checkpoint_is_not_treated_as_new_success(self):
        self.assertTrue(callable(getattr(self.api, 'read_checkpoint', None)), 'Missing checkpoint verification')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'checkpoint.json').write_text('{truncated')
            with self.assertRaises(ValueError):
                self.api.read_checkpoint(root, 'expected-identity')
            (root / 'checkpoint.json').write_text(json.dumps({'identity': 'wrong', 'phase': 'COMPLETED'}))
            with self.assertRaises(ValueError):
                self.api.read_checkpoint(root, 'expected-identity')

    def test_real_final_models_replay_and_do_not_fit_future_targets(self):
        self.assertTrue(callable(getattr(self.api, 'final_case', None)), 'Missing final case runner')
        data = importlib.import_module('scripts.forecast_synthetic_data')
        frame = data.make_series('weekly_calendar', 2026101611)
        altered = frame.copy()
        altered.iloc[584:, 0] += 100_000_000
        selected = {**self.api.reference_params(), 'n_estimators': 5, 'max_depth': 2}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.api.final_case(frame, selected, root / 'first')
            self.api.final_case(frame, selected, root / 'replay')
            self.api.final_case(altered, selected, root / 'changed')
            for name in ('selected_xgb.json', 'reference_xgb.json', 'recursive_predictions.csv', 'one_step_predictions.csv'):
                self.assertEqual((root / 'first' / name).read_bytes(), (root / 'replay' / name).read_bytes())
            for name in ('selected_xgb.json', 'reference_xgb.json'):
                self.assertEqual((root / 'first' / name).read_bytes(), (root / 'changed' / name).read_bytes())
            before = pd.read_csv(root / 'first/recursive_predictions.csv')
            after = pd.read_csv(root / 'changed/recursive_predictions.csv')
            origin = before.origin.min()
            fields = ['method', 'origin', 'date', 'step', 'prediction']
            pd.testing.assert_frame_equal(before.loc[before.origin == origin, fields],
                                          after.loc[after.origin == origin, fields])
            self.assertEqual(first['recursive']['selected_xgb']['count'], 140)
            self.assertEqual(first['omitted_tail_days'], 6)
            self.assertLess(first['fit_end'], str(frame.index[584].date()))
            with self.assertRaises(FileExistsError):
                self.api.final_case(frame, selected, root / 'first')

    def test_failed_receipt_is_retained_and_partial_attempt_can_resume_without_overwrite(self):
        self.assertTrue(callable(getattr(self.api, 'run_case', None)), 'Missing durable case runner')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'failed'
            def fail(attempt):
                raise ValueError('sensitive details must not leak')
            first = self.api.run_case(directory, 'identity', fail)
            self.assertEqual(first['status'], 'FAILED')
            self.assertEqual(first['error_class'], 'ValueError')
            self.assertNotIn('sensitive', json.dumps(first))
            again = self.api.run_case(directory, 'identity', lambda _: self.fail('Must not retry recorded failure'))
            self.assertEqual(first, again)
            partial = root / 'partial'
            (partial / 'attempt_0001').mkdir(parents=True)
            (partial / 'attempt_0001/partial.txt').write_text('interrupted')
            result = self.api.run_case(partial, 'identity', lambda attempt: {'value': 12})
            self.assertEqual(result['status'], 'OK')
            self.assertEqual(result['attempt'], 'attempt_0002')
            self.assertEqual((partial / 'attempt_0001/partial.txt').read_text(), 'interrupted')

    def test_all_fit_failures_remain_visible_and_final_evaluation_never_starts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'failed_search'
            with patch.object(self.api, 'fit_xgb', side_effect=ValueError('private transport details')):
                with self.assertRaises(ValueError):
                    self.api.run(root)
            trials = json.loads((root / 'trials.json').read_text())
            self.assertEqual(len(trials), 12)
            self.assertTrue(all(len(trial['failures']) == 15 and not trial['scores'] for trial in trials))
            self.assertEqual(json.loads((root / 'checkpoint.json').read_text())['phase'], 'FAILED')
            self.assertFalse((root / 'final').exists())
            self.assertFalse((root / 'selection.json').exists())
            self.assertNotIn('private', (root / 'trials.json').read_text())
            with self.assertRaises(FileExistsError):
                self.api.run(root)
            with self.assertRaises(ValueError):
                self.api.run(root, resume=True)

    def test_exclusive_run_prevents_a_second_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.api.exclusive_run(Path(temporary)):
                with self.assertRaises(OSError):
                    with self.api.exclusive_run(Path(temporary)):
                        self.fail('Two benchmark writers must not hold the same lock')

    @contextmanager
    def lightweight_orchestration(self):
        # Isolate persistence control, not model performance (tested with real XGB above).
        metric = {'mae': 5., 'rmse': 6., 'mape': 1., 'r2': -.5, 'count': 140}
        payload = {'recursive': {name: metric.copy() for name in
                                ('selected_xgb', 'reference_xgb', 'ma7', 'naive1', 'seasonal7')},
                   'one_step': {'selected_xgb': metric.copy()}}
        with patch.object(self.api, 'validation_case', return_value={'score': 1.0}), \
             patch.object(self.api, 'final_case', return_value=payload):
            yield

    def test_resume_rejects_stale_trial_summary(self):
        with tempfile.TemporaryDirectory() as temporary, self.lightweight_orchestration():
            root = Path(temporary) / 'bundle'
            write = self.api.write_json
            def interrupt(path, value):
                write(path, value)
                if Path(path).name == 'trials.json':
                    raise KeyboardInterrupt()
            with patch.object(self.api, 'write_json', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.api.run(root)
            (root / 'trials.json').write_text(json.dumps({'stale': True}))
            with self.assertRaises(ValueError):
                self.api.run(root, resume=True)
            self.assertFalse((root / 'final').exists())

    def test_resume_finalizes_after_each_immutable_finalization_write(self):
        for boundary in ('results.json', 'result_manifest.json'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temporary, self.lightweight_orchestration():
                root = Path(temporary) / 'bundle'
                write = self.api.write_json
                def interrupt(path, value):
                    write(path, value)
                    if Path(path).name == boundary:
                        raise KeyboardInterrupt()
                with patch.object(self.api, 'write_json', side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        self.api.run(root)
                saved = (root / 'results.json').read_bytes()
                try:
                    result = self.api.run(root, resume=True)
                except FileExistsError:
                    self.fail('A valid interrupted finalization must resume, not fail on existing immutable artifacts')
                self.assertTrue(result['all_final_cases_successful'])
                self.assertEqual((root / 'results.json').read_bytes(), saved)
                self.assertEqual(json.loads((root / 'checkpoint.json').read_text())['phase'], 'COMPLETED')

    def test_cached_receipt_rejects_changed_payload_and_swapped_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'case_a'
            self.api.run_case(source, 'bundle', lambda attempt: {'score': .5})
            swapped = root / 'case_b'
            shutil.copytree(source, swapped)
            with self.assertRaises(ValueError):
                self.api.run_case(swapped, 'bundle', lambda _: self.fail('Must reject swap before worker'))
            receipt = source / 'result.json'
            changed = json.loads(receipt.read_text())
            changed['payload']['score'] = .01
            receipt.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                self.api.run_case(source, 'bundle', lambda _: self.fail('Must reject tampered payload'))

    def test_runtime_identity_is_frozen_and_resume_refuses_mixed_versions(self):
        data = importlib.import_module('scripts.forecast_synthetic_data')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'bundle'
            manifest = data.freeze_inputs(root)
            self.assertTrue('runtime' in manifest, 'Runtime must be frozen before fitting')
            manifest['runtime']['numpy'] = 'different-runtime'
            (root / 'input_manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.api.verify_inputs(root)


if __name__ == '__main__':
    unittest.main()
