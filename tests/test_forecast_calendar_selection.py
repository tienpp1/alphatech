"""Calendar selection contracts, not an assertion XGB wins every noisy series."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd


class CalendarSelectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_calendar_selection'),
                             'Calendar selection module is missing')
        self.api = importlib.import_module('scripts.forecast_calendar_selection')

    @staticmethod
    def frame():
        dates = pd.date_range('2024-01-01', periods=100)
        return pd.DataFrame({'target': 20_000_000 + 5_000_000 * (dates.dayofweek >= 5)
                             + 2000 * np.arange(100)}, index=dates)

    def test_one_se_prefers_simple_mode_only_when_loss_difference_is_inconclusive(self):
        losses = {'none': [9.5] * 10, 'weekly': [10.5] * 10, 'full': [6., 12.] * 5}
        result = self.api.choose_mode(losses)
        self.assertEqual(result['best_mode'], 'full')
        self.assertEqual(result['selected_mode'], 'none')
        self.assertAlmostEqual(result['best_mean_mae'], 9.)
        self.assertAlmostEqual(result['best_sem'], 1.)  #sample variance10 /N10.
        self.assertAlmostEqual(result['threshold'], 10.)

    def test_zero_variance_or_exact_tie_cannot_waive_a_real_loss(self):
        self.assertEqual(self.api.choose_mode({'none': [10.] * 10, 'weekly': [9.] * 10,
                                              'full': [8.] * 10})['selected_mode'], 'full')
        self.assertEqual(self.api.choose_mode({mode: [8.] * 10 for mode in
                                              ('none', 'weekly', 'full')})['selected_mode'], 'none')

    def test_missing_nonfinite_negative_or_partial_losses_fail_closed(self):
        good = {mode: [8.] * 10 for mode in ('none', 'weekly', 'full')}
        for invalid in ({'none': [1.] * 10}, {**good, 'full': [1.] * 9},
                        {**good, 'full': [np.nan] * 10}, {**good, 'full': [-1.] * 10},
                        {**good, 'full': [True] * 10}, {**good, 'unknown': [1.] * 10}):
            with self.subTest(keys=list(invalid)), self.assertRaises(ValueError):
                self.api.choose_mode(invalid)

    def test_real_no_calendar_model_ignores_calendar_edits_and_survives_save_load(self):
        old = importlib.import_module('scripts.forecast_level_adaptive')
        frame = self.frame()
        model = self.api.fit_mode(frame, 'none', {**old.model_params(), 'n_estimators': 5})
        dates = pd.date_range(frame.index[-1] + pd.Timedelta(days=1), periods=14)
        features, _, _ = old.origin_features(frame, dates)
        expected = model.estimator.predict(features[model.columns])
        changed = features.copy()
        changed[['day_of_week', 'day_of_month', 'month', 'is_weekend']] = 999
        np.testing.assert_array_equal(model.predict(changed), expected)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'none.json'
            model.save_model(path)
            restored = self.api.load_mode(path)
            np.testing.assert_array_equal(restored.predict(changed), expected)
            self.assertEqual(restored.mode, 'none')
            tampered = json.loads(path.read_text())
            tampered['learner']['feature_names'][0] = 'seed'
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):
                self.api.load_mode(path)
        with self.assertRaises(ValueError):
            self.api.fit_mode(frame, 'noise_seed_1912')


if __name__ == '__main__':
    unittest.main()
