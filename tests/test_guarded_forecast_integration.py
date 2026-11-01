"""Database integration for the guarded forecast lifecycle and truthful metadata."""

import datetime
import hashlib
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastResult,
    ForecastRun,
    Granularity,
    ModelType,
    RunStatus,
    TargetType,
)
from apps.forecasting.services import get_or_create_default_config
from apps.forecasting.training import train_forecast_model
from apps.retail.models import Customer, Order, OrderStatus
from apps.workspaces.models import Workspace, WorkspaceType


class GuardedForecastLifecycleTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Guarded integration retail",
            code="guarded-integration-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="GUARDED-INT-CUSTOMER",
            name="Guarded Integration Customer",
        )
        artifact_temp = tempfile.TemporaryDirectory(
            prefix="guarded-forecast-integration-",
            dir=Path(settings.BASE_DIR) / "ml_models" / "forecasting",
        )
        self.addCleanup(artifact_temp.cleanup)
        self.artifact_dir = Path(artifact_temp.name)
        override = override_settings(FORECASTING_ARTIFACTS_DIR=self.artifact_dir)
        override.enable()
        self.addCleanup(override.disable)

    def create_daily_orders(self, count):
        first = datetime.date(2025, 1, 1)
        for offset in range(count):
            current = first + datetime.timedelta(days=offset)
            amount = Decimal(str(1000 + (offset % 7) * 175 + (offset // 14) * 9))
            Order.objects.create(
                workspace=self.workspace,
                order_number=f"GINT-{offset:04d}",
                customer=self.customer,
                order_date=current,
                order_timestamp=timezone.make_aware(
                    datetime.datetime.combine(current, datetime.time(12, 0))
                ),
                status=OrderStatus.COMPLETED,
                total_amount=amount,
            )

    def create_config(self, version, *, active=True, strategy=None, granularity=Granularity.DAILY):
        training_config = {
            "n_estimators": 10,
            "max_depth": 2,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "test_size": 0.20,
        }
        if strategy:
            training_config["strategy"] = strategy
        return ForecastModelConfig.objects.create(
            workspace=self.workspace,
            name=f"Guarded config v{version}",
            target_type=TargetType.RETAIL_REVENUE,
            model_type=ModelType.XGBOOST_REGRESSOR,
            granularity=granularity,
            feature_config={},
            training_config=training_config,
            is_active=active,
            model_version=version,
        )

    def test_default_config_is_latest_active_and_disabled_configs_are_not_reactivated(self):
        old = self.create_config(1, active=False)
        latest = self.create_config(2, active=True)

        self.assertEqual(
            get_or_create_default_config(self.workspace, TargetType.RETAIL_REVENUE).pk,
            latest.pk,
        )

        latest.is_active = False
        latest.save(update_fields=["is_active"])
        with self.assertRaisesMessage(ValueError, "No active forecast configuration"):
            get_or_create_default_config(self.workspace, TargetType.RETAIL_REVENUE)
        old.refresh_from_db()
        latest.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertFalse(latest.is_active)

    def test_direct_training_resolves_latest_active_config_without_multiple_object_error(self):
        self.create_config(1, active=False)
        latest = self.create_config(2, active=True)
        empty = pd.DataFrame(columns=["target"], index=pd.DatetimeIndex([], name="date"))

        with patch("apps.forecasting.training.get_historical_timeseries", return_value=empty):
            with self.assertRaisesRegex(ValueError, "Insufficient historical data"):
                train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE)

        run = ForecastRun.objects.get(workspace=self.workspace)
        self.assertEqual(run.model_config_id, latest.pk)
        self.assertEqual(run.status, RunStatus.FAILED)

    def test_guarded_runs_without_stored_selection_do_not_claim_xgboost(self):
        from apps.forecasting.diagnostics import get_run_model_label

        guarded = self.create_config(1, strategy="guarded_direct_v1")
        for status in (RunStatus.PENDING, RunStatus.RUNNING):
            with self.subTest(status=status):
                run = ForecastRun.objects.create(
                    workspace=self.workspace,
                    model_config=guarded,
                    target_type=TargetType.RETAIL_REVENUE,
                    status=status,
                )
                self.assertEqual(get_run_model_label(run), "Đang chờ lựa chọn")

        failed = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=guarded,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.FAILED,
            error_message="Insufficient history",
        )
        self.assertEqual(get_run_model_label(failed), "Chưa xác định")

        completed = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=guarded,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.COMPLETED,
            job_parameters={"provenance": {
                "strategy": "guarded_direct_v1",
                "effective_model": "XGBOOST_DIRECT",
            }},
        )
        self.assertEqual(get_run_model_label(completed), "XGBoost Direct")

        legacy = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=self.create_config(2),
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.PENDING,
        )
        self.assertEqual(get_run_model_label(legacy), "XGBoost")

    def test_guarded_training_records_actual_model_baselines_and_snapshot_without_refetch(self):
        self.create_daily_orders(130)
        config = self.create_config(1, strategy="guarded_direct_v1")
        from apps.forecasting.selectors import get_historical_timeseries

        with patch(
            "apps.forecasting.training.get_historical_timeseries",
            wraps=get_historical_timeseries,
        ) as history_fetch, patch(
            "apps.forecasting.prediction.get_historical_timeseries",
            side_effect=AssertionError("training prediction must reuse its source snapshot"),
        ):
            run = train_forecast_model(
                workspace=self.workspace,
                target_type=TargetType.RETAIL_REVENUE,
                model_config=config,
                hyperparams={"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05},
                horizon_days=14,
            )

        run.refresh_from_db()
        self.assertEqual(history_fetch.call_count, 1)
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertTrue((Path(settings.BASE_DIR) / run.artifact_path).is_file())
        provenance = run.job_parameters["provenance"]
        self.assertEqual(provenance["strategy"], "guarded_direct_v1")
        self.assertIn(provenance["effective_model"], {"MA7", "XGBOOST_DIRECT"})
        self.assertEqual(provenance["evaluation"]["method"], "chronological_validation_selection_then_separate_rolling_holdout")
        self.assertIn("reason", provenance["selection"])
        self.assertEqual(provenance["selection"]["params"]["n_estimators"], 10)
        self.assertEqual(provenance["selection"]["params"]["max_depth"], 2)
        self.assertEqual(provenance["selection"]["params"]["learning_rate"], 0.05)
        self.assertEqual(provenance["selection"]["params"]["subsample"], 1.0)
        self.assertEqual(provenance["selection"]["params"]["colsample_bytree"], 1.0)
        self.assertNotIn("test_size", provenance["selection"]["params"])
        self.assertEqual(provenance["training_config"]["test_size"], 0.20)
        self.assertTrue(provenance["deployment_qualification"])
        self.assertNotIn("holdout_rows", provenance)
        self.assertIn("ma7", run.baseline_metrics)
        self.assertIn("seasonal_naive_7", run.baseline_metrics)
        self.assertEqual(run.baseline_metrics["moving_average_7_mae"], run.baseline_metrics["ma7"]["mae"])
        self.assertEqual(run.baseline_metrics["naive_mae"], run.baseline_metrics["seasonal_naive_7"]["mae"])
        self.assertEqual(set(provenance["source_sha256"]) & {"adaptive.py", "guarded.py", "artifacts.py", "prediction.py"},
                         {"adaptive.py", "guarded.py", "artifacts.py", "prediction.py"})
        self.assertEqual(run.results.count(), 14)
        self.assertTrue(all(result.lower_bound is None and result.upper_bound is None for result in run.results.all()))
        self.assertIn("body", run.job_parameters["artifact_snapshot"])

        artifact_path = Path(settings.BASE_DIR) / run.artifact_path
        self.assertTrue(artifact_path.exists())
        self.assertEqual(provenance["artifact_sha256"], hashlib.sha256(artifact_path.read_bytes()).hexdigest())

        from apps.forecasting.serializers import ForecastRunSerializer
        serialized = ForecastRunSerializer(run).data
        self.assertEqual(serialized["model_label"], "MA7" if provenance["effective_model"] == "MA7" else "XGBoost Direct")
        self.assertNotIn("body", serialized["job_parameters"]["artifact_snapshot"])
        self.assertIn("body", run.job_parameters["artifact_snapshot"])

        from apps.forecasting.services import get_forecast_chart_data
        chart = get_forecast_chart_data(self.workspace, TargetType.RETAIL_REVENUE, history_days=366)
        self.assertEqual(chart["model_label"], serialized["model_label"])
        self.assertEqual(chart["comparison_baseline_label"], "MA7")
        self.assertIn(serialized["model_label"], chart["quality"]["message"])

        from django.template.loader import render_to_string
        executive_report = render_to_string("dashboard/executive_report.html", {
            "forecast_runs": [{
                "target_name": "Retail Revenue",
                "workspace": self.workspace.name,
                "model_label": serialized["model_label"],
                "baseline_label": "MA7",
                "mae": run.model_metrics["mae"],
                "rmse": run.model_metrics["rmse"],
                "baseline_mae": run.baseline_metrics["moving_average_7_mae"],
                "improvement_pct": run.model_metrics["mae_improvement_pct"],
            }],
        })
        self.assertIn(serialized["model_label"], executive_report)
        self.assertIn("MA7 MAE", executive_report)
        self.assertNotIn("XGBoost MAE", executive_report)

        from apps.forecasting.academic_reporting import render_report
        report = render_report([{
            "id": run.pk,
            "workspace": self.workspace.code,
            "config": config.pk,
            "target": run.target_type,
            "status": run.status,
            "train": run.train_row_count,
            "test": run.test_row_count,
            "metrics": run.model_metrics,
            "baseline": run.baseline_metrics,
            "start": run.dataset_period_start,
            "end": run.dataset_period_end,
            "parameters": run.job_parameters,
            "model_label": serialized["model_label"],
        }], {"recommendations": 0, "approvals": 0, "statuses": {}}, "fixed-time")
        self.assertIn("Mô hình thực tế", report)
        self.assertIn(serialized["model_label"], report)
        self.assertIn("guarded_direct_v1", report)
        self.assertIn("Đánh giá guarded dùng phương pháp", report)
        self.assertNotIn("Backtest hiện tại là one-step observed-history", report)

    def test_guarded_prediction_rejects_a_changed_history_snapshot_without_replacing_results(self):
        self.create_daily_orders(130)
        config = self.create_config(1, strategy="guarded_direct_v1")
        run = train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            model_config=config,
            hyperparams={"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05},
            horizon_days=14,
        )
        before = list(run.results.order_by("forecast_date").values_list("forecast_date", "predicted_value"))
        from apps.forecasting.selectors import get_historical_timeseries
        history = get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE)
        changed = history.copy()
        changed.iloc[0, 0] += 1

        from apps.forecasting.prediction import generate_future_forecast
        with self.assertRaisesMessage(ValueError, "dataset fingerprint"):
            generate_future_forecast(run, horizon_days=14, history_snapshot=changed)

        after = list(run.results.order_by("forecast_date").values_list("forecast_date", "predicted_value"))
        self.assertEqual(after, before)

    def test_weekly_long_horizon_falls_back_to_ma7_and_report_never_calls_it_xgboost(self):
        from django.template.loader import render_to_string
        from apps.forecasting.diagnostics import get_run_model_label

        config = self.create_config(1, strategy="guarded_direct_v1", granularity=Granularity.WEEKLY)
        index = pd.date_range("2024-01-01", periods=55, freq="7D", name="date")
        history = pd.DataFrame({"target": [float(100 + (i % 7)) for i in range(55)]}, index=index)
        history.attrs.update({
            "source_observation_count": 55,
            "missing_period_count": 0,
            "missing_period_policy": "zero_fill_daily_gap",
            "source_frequency": Granularity.WEEKLY,
            "observed_period_dates": [day.date().isoformat() for day in index],
        })
        with patch("apps.forecasting.training.get_historical_timeseries", return_value=history):
            run = train_forecast_model(
                workspace=self.workspace,
                target_type=TargetType.RETAIL_REVENUE,
                model_config=config,
                horizon_days=20,
            )

        run.refresh_from_db()
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.job_parameters["provenance"]["effective_model"], "MA7")
        self.assertEqual(get_run_model_label(run), "MA7")
        self.assertEqual(run.results.count(), 20)
        self.assertTrue(all(result.lower_bound is None and result.upper_bound is None for result in run.results.all()))
        self.assertEqual(run.results.first().forecast_date, index[-1].date() + datetime.timedelta(days=7))

        from apps.forecasting.services import get_forecast_chart_data
        chart = get_forecast_chart_data(
            self.workspace,
            TargetType.RETAIL_REVENUE,
            history_days=3660,
            horizon_days=90,
        )
        self.assertEqual(chart["model_label"], "MA7")
        self.assertIn("MA7", chart["quality"]["message"])
        self.assertEqual(chart["comparison_baseline_label"], "MA7")
        self.assertFalse(chart["show_prediction_intervals"])
        run.display_model_label = "MA7"
        run.display_baseline_label = "MA7"
        run.display_baseline_mae = run.baseline_metrics["moving_average_7_mae"]
        dashboard_html = render_to_string("forecasting/index.html", {
            "active_workspace": self.workspace,
            "available_targets": [{"code": TargetType.RETAIL_REVENUE, "label": "Revenue"}],
            "selected_target": TargetType.RETAIL_REVENUE,
            "chart_data": chart,
            "runs": [run],
            "configs": [],
            "can_manage": False,
            "products": [],
            "categories": [],
            "branches": [],
            "selected_dimensions": {},
        })
        self.assertIn("MA7", dashboard_html)
        self.assertIn('Dự báo ${modelLabel}', dashboard_html)
        self.assertIn('"model_label": "MA7"', dashboard_html)
        self.assertIn('"show_prediction_intervals": false', dashboard_html)
        self.assertIn("MA7: ", dashboard_html)

        report = render_to_string("dashboard/executive_report.html", {
            "forecast_runs": [{
                "target_name": "Retail Revenue",
                "workspace": self.workspace.name,
                "model_label": get_run_model_label(run),
                "baseline_label": "MA7",
                "mae": run.model_metrics["mae"],
                "rmse": run.model_metrics["rmse"],
                "baseline_mae": run.baseline_metrics["moving_average_7_mae"],
                "improvement_pct": run.model_metrics["mae_improvement_pct"],
            }],
        })
        self.assertIn("MA7", report)
        self.assertNotIn("XGBoost MAE", report)
        self.assertNotIn("XGBoost vs Baseline", report)
        self.assertNotIn("cảnh báo của mô hình XGBoost", report)
        self.assertIn("số liệu tồn kho và nhu cầu đã ghi nhận trong kỳ", report)

        from apps.knowledge.services import generate_grounded_answer
        forecast_point = run.results.first()
        answer, _ = generate_grounded_answer(
            self.workspace,
            None,
            "Dự báo tiếp theo là gì?",
            [],
            tools_data=[{
                "tool": "get_forecast",
                "target_type": run.target_type,
                "model_label": get_run_model_label(run),
                "forecast": [{
                    "date": forecast_point.forecast_date.isoformat(),
                    "predicted": str(forecast_point.predicted_value),
                    "lower": None,
                    "upper": None,
                }],
                "snapshot": {"message": "Snapshot lịch sử."},
                "quality": {"message": "Đường cơ sở tốt hơn hoặc bằng MA7.", "r2_warning": ""},
            }],
        )
        self.assertIn("MA7", answer)
        self.assertIn("không cung cấp cận dự báo", answer)
        self.assertNotIn("XGBoost", answer)

    def test_guarded_artifact_sha_rejection_preserves_results_and_missing_file_uses_inline_snapshot(self):
        self.create_daily_orders(130)
        config = self.create_config(1, strategy="guarded_direct_v1")
        run = train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            model_config=config,
            hyperparams={"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05},
            horizon_days=14,
        )
        from apps.forecasting.selectors import get_historical_timeseries
        from apps.forecasting.prediction import generate_future_forecast

        history = get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE)
        path = Path(settings.BASE_DIR) / run.artifact_path
        original = path.read_bytes()
        old_results = list(run.results.order_by("forecast_date").values_list(
            "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        ))
        path.write_bytes(b"tampered artifact")
        with self.assertRaisesMessage(ValueError, "SHA-256"):
            generate_future_forecast(run, horizon_days=14, history_snapshot=history)
        self.assertEqual(list(run.results.order_by("forecast_date").values_list(
            "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        )), old_results)

        path.write_bytes(original)
        path.unlink()
        regenerated = generate_future_forecast(run, horizon_days=14, history_snapshot=history)
        self.assertEqual(len(regenerated), 14)
        self.assertEqual(run.results.count(), 14)

    def test_legacy_chart_keeps_prediction_interval_datasets(self):
        from apps.forecasting.services import get_forecast_chart_data

        self.create_daily_orders(30)
        config = self.create_config(1)
        last_history_date = datetime.date(2025, 1, 30)
        run = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=config,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.COMPLETED,
            dataset_period_end=last_history_date,
            baseline_metrics={"naive_mae": 10.0, "naive_rmse": 12.0},
        )
        ForecastResult.objects.create(
            workspace=self.workspace,
            forecast_run=run,
            target_type=TargetType.RETAIL_REVENUE,
            forecast_date=last_history_date + datetime.timedelta(days=1),
            predicted_value=Decimal("1000.00"),
            lower_bound=Decimal("900.00"),
            upper_bound=Decimal("1100.00"),
        )

        chart = get_forecast_chart_data(
            self.workspace,
            TargetType.RETAIL_REVENUE,
            history_days=3660,
            horizon_days=7,
        )
        self.assertTrue(chart["show_prediction_intervals"])

    @override_settings(FORECAST_ASYNC_ENABLED=True)
    def test_guarded_worker_losing_final_fence_removes_only_new_artifact(self):
        import apps.forecasting.training as training
        from apps.forecasting.queue import claim_job
        from apps.forecasting.services import execute_training_job

        config = self.create_config(1, strategy="guarded_direct_v1", granularity=Granularity.WEEKLY)
        index = pd.date_range("2024-01-01", periods=55, freq="7D", name="date")
        history = pd.DataFrame({"target": [float(100 + (i % 7)) for i in range(55)]}, index=index)
        history.attrs["observed_period_dates"] = [day.date().isoformat() for day in index]
        pending = execute_training_job(self.workspace, TargetType.RETAIL_REVENUE, is_async=True)
        old_artifact = self.artifact_dir / f"run_{pending.pk}_{uuid.uuid4().hex}.json"
        old_artifact.write_bytes(b"previous artifact")
        ForecastRun.objects.filter(pk=pending.pk).update(
            artifact_path=old_artifact.relative_to(settings.BASE_DIR).as_posix(),
        )
        claimed = claim_job()
        finish_with_fence = training._finish_training_run

        def cancel_after_artifact_save(run, **kwargs):
            ForecastRun.objects.filter(pk=run.pk).update(
                status=RunStatus.CANCELLED,
                cancel_requested=True,
                lease_token=None,
                lease_expires_at=None,
                error_message="CANCELLED_AFTER_ARTIFACT_SAVE",
            )
            return finish_with_fence(run, **kwargs)

        with patch("apps.forecasting.training.get_historical_timeseries", return_value=history), patch(
            "apps.forecasting.training._finish_training_run", side_effect=cancel_after_artifact_save,
        ):
            with self.assertRaisesMessage(ValueError, "FORECAST_LEASE_LOST"):
                train_forecast_model(
                    self.workspace,
                    TargetType.RETAIL_REVENUE,
                    model_config=config,
                    run=claimed,
                    lease_token=claimed.lease_token,
                )

        claimed.refresh_from_db()
        self.assertEqual(claimed.status, RunStatus.CANCELLED)
        self.assertEqual(claimed.error_message, "CANCELLED_AFTER_ARTIFACT_SAVE")
        self.assertEqual(sorted(self.artifact_dir.glob(f"run_{claimed.pk}_*.json")), [old_artifact])
        self.assertEqual(claimed.results.count(), 0)

    def test_guarded_artifact_cleanup_rejects_path_outside_trusted_root(self):
        from apps.forecasting.training import _remove_new_guarded_artifact

        config = self.create_config(1, strategy="guarded_direct_v1")
        run = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=config,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.RUNNING,
        )
        outside_dir = tempfile.TemporaryDirectory(
            prefix="guarded-cleanup-sentinel-",
            dir=self.artifact_dir.parent,
        )
        self.addCleanup(outside_dir.cleanup)
        sentinel = Path(outside_dir.name) / f"run_{run.pk}_{uuid.uuid4().hex}.json"
        sentinel.write_bytes(b"leave outside artifact root untouched")
        generated_path = sentinel.relative_to(settings.BASE_DIR).as_posix()
        generated_sha = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        run.artifact_path = generated_path

        _remove_new_guarded_artifact(
            run,
            generated_path,
            generated_sha,
            base_dir=settings.BASE_DIR,
            artifacts_dir=self.artifact_dir,
        )
        self.assertTrue(sentinel.is_file())

    def test_guarded_artifact_cleanup_rejects_symlink_before_resolving_target(self):
        from apps.forecasting.training import _remove_new_guarded_artifact

        config = self.create_config(1, strategy="guarded_direct_v1")
        run = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=config,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.RUNNING,
        )
        existing_artifact = self.artifact_dir / f"run_{run.pk}_{uuid.uuid4().hex}.json"
        existing_artifact.write_bytes(b"existing artifact must survive")
        alias = self.artifact_dir / f"run_{run.pk}_{uuid.uuid4().hex}.json"
        try:
            alias.symlink_to(existing_artifact)
            symlink_available = True
        except (OSError, NotImplementedError):
            alias.write_bytes(b"symlink stand-in")
            symlink_available = False
        generated_path = alias.relative_to(settings.BASE_DIR).as_posix()
        generated_sha = hashlib.sha256(existing_artifact.read_bytes()).hexdigest()
        run.artifact_path = generated_path

        def resolve_to_existing_artifact(*args, **kwargs):
            return existing_artifact.resolve()

        resolver_patch = patch(
            "apps.forecasting.artifacts._validated_artifact_path",
            side_effect=resolve_to_existing_artifact,
        )
        if symlink_available:
            with resolver_patch:
                _remove_new_guarded_artifact(
                    run,
                    generated_path,
                    generated_sha,
                    base_dir=settings.BASE_DIR,
                    artifacts_dir=self.artifact_dir,
                )
        else:
            original_is_symlink = type(alias).is_symlink

            def report_raw_path_as_symlink(path):
                return True if path == alias else original_is_symlink(path)

            with patch.object(type(alias), "is_symlink", new=report_raw_path_as_symlink), resolver_patch:
                _remove_new_guarded_artifact(
                    run,
                    generated_path,
                    generated_sha,
                    base_dir=settings.BASE_DIR,
                    artifacts_dir=self.artifact_dir,
                )

        self.assertTrue(existing_artifact.is_file())

    @override_settings(FORECAST_ASYNC_ENABLED=True)
    def test_guarded_worker_losing_lease_cannot_publish_metadata_or_results(self):
        from apps.forecasting.queue import claim_job
        from apps.forecasting.services import execute_training_job

        config = self.create_config(1, strategy="guarded_direct_v1", granularity=Granularity.WEEKLY)
        index = pd.date_range("2024-01-01", periods=55, freq="7D", name="date")
        history = pd.DataFrame({"target": [float(100 + (i % 7)) for i in range(55)]}, index=index)
        history.attrs["observed_period_dates"] = [day.date().isoformat() for day in index]
        pending = execute_training_job(
            self.workspace,
            TargetType.RETAIL_REVENUE,
            is_async=True,
        )
        claimed = claim_job()
        self.assertEqual(claimed.pk, pending.pk)

        def expire_after_read(*args, **kwargs):
            ForecastRun.objects.filter(pk=claimed.pk).update(
                lease_expires_at=timezone.now() - datetime.timedelta(seconds=1),
                job_parameters={"dimensions": {}, "new_attempt_marker": True},
            )
            return history

        with patch("apps.forecasting.training.get_historical_timeseries", side_effect=expire_after_read):
            with self.assertRaisesMessage(ValueError, "FORECAST_LEASE_LOST"):
                train_forecast_model(
                    self.workspace,
                    TargetType.RETAIL_REVENUE,
                    model_config=config,
                    run=claimed,
                    lease_token=claimed.lease_token,
                )

        claimed.refresh_from_db()
        self.assertEqual(claimed.status, RunStatus.PENDING)
        self.assertTrue(claimed.job_parameters["new_attempt_marker"])
        self.assertNotIn("provenance", claimed.job_parameters)
        self.assertEqual(claimed.results.count(), 0)

    def test_holdout_worse_than_ma7_is_failed_not_served_and_keeps_prior_results(self):
        self.create_daily_orders(130)
        legacy_config = self.create_config(1)
        guard_config = self.create_config(2, strategy="guarded_direct_v1")
        from apps.forecasting.selectors import get_historical_timeseries
        from apps.forecasting.adaptive import booster_to_json_dict, columns_for, fit_direct

        artifact_history = get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE).iloc[:80]
        artifact_params = {"n_estimators": 1, "max_depth": 1, "learning_rate": 0.05}
        artifact_model = fit_direct(artifact_history, mode="none", params=artifact_params)
        prior_run = ForecastRun.objects.create(
            workspace=self.workspace,
            model_config=legacy_config,
            target_type=TargetType.RETAIL_REVENUE,
            status=RunStatus.COMPLETED,
            job_parameters={"provenance": {"legacy_marker": "prior"}},
        )
        prior_result = ForecastResult.objects.create(
            workspace=self.workspace,
            forecast_run=prior_run,
            target_type=TargetType.RETAIL_REVENUE,
            forecast_date=datetime.date(2026, 12, 20),
            predicted_value=Decimal("123.45"),
        )
        guarded_result = {
            "artifact": {
                "format": "alphatech_guarded_forecast_v1",
                "effective_model": "XGBOOST_DIRECT",
                "calendar_mode": "none",
                "columns": columns_for("none"),
                "params": artifact_params,
                "booster": booster_to_json_dict(artifact_model),
            },
            "selection": {"effective_model": "XGBOOST_DIRECT", "reason": "validation_gates_passed", "params": {}},
            "model_metrics": {"mae": 11.0, "rmse": 12.0, "mape": 10.0, "r2": -0.1, "bias": 1.0, "count": 14},
            "baseline_metrics": {
                "ma7": {"mae": 10.0, "rmse": 11.0, "mape": 9.0, "r2": 0.0, "bias": 0.0, "count": 14},
                "seasonal_naive_7": {"mae": 15.0, "rmse": 16.0, "mape": 12.0, "r2": -0.2, "bias": 1.0, "count": 14},
            },
            "feature_importances": {},
            "evaluation": {
                "method": "chronological_validation_selection_then_separate_rolling_holdout",
                "partitions": {
                    "initial_fit": ["2025-01-01", "2025-03-17"],
                    "validation": ["2025-03-18", "2025-04-14"],
                    "holdout": ["2025-04-15", "2025-05-10"],
                },
                "counts": {"initial_fit": 76, "validation": 28, "holdout": 26, "history": 130},
                "intervals_calibrated": False,
            },
            "holdout_rows": [],
        }

        with patch("apps.forecasting.guarded.fit_guarded", return_value=guarded_result):
            with self.assertRaisesMessage(ValueError, "selected model holdout MAE exceeded matched MA7"):
                train_forecast_model(
                    workspace=self.workspace,
                    target_type=TargetType.RETAIL_REVENUE,
                    model_config=guard_config,
                    hyperparams={"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05},
                    horizon_days=14,
                )

        rejected = ForecastRun.objects.filter(model_config=guard_config).get()
        rejected_provenance = rejected.job_parameters["provenance"]
        self.assertEqual(rejected.status, RunStatus.FAILED)
        self.assertEqual(rejected_provenance["effective_model"], "XGBOOST_DIRECT")
        self.assertEqual(rejected_provenance["selection"]["effective_model"], "XGBOOST_DIRECT")
        self.assertFalse(rejected_provenance["deployment_qualification"])
        self.assertEqual(rejected_provenance["deployment_qualification_reason"],
                         "selected_model_holdout_mae_exceeded_matched_ma7")
        self.assertEqual(rejected.model_metrics["mae"], 11.0)
        self.assertEqual(rejected.results.count(), 0)
        prior_result.refresh_from_db()
        self.assertEqual(prior_result.predicted_value, Decimal("123.45"))
        from apps.forecasting.prediction import generate_future_forecast
        with self.assertRaisesMessage(ValueError, "did not qualify for deployment"):
            generate_future_forecast(rejected, horizon_days=14)

    def test_deployment_holdout_guard_allows_ties_and_rejects_any_strict_float_loss(self):
        from apps.forecasting.training import _guarded_deployment_qualification

        def result(selected_mae, baseline_mae):
            return {
                "artifact": {"effective_model": "XGBOOST_DIRECT"},
                "model_metrics": {"mae": selected_mae},
                "baseline_metrics": {"ma7": {"mae": baseline_mae}},
            }

        self.assertTrue(_guarded_deployment_qualification(result(10.0, 10.0))["qualified"])
        rejected = _guarded_deployment_qualification(result(10.0000000001, 10.0))
        self.assertFalse(rejected["qualified"])
        self.assertEqual(rejected["reason"], "selected_model_holdout_mae_exceeded_matched_ma7")
