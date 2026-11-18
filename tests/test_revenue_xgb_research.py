from unittest.mock import patch
import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from apps.forecasting.revenue_research import evaluate_revenue_xgboost


class RevenueResearchTests(SimpleTestCase):
    def test_scores_only_observed_holdout_and_returns_future_xgboost(self):
        index = pd.date_range('2025-01-01', periods=130)
        history = pd.DataFrame({'target': np.arange(130, dtype=float)}, index=index)
        observed = list(index[:100]) + [index[105], index[129]]
        history.attrs['observed_period_dates'] = [day.date().isoformat() for day in observed]
        with patch('apps.forecasting.revenue_research.get_historical_timeseries', return_value=history):
            result = evaluate_revenue_xgboost(object())
        self.assertEqual(result['holdout_observed'], 2)
        self.assertEqual(result['metrics']['xgboost']['count'], 2)
        self.assertEqual(result['metrics']['ma7']['count'], 2)
        self.assertEqual(len(result['forecast']), 14)
        self.assertEqual(result['data_mode'], 'EXPERIMENTAL_NOT_OPERATIONAL')
        self.assertEqual(result['imputed'], 28)

    def test_no_observed_holdout_is_rejected(self):
        index = pd.date_range('2025-01-01', periods=130)
        history = pd.DataFrame({'target': np.arange(130, dtype=float)}, index=index)
        history.attrs['observed_period_dates'] = [day.date().isoformat() for day in index[:100]]
        with patch('apps.forecasting.revenue_research.get_historical_timeseries', return_value=history):
            with self.assertRaisesRegex(ValueError, 'Không có quan sát'):
                evaluate_revenue_xgboost(object())
