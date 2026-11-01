import unittest

import numpy as np
import pandas as pd


def _series(n=100, freq='D'):
    dates = pd.date_range('2025-01-01', periods=n, freq=freq)
    values = 20 + np.arange(n) * 0.15 + 3 * np.sin(np.arange(n) / 5)
    return pd.DataFrame({'target': values}, index=dates)


class GuardedForecastEngineTests(unittest.TestCase):
    def test_real_xgboost_artifact_reloads_and_serves_daily_horizon(self):
        from apps.forecasting.guarded import fit_guarded, predict_artifact

        series = _series(168)
        series['target'] = [100. if date.dayofweek < 5 else 10. for date in series.index]
        result = fit_guarded(series, params={'n_estimators': 40, 'max_depth': 2})
        self.assertEqual(result['selection']['effective_model'], 'XGBOOST_DIRECT')
        prediction = predict_artifact(result['artifact'], series, horizon=14)
        self.assertEqual(prediction.shape, (14,))
        self.assertTrue(np.isfinite(prediction).all())
        self.assertTrue((prediction >= 0).all())

    def test_metrics_report_hand_computed_mape_bias_and_null_all_zero_mape(self):
        from apps.forecasting.guarded import _metrics

        metrics = _metrics([0., 2., 4.], [1., 1., 6.])
        self.assertEqual(set(metrics), {'mae', 'rmse', 'mape', 'r2', 'bias', 'count'})
        self.assertAlmostEqual(metrics['mae'], 4 / 3)
        self.assertAlmostEqual(metrics['rmse'], np.sqrt(2))
        self.assertAlmostEqual(metrics['mape'], 50.)
        self.assertAlmostEqual(metrics['r2'], .25)
        self.assertAlmostEqual(metrics['bias'], 2 / 3)
        self.assertIsNone(_metrics([0., 0.], [1., 2.])['mape'])

    def test_supported_public_override_and_test_size_boundaries_are_accepted(self):
        from apps.forecasting.adaptive import model_params
        from apps.forecasting.guarded import fit_guarded

        params = model_params({'n_estimators': 500, 'max_depth': 10})
        self.assertEqual(params['n_estimators'], 500)
        self.assertEqual(params['max_depth'], 10)
        for test_size in (.05, .5):
            with self.subTest(test_size=test_size):
                result = fit_guarded(_series(100), test_size=test_size)
                self.assertEqual(result['evaluation']['counts']['holdout'], max(14, int(100 * test_size)))

    def test_normalized_features_and_real_booster_json_roundtrip(self):
        from apps.forecasting import adaptive

        values = np.arange(1, 57, dtype=float)
        origin = pd.Timestamp('2025-02-25')
        dates = pd.date_range(origin + pd.Timedelta(days=1), periods=2, freq='D')
        features, anchor, scale = adaptive.origin_features(values, origin, dates, mode='none')
        self.assertEqual(list(features.columns), adaptive.columns_for('none'))
        self.assertAlmostEqual(anchor, 53.)
        self.assertAlmostEqual(scale, 53.)
        self.assertAlmostEqual(features.iloc[0]['lag_1'], 56 / 53)
        self.assertEqual(features.iloc[1]['horizon'], 2)
        history = _series(80)
        training_features, training_targets, sample_weights = adaptive.supervised_pairs(history)
        self.assertEqual(len(training_features), sum(range(1, 15)) + 10 * 14)
        self.assertEqual(set(training_features['horizon']), set(range(1, 15)))
        self.assertEqual(training_targets.shape, (len(training_features),))
        self.assertEqual(sample_weights.shape, (len(training_features),))
        model = adaptive.fit_direct(history, 'none', adaptive.model_params({'n_estimators': 8}))
        original = adaptive.predict_direct(model, history.target.values, history.index[-1],
                                           pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=2),
                                           mode='none')
        recovered = adaptive.booster_from_json_dict(adaptive.booster_to_json_dict(model),
                                                    adaptive.model_params({'n_estimators': 8}))
        replay = adaptive.predict_direct(recovered, history.target.values, history.index[-1],
                                         pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=2),
                                         mode='none')
        np.testing.assert_array_equal(original, replay)

    def test_paired_adoption_gates_enforce_10_percent_three_se_and_80_percent(self):
        from apps.forecasting.guarded import _paired_gates

        pass_at_ten = _paired_gates([90] * 5, [100] * 5)
        self.assertTrue(pass_at_ten['improvement_at_least_10_percent'])
        self.assertTrue(pass_at_ten['wins_at_least_80_percent'])
        exact_three_se = _paired_gates([100 - 20 / 3, 100 - 40 / 3], [100] * 2)
        self.assertFalse(exact_three_se['paired_gain_exceeds_3_sample_se'])
        at_eighty = _paired_gates([90, 90, 90, 90, 110], [100] * 5)
        self.assertTrue(at_eighty['wins_at_least_80_percent'])
        below_eighty = _paired_gates([90, 90, 90, 110, 110], [100] * 5)
        self.assertFalse(below_eighty['wins_at_least_80_percent'])
        tied = _paired_gates([10, 10], [10, 10])
        self.assertFalse(tied['improvement_at_least_10_percent'])
        self.assertFalse(tied['paired_gain_exceeds_3_sample_se'])

    def test_fit_returns_guarded_contract_and_holdout_rows_are_paired(self):
        from apps.forecasting.guarded import fit_guarded

        result = fit_guarded(_series(), params={'n_estimators': 8}, test_size=.2)

        self.assertEqual(set(result), {
            'artifact', 'selection', 'model_metrics', 'baseline_metrics',
            'feature_importances', 'evaluation', 'holdout_rows',
        })
        artifact = result['artifact']
        self.assertEqual(artifact['format'], 'alphatech_guarded_forecast_v1')
        self.assertIn(artifact['effective_model'], {'MA7', 'XGBOOST_DIRECT'})
        self.assertEqual(len(result['holdout_rows']) % 14, 0)
        for row in result['holdout_rows']:
            self.assertEqual(set(row), {
                'date', 'origin', 'step', 'actual', 'prediction', 'ma7', 'naive', 'observed'
            })

    def test_short_weekly_and_long_horizon_use_explicit_ma7_artifact(self):
        from apps.forecasting.guarded import fit_guarded, predict_artifact

        for kwargs, granularity in [
            ({}, 'WEEKLY'),
            ({'horizon': 15}, 'DAILY'),
        ]:
            result = fit_guarded(_series(80, '7D' if granularity == 'WEEKLY' else 'D'), granularity=granularity, **kwargs)
            self.assertEqual(result['artifact']['effective_model'], 'MA7')
            self.assertIsNone(result['artifact']['booster'])
            self.assertIsNone(result['artifact']['calendar_mode'])
            self.assertEqual(result['artifact']['columns'], [])
            self.assertEqual(len(predict_artifact(result['artifact'], _series(80, '7D' if granularity == 'WEEKLY' else 'D'),
                                                   horizon=kwargs.get('horizon', 14),
                                                   granularity=granularity)), kwargs.get('horizon', 14))

    def test_series_rejects_nonfinite_negative_and_insufficient_history(self):
        from apps.forecasting.guarded import fit_guarded

        bad = _series(75)
        bad.iloc[0, 0] = np.nan
        with self.assertRaises(ValueError):
            fit_guarded(bad)
        bad = _series(75)
        bad.iloc[0, 0] = -1
        with self.assertRaises(ValueError):
            fit_guarded(bad)
        with self.assertRaises(ValueError):
            fit_guarded(_series(48))

    def test_only_bounded_estimator_depth_rate_overrides_are_accepted(self):
        from apps.forecasting.guarded import fit_guarded

        result = fit_guarded(_series(), params={
            'n_estimators': 8, 'max_depth': 2, 'learning_rate': .05,
        })
        params = result['artifact']['params']
        self.assertEqual(params['n_estimators'], 8)
        self.assertEqual(params['max_depth'], 2)
        self.assertEqual(params['learning_rate'], .05)
        self.assertEqual(params['n_jobs'], 1)
        self.assertEqual(params['random_state'], 42)
        for invalid in [
            {'n_jobs': 2}, {'max_depth': True}, {'n_estimators': True},
            {'learning_rate': 0}, {'max_depth': 99}, {'n_estimators': 0},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                fit_guarded(_series(), params=invalid)

    def test_observed_dates_only_controls_scoring_not_feature_history(self):
        from apps.forecasting.guarded import fit_guarded

        series = _series(100)
        series.attrs['observed_period_dates'] = list(series.index[:-8])
        result = fit_guarded(series, params={'n_estimators': 8})
        self.assertTrue(result['evaluation']['observed_dates_count'] < len(series))
        self.assertTrue(any(row['observed'] for row in result['holdout_rows']))
        self.assertTrue(any(not row['observed'] for row in result['holdout_rows']))
        with self.assertRaises(ValueError):
            fit_guarded(series, observed_dates=[])

    def test_holdout_truth_cannot_change_selection_or_first_block_prediction(self):
        from apps.forecasting.guarded import fit_guarded

        original = _series(140)
        changed = original.copy()
        changed.iloc[-14:, 0] += 500
        first = fit_guarded(original, params={'n_estimators': 8})
        second = fit_guarded(changed, params={'n_estimators': 8})
        self.assertEqual(first['selection'], second['selection'])
        self.assertEqual(first['holdout_rows'][0]['prediction'], second['holdout_rows'][0]['prediction'])

    def test_baseline_prediction_is_recursive_ma7_and_nonnegative(self):
        from apps.forecasting.guarded import fit_guarded, predict_artifact

        series = _series(75, '7D')
        artifact = fit_guarded(series, granularity='WEEKLY')['artifact']
        pred = predict_artifact(artifact, series, horizon=3, granularity='WEEKLY')
        self.assertTrue(np.all(np.isfinite(pred)))
        self.assertTrue(np.all(pred >= 0))
        self.assertAlmostEqual(pred[0], series.target.iloc[-7:].mean())
        self.assertAlmostEqual(pred[1], (series.target.iloc[-6:].sum() + pred[0]) / 7)

    def test_missing_observed_holdout_period_is_masked_and_date_gap_is_rejected(self):
        from apps.forecasting.guarded import fit_guarded

        series = _series(75)
        observed = set(series.index)
        observed.remove(series.index[-2])
        result = fit_guarded(series, observed_dates=observed)
        self.assertFalse(result['holdout_rows'][-1]['observed'])
        self.assertEqual(result['model_metrics']['count'], 13)
        gap = series.drop(series.index[20])
        with self.assertRaises(ValueError):
            fit_guarded(gap)

    def test_validation_blocks_without_observed_truth_cannot_select_xgboost(self):
        from apps.forecasting.guarded import fit_guarded

        series = _series(140)
        observed = list(series.index[:84]) + list(series.index[112:])
        result = fit_guarded(series, params={'n_estimators': 8}, observed_dates=observed)
        self.assertTrue(result['selection']['eligible'])
        self.assertEqual(result['selection']['reason'], 'insufficient_observed_validation_blocks')
        self.assertEqual(result['artifact']['effective_model'], 'MA7')

    def test_constant_zero_holdout_has_zero_mae_and_undefined_r2(self):
        from apps.forecasting.guarded import fit_guarded

        series = _series(50)
        series['target'] = 0.
        result = fit_guarded(series)
        self.assertEqual(result['model_metrics']['mae'], 0.)
        self.assertIsNone(result['model_metrics']['r2'])


if __name__ == '__main__':
    unittest.main()
