"""Past-only adaptive XGB contracts; not a demand that a model wins every dataset."""
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd


class AdaptiveForecastTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.forecast_level_adaptive'),
                             'Adaptive implementation is missing')
        self.api = importlib.import_module('scripts.forecast_level_adaptive')

    @staticmethod
    def history(values):
        return pd.DataFrame({'target': np.asarray(values, float)},
                            index=pd.date_range('2024-01-01', periods=len(values)))

    def test_origin_arithmetic_and_reconstruction_are_hand_derived(self):
        history = self.history(np.arange(1., 57.))
        dates = pd.date_range('2024-02-26', periods=2)
        rows, anchor, scale = self.api.origin_features(history, dates)
        # Past7=50..56 mean53; past28=29..56 mean42.5; max(53,10.625,1)=53.
        self.assertEqual(anchor, 53.)
        self.assertEqual(scale, 53.)
        self.assertAlmostEqual(rows.iloc[0].lag_1, 56 / 53)
        self.assertAlmostEqual(rows.iloc[0].mean_28, 42.5 / 53)
        self.assertEqual(rows.horizon.to_list(), [1, 2])
        class Residual:
            def predict(self, features):
                return np.array([.2, -.4])
        np.testing.assert_allclose(self.api.predict_direct(Residual(), history, dates, alpha=.5), [58.3, 42.4])

    def test_training_targets_stop_at_cutoff_and_features_do_not_see_future(self):
        frame = self.history(np.arange(1., 85.))
        x, y, weights, trace = self.api.supervised_pairs(frame)
        self.assertEqual(len(x), 15 * 14 + 91)  #15 complete origins +13+12+...+1 tail pairs.
        self.assertTrue((pd.to_datetime(trace.target_date) > pd.to_datetime(trace.origin)).all())
        self.assertEqual(trace.target_date.max(), '2024-03-24')
        first = trace.origin.min()
        changed = frame.copy()
        changed.iloc[56:, 0] += 1_000_000
        other_x, other_y, _, other_trace = self.api.supervised_pairs(changed)
        pd.testing.assert_frame_equal(x.loc[trace.origin == first], other_x.loc[other_trace.origin == first])
        self.assertFalse(np.array_equal(y, other_y))
        self.assertTrue(np.isfinite(weights).all())
        self.assertTrue((weights > 0).all())

    def test_fixed_residual_predictions_follow_new_level_not_old_training_units(self):
        class ZeroResidual:
            def predict(self, features):
                return np.zeros(len(features))
        old = self.history([100.] * 80)
        low = old.copy()
        low.iloc[-28:, 0] = 30.
        dates = pd.date_range('2024-03-21', periods=14)
        np.testing.assert_array_equal(self.api.predict_direct(ZeroResidual(), old, dates), [100.] * 14)
        np.testing.assert_array_equal(self.api.predict_direct(ZeroResidual(), low, dates), [30.] * 14)
        zero = self.history([0.] * 80)
        np.testing.assert_array_equal(self.api.predict_direct(ZeroResidual(), zero, dates), [0.] * 14)

    def test_invalid_history_dates_alpha_and_nonfinite_output_are_rejected(self):
        good = self.history([20.] * 80)
        dates = pd.date_range('2024-03-21', periods=14)
        class BadResidual:
            def predict(self, features):
                return np.full(len(features), np.nan)
        for bad in (good.iloc[:10], good.iloc[::-1], good.drop(good.index[30]),
                    good.assign(target=-1), good.assign(target=np.inf)):
            with self.subTest(shape=bad.shape), self.assertRaises(ValueError):
                self.api.origin_features(bad, dates)
        with self.assertRaises(ValueError):
            self.api.predict_direct(BadResidual(), good, dates)
        with self.assertRaises(ValueError):
            self.api.predict_direct(BadResidual(), good, dates, alpha=0)
        for invalid in (good.index[-14:], dates[::-1], dates.delete(1), dates[:0]):
            with self.assertRaises(ValueError):
                self.api.origin_features(good, invalid)

    def test_real_xgb_replays_saved_model_and_is_scale_equivariant_inference(self):
        frame = self.history(1_000_000 + np.arange(100) * 1000 + np.tile([0, 0, 0, 0, 0, 200000, 200000], 15)[:100])
        model = self.api.fit_direct(frame, {**self.api.model_params(), 'n_estimators': 5})
        dates = pd.date_range(frame.index[-1] + pd.Timedelta(days=1), periods=14)
        prediction = self.api.predict_direct(model, frame, dates)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'model.json'
            model.save_model(path)
            restored = self.api.load_direct(path)
            np.testing.assert_array_equal(prediction, self.api.predict_direct(restored, frame, dates))
        np.testing.assert_allclose(self.api.predict_direct(model, frame * .5, dates), prediction * .5, rtol=1e-7)
        self.assertTrue(np.isfinite(prediction).all())
        self.assertTrue((prediction >= 0).all())


if __name__ == '__main__':
    unittest.main()
