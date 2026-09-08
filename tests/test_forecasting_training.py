"""
Tests for Model Training, Chronological Split, Evaluation Metrics, and Artifact Persistence.
"""

from decimal import Decimal
from pathlib import Path
import datetime
from django.test import TestCase
from django.utils import timezone
from django.conf import settings
import numpy as np
import pandas as pd

from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Order, OrderStatus, Customer
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    RunStatus,
    TargetType,
)
from apps.forecasting.training import chronological_split, train_forecast_model
from apps.forecasting.features import build_features
from apps.forecasting.evaluation import (
    compute_mae,
    compute_rmse,
    compute_mape,
    compute_r2,
    generate_naive_baseline_predictions,
)


class ForecastingTrainingTestCase(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Retail Training WS",
            code="retail-train-ws",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-TRAIN-01",
            name="Train Customer",
        )

        # Seed 60 days of orders with weekly pattern (higher on weekends)
        start_date = datetime.date(2026, 1, 1)
        for d in range(60):
            cur_date = start_date + datetime.timedelta(days=d)
            # Weekend has 300,000; Weekday has 100,000
            amt = Decimal("300000.00") if cur_date.weekday() >= 5 else Decimal("100000.00")

            Order.objects.create(
                workspace=self.workspace,
                order_number=f"ORD-TRAIN-{d:03d}",
                customer=self.customer,
                order_date=cur_date,
                order_timestamp=timezone.make_aware(datetime.datetime(cur_date.year, cur_date.month, cur_date.day, 12, 0)),
                status=OrderStatus.COMPLETED,
                total_amount=amt,
            )

    def test_chronological_split_strict_ordering(self):
        """Tests that chronological split never shuffles or places future dates in train set."""
        dates = pd.date_range("2026-01-01", periods=50, freq="D")
        df = pd.DataFrame({"target": np.arange(50, dtype=float)}, index=dates)
        feat_df = build_features(df, drop_na=True)

        X_train, X_test, y_train, y_test, split_idx = chronological_split(feat_df, test_size=0.20)

        # All training timestamps must strictly precede all test timestamps
        max_train_date = X_train.index.max()
        min_test_date = X_test.index.min()
        self.assertLess(max_train_date, min_test_date)

        # Row counts match split ratio
        self.assertEqual(len(X_train) + len(X_test), len(feat_df))
        self.assertEqual(len(y_train), len(X_train))
        self.assertEqual(len(y_test), len(X_test))

    def test_metrics_calculation_accuracy(self):
        """Tests calculation of pure numerical metrics: MAE, RMSE, MAPE, R2."""
        y_true = np.array([100.0, 200.0, 300.0, 400.0])
        y_pred = np.array([110.0, 190.0, 310.0, 390.0])  # Constant error of 10.0

        mae = compute_mae(y_true, y_pred)
        rmse = compute_rmse(y_true, y_pred)
        mape = compute_mape(y_true, y_pred)
        r2 = compute_r2(y_true, y_pred)

        self.assertEqual(mae, 10.0)
        self.assertEqual(rmse, 10.0)
        # MAPE: mean(10/100, 10/200, 10/300, 10/400) * 100 = mean(0.1, 0.05, 0.0333, 0.025) * 100 = 5.21%
        self.assertAlmostEqual(mape, 5.208, places=2)
        self.assertGreater(r2, 0.95)

    def test_naive_baseline_generation(self):
        """Tests naive persistence baseline generation with lag 7."""
        # 14 points: 7 values repeated twice
        y_full = np.array([1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7], dtype=float)
        # Test set is the second half: indices 7 to 13
        test_start_idx = 7
        baseline_preds = generate_naive_baseline_predictions(y_full, test_start_idx=test_start_idx, seasonality_lag=7)

        # Should match the first half exactly
        expected = np.array([1, 2, 3, 4, 5, 6, 7], dtype=float)
        np.testing.assert_array_equal(baseline_preds, expected)

    def test_train_forecast_model_execution_and_artifact_persistence(self):
        """Tests full training execution, metric recording, and artifact file creation."""
        run = train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            horizon_days=7,
        )

        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertGreater(run.dataset_row_count, 0)
        self.assertGreater(run.train_row_count, 0)
        self.assertGreater(run.test_row_count, 0)

        # Metrics recorded
        self.assertIn("mae", run.model_metrics)
        self.assertIn("rmse", run.model_metrics)
        self.assertIn("mape", run.model_metrics)
        self.assertIn("naive_mae", run.baseline_metrics)

        # Feature importances recorded
        self.assertIn("is_weekend", run.feature_importances)

        # Artifact exists on disk
        artifact_full_path = settings.BASE_DIR / run.artifact_path
        self.assertTrue(artifact_full_path.exists())

        # Future results populated
        self.assertEqual(run.results.count(), 7)
