"""Prediction parity, failure preservation and immutable training configuration."""
import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from django.test import SimpleTestCase, TestCase

from apps.forecasting.features import build_features, recursive_feature_predictions
from apps.forecasting.models import ForecastModelConfig, ForecastRun, ForecastResult, TargetType, Granularity
from apps.forecasting.prediction import generate_future_forecast
from apps.workspaces.models import Workspace, WorkspaceType


class RecursiveFeatureParityTests(SimpleTestCase):
    def test_configured_features_and_sample_std_match_training(self):
        history = pd.DataFrame({'target': np.arange(1., 31.)}, index=pd.date_range('2026-01-01', periods=30))
        date = history.index[-1] + pd.Timedelta(days=1)
        config = {'lags': [2, 5], 'rolling_windows': [3, 10], 'calendar_features': False}
        model = Mock()
        model.predict.return_value = [40.]
        recursive_feature_predictions(model, history, [date], config)
        extended = history.copy()
        extended.loc[date, 'target'] = 999999.
        expected = build_features(extended, config).drop(columns='target').loc[[date]]
        pd.testing.assert_frame_equal(model.predict.call_args.args[0], expected)
        self.assertAlmostEqual(expected.iloc[0]['rolling_std_3'], 1.)

    def test_second_step_uses_prediction_not_future_actual(self):
        history = pd.DataFrame({'target': [1., 2., 3.]}, index=pd.date_range('2026-01-01', periods=3))
        model = Mock()
        model.predict.side_effect = [[10.], [20.]]
        result = recursive_feature_predictions(model, history, pd.date_range('2026-01-04', periods=2),
            {'lags': [1], 'rolling_windows': [], 'calendar_features': False})
        self.assertEqual(result.tolist(), [10., 20.])
        self.assertEqual(model.predict.call_args_list[1].args[0].iloc[0]['lag_1'], 10.)
        self.assertEqual(len(history), 3)

    def test_insufficient_history_or_nonfinite_prediction_is_rejected(self):
        history = pd.DataFrame({'target': [1., 2.]}, index=pd.date_range('2026-01-01', periods=2))
        model = Mock()
        with self.assertRaises(ValueError):
            recursive_feature_predictions(model, history, [pd.Timestamp('2026-01-03')])
        model.predict.return_value = [float('nan')]
        with self.assertRaises(ValueError):
            recursive_feature_predictions(model, history, [pd.Timestamp('2026-01-03')],
                {'lags': [1], 'rolling_windows': [], 'calendar_features': False})


class ForecastReplacementIntegrityTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name='Recursive test', code='recursive-test', workspace_type=WorkspaceType.RETAIL)
        self.config = ForecastModelConfig.objects.create(workspace=self.workspace, name='Test', target_type=TargetType.RETAIL_REVENUE)
        self.run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
            target_type=TargetType.RETAIL_REVENUE, artifact_path='unused.json', model_metrics={'rmse': 0},
            job_parameters={'provenance': {'feature_config': {'lags': [1], 'rolling_windows': [], 'calendar_features': False},
                                         'feature_columns': ['lag_1'], 'granularity': Granularity.DAILY}})
        self.old = ForecastResult.objects.create(workspace=self.workspace, forecast_run=self.run,
            target_type=self.run.target_type, forecast_date=datetime.date(2026, 1, 4), predicted_value=99)
        self.history = pd.DataFrame({'target': [1., 2., 3.]}, index=pd.date_range('2026-01-01', periods=3))

    def generate(self, model, horizon=2):
        with patch('apps.forecasting.prediction.load_model_artifact', return_value=model), \
             patch('apps.forecasting.prediction.get_historical_timeseries', return_value=self.history):
            return generate_future_forecast(self.run, horizon)

    def test_later_config_edit_does_not_change_trained_features_and_zero_rmse_is_zero(self):
        self.config.feature_config = {'lags': [99]}
        model = Mock()
        model.predict.return_value = [10.]
        results = self.generate(model)
        self.assertEqual(list(model.predict.call_args.args[0].columns), ['lag_1'])
        self.assertEqual(results[0].lower_bound, results[0].predicted_value)
        self.assertEqual(results[0].upper_bound, results[0].predicted_value)
        self.assertEqual(self.run.results.count(), 2)

    def test_missing_or_invalid_rmse_does_not_invent_interval(self):
        for metrics in ({}, {'rmse': -1}, {'rmse': 'invalid'}, {'rmse': float('nan')}):
            self.run.model_metrics = metrics
            model = Mock()
            model.predict.return_value = [10.]
            results = self.generate(model)
            self.assertIsNone(results[0].lower_bound)
            self.assertIsNone(results[0].upper_bound)

    def test_predict_error_preserves_last_good_results(self):
        model = Mock()
        model.predict.side_effect = [[10.], ValueError('provider failed')]
        with self.assertRaises(ValueError):
            self.generate(model)
        self.old.refresh_from_db()
        self.assertEqual(self.old.predicted_value, 99)
        self.assertEqual(self.run.results.count(), 1)

    def test_insert_failure_rolls_back_replacement(self):
        model = Mock()
        model.predict.return_value = [10.]
        with patch('apps.forecasting.prediction.ForecastResult.objects.bulk_create', side_effect=ValueError('write failed')):
            with self.assertRaises(ValueError):
                self.generate(model)
        self.old.refresh_from_db()
        self.assertEqual(self.run.results.count(), 1)

    def test_weekly_snapshot_keeps_weekly_cadence(self):
        self.run.job_parameters['provenance']['granularity'] = Granularity.WEEKLY
        self.history.index = pd.date_range('2026-01-05', periods=3, freq='W-MON')
        model = Mock()
        model.predict.return_value = [10.]
        results = self.generate(model)
        self.assertEqual([r.forecast_date for r in results], [datetime.date(2026, 1, 26), datetime.date(2026, 2, 2)])

    def test_invalid_horizon_preserves_existing_results(self):
        for horizon in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.generate(Mock(), horizon)
        self.assertTrue(self.run.results.filter(pk=self.old.pk).exists())
