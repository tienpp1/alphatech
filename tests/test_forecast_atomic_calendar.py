"""Atomic calendar contracts; no assertion forces empirical forecast wins."""
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


class AtomicCalendarTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_atomic_calendar'),
                             'Atomic calendar implementation is missing')
        self.api = importlib.import_module('scripts.forecast_atomic_calendar')

    def test_hand_derived_one_se_selection_and_zero_variance_ties(self):
        # Full mean9, sampleSDsqrt10, SEM1 => threshold10; none9.5 is eligible.
        result = self.api.choose_atomic({'none': [9.5] * 10, 'full': [6., 12.] * 5})
        self.assertEqual(result['best_mode'], 'full')
        self.assertAlmostEqual(result['best_mean_mae'], 9.)
        self.assertAlmostEqual(result['best_sem'], 1.)
        self.assertAlmostEqual(result['threshold'], 10.)
        self.assertEqual(result['selected_mode'], 'none')
        self.assertFalse(result['statistical_guarantee'])
        self.assertEqual(self.api.choose_atomic({'none': [2.] * 10, 'full': [2.] * 10})['selected_mode'], 'none')
        self.assertEqual(self.api.choose_atomic({'none': [2.] * 10, 'full': [1.] * 10})['selected_mode'], 'full')

    def test_incomplete_non_numeric_and_overflow_evidence_fail_closed(self):
        complete = {'none': [1.] * 10, 'full': [1.] * 10}
        invalid = [{}, {'full': [1.] * 10}, {**complete, 'weekly': [1.] * 10},
                   {**complete, 'none': [1.] * 9}]
        for value in (True, float('nan'), float('inf'), -1., '1'):
            invalid.append({**complete, 'none': [value] + [1.] * 9})
        invalid.append({'none': [1e308, 0.] * 5, 'full': [1.] * 10})
        for losses in invalid:
            with self.subTest(losses=str(losses)[:80]), self.assertRaises(ValueError):
                self.api.choose_atomic(losses)

    def test_real_model_schema_save_load_and_no_calendar_invariance(self):
        import numpy as np
        import pandas as pd
        from scripts.forecast_level_adaptive import model_params, origin_features
        from scripts.forecast_synthetic_data import make_series
        history = make_series('noise_control', 12345).iloc[:100]
        features, _, _ = origin_features(history, pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=14))
        with tempfile.TemporaryDirectory() as temporary:
            for mode, width in (('none', 14), ('full', 18)):
                model = self.api.fit_atomic(history, mode, {**model_params(), 'n_estimators': 5})
                self.assertEqual(len(model.columns), width)
                expected = model.predict(features)
                path = Path(temporary) / f'{mode}.json'
                model.save_model(path)
                np.testing.assert_array_equal(self.api.load_atomic(path).predict(features), expected)
                if mode == 'none':
                    changed = features.copy()
                    changed[['day_of_week', 'day_of_month', 'month', 'is_weekend']] = 999
                    np.testing.assert_array_equal(model.predict(changed), expected)

    def test_partial_calendar_fit_and_saved_model_are_rejected(self):
        from scripts.forecast_calendar_selection import fit_mode
        from scripts.forecast_level_adaptive import model_params
        from scripts.forecast_synthetic_data import make_series
        history = make_series('noise_control', 54321).iloc[:100]
        with self.assertRaises(ValueError):
            self.api.fit_atomic(history, 'weekly')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'weekly.json'
            fit_mode(history, 'weekly', {**model_params(), 'n_estimators': 5}).save_model(path)
            with self.assertRaises(ValueError):
                self.api.load_atomic(path)
