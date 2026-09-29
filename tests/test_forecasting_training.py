"""
Tests for Model Training, Chronological Split, Evaluation Metrics, and Artifact Persistence.
"""

from decimal import Decimal
from pathlib import Path
import datetime
import hashlib
from unittest.mock import patch
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
    compute_interval_coverage,
    generate_naive_baseline_predictions,
    generate_moving_average_baseline_predictions,
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

    def test_worker_losing_lease_cannot_overwrite_new_attempt_metadata(self):
        from apps.forecasting.services import execute_training_job
        from apps.forecasting.queue import claim_job
        from apps.forecasting.selectors import get_historical_timeseries
        pending = execute_training_job(self.workspace, TargetType.RETAIL_REVENUE, is_async=True)
        claimed = claim_job()
        self.assertEqual(claimed.pk, pending.pk)

        def expire_after_read(*args, **kwargs):
            data = get_historical_timeseries(*args, **kwargs)
            ForecastRun.objects.filter(pk=claimed.pk).update(
                lease_expires_at=timezone.now() - datetime.timedelta(seconds=1),
                job_parameters={"dimensions": {}, "new_attempt_marker": True},
            )
            return data

        with patch("apps.forecasting.training.get_historical_timeseries", side_effect=expire_after_read):
            with self.assertRaisesMessage(ValueError, "FORECAST_LEASE_LOST"):
                train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE,
                                     run=claimed, lease_token=claimed.lease_token)
        claimed.refresh_from_db()
        self.assertTrue(claimed.job_parameters["new_attempt_marker"])
        self.assertNotIn("provenance", claimed.job_parameters)
        self.assertEqual(claimed.results.count(), 0)

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
        self.assertEqual(len(baseline_preds), len(y_full) - test_start_idx)

    def test_moving_average_baseline_uses_only_prior_observations(self):
        y_full = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90], dtype=float)
        predictions = generate_moving_average_baseline_predictions(
            y_full, test_start_idx=7, window=3
        )
        # idx 7: mean(50, 60, 70); idx 8: mean(60, 70, 80).
        np.testing.assert_allclose(predictions, np.array([60.0, 70.0]))

    def test_moving_average_baseline_rejects_invalid_window(self):
        with self.assertRaises(ValueError):
            generate_moving_average_baseline_predictions(np.array([1.0]), 1, window=0)

    def test_mape_excludes_zero_actual_days_without_fabricating_accuracy(self):
        y_true = np.array([0.0, 100.0, 0.0, 200.0])
        y_pred = np.array([50.0, 110.0, 40.0, 180.0])
        # Only non-zero actual observations contribute: (10/100 + 20/200) / 2.
        self.assertAlmostEqual(compute_mape(y_true, y_pred), 10.0, places=6)

    def test_interval_coverage_is_measured_without_claiming_calibration(self):
        y_true = np.array([90.0, 100.0, 118.0, 160.0])
        y_pred = np.array([100.0, 100.0, 100.0, 100.0])
        # With scale=10 and z=1.96, the first three observations are covered.
        self.assertAlmostEqual(compute_interval_coverage(y_true, y_pred, 10.0), 0.75)
        self.assertIsNone(compute_interval_coverage(np.array([]), np.array([]), 10.0))

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

        provenance = run.job_parameters["provenance"]
        self.assertEqual(provenance["workspace_code"], self.workspace.code)
        self.assertEqual(provenance["target_type"], TargetType.RETAIL_REVENUE)
        self.assertEqual(provenance["horizon_days"], 7)
        self.assertEqual(len(provenance["dataset"]["fingerprint_sha256"]), 64)
        self.assertGreaterEqual(provenance["dataset"]["source_observation_count"], 1)
        self.assertIn("missing_period_policy", provenance["dataset"])
        self.assertEqual(provenance["split"]["method"], "chronological")
        self.assertEqual(provenance["split"]["train_rows"], run.train_row_count)
        self.assertEqual(provenance["split"]["test_rows"], run.test_row_count)
        self.assertIn("python", provenance["runtime"])
        self.assertIn("xgboost", provenance["runtime"])

        # Metrics recorded
        self.assertIn("mae", run.model_metrics)
        self.assertIn("rmse", run.model_metrics)
        self.assertIn("mape", run.model_metrics)
        self.assertIn("interval_coverage", run.model_metrics)
        self.assertEqual(run.model_metrics["interval_nominal_coverage"], 0.95)
        self.assertEqual(run.model_metrics["interval_evaluation"], "one_step_holdout_diagnostic_using_holdout_rmse")
        self.assertIn("naive_mae", run.baseline_metrics)
        self.assertIn("moving_average_7_mae", run.baseline_metrics)
        self.assertIn("moving_average_7_rmse", run.baseline_metrics)

        # Feature importances recorded
        self.assertIn("is_weekend", run.feature_importances)

        # Artifact exists on disk
        artifact_full_path = settings.BASE_DIR / run.artifact_path
        self.assertTrue(artifact_full_path.exists())
        run.refresh_from_db()
        provenance = run.job_parameters["provenance"]
        self.assertEqual(provenance["artifact_sha256"], hashlib.sha256(artifact_full_path.read_bytes()).hexdigest())
        self.assertEqual(provenance["training_config"]["random_state"], 42)
        self.assertEqual(provenance["dataset"]["unit"], "VND")
        self.assertLess(provenance["split"]["train_end"], provenance["split"]["test_start"])
        self.assertEqual(provenance["split"]["validation"], "no_separate_validation_partition")
        self.assertIn("lag_14", provenance["feature_columns"])
        self.assertEqual(set(provenance["source_sha256"]),
                         {"training.py", "selectors.py", "features.py", "evaluation.py"})
        for name, fingerprint in provenance["source_sha256"].items():
            self.assertEqual(fingerprint, hashlib.sha256(
                (settings.BASE_DIR / "apps/forecasting" / name).read_bytes()).hexdigest())
        from apps.forecasting.academic_reporting import render_report
        report = render_report([dict(id=run.pk, workspace=self.workspace.code,
            config=run.model_config_id, target=run.target_type, status=run.status,
            train=run.train_row_count, test=run.test_row_count, metrics=run.model_metrics,
            baseline=run.baseline_metrics, start=provenance["dataset"]["period_start"],
            end=provenance["dataset"]["period_end"], parameters=run.job_parameters)],
            dict(recommendations=0, approvals=0, statuses={}), timezone.now().isoformat())
        for field in ("train_start", "train_end", "test_start", "test_end"):
            self.assertIn(provenance["split"][field], report)
        self.assertIn(provenance["artifact_sha256"], report)
        self.assertIn(provenance["dataset"]["fingerprint_sha256"], report)
        if getattr(settings, "EVIDENCE_REPORT_DIR", None):
            settings.EVIDENCE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
            (settings.EVIDENCE_REPORT_DIR / "forecast_run_provenance.md").write_text(report, encoding="utf-8")

        # Future results populated
        self.assertEqual(run.results.count(), 7)
