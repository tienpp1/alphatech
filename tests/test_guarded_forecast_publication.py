"""Append-only publication command tests against canonical TEST fixtures."""

import datetime
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.audit.models import ActorType, AuditLog
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastResult,
    ForecastRun,
    Granularity,
    ModelType,
    RunStatus,
    TargetType,
)
from apps.retail.models import Category, Customer, Order, OrderItem, OrderStatus, Product
from apps.service_ops.models import Service, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceType


class GuardedForecastPublicationTests(TestCase):
    def setUp(self):
        self.retail = Workspace.objects.create(
            name="Publication Retail",
            code="publication-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service = Workspace.objects.create(
            name="Publication Service",
            code="publication-service",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.make_retail_history(self.retail, 55)
        self.make_service_history(self.service, 55)
        artifact_temp = tempfile.TemporaryDirectory(
            prefix="guarded-forecast-publication-",
            dir=Path(settings.BASE_DIR) / "ml_models" / "forecasting",
        )
        self.addCleanup(artifact_temp.cleanup)
        override = override_settings(FORECASTING_ARTIFACTS_DIR=Path(artifact_temp.name))
        override.enable()
        self.addCleanup(override.disable)

    def make_retail_history(self, workspace, count):
        customer = Customer.objects.create(
            workspace=workspace,
            code=f"PUB-CUST-{workspace.code}",
            name="Publication Customer",
        )
        category = Category.objects.create(
            workspace=workspace,
            name="Publication fixture category",
            code=f"PUB-CAT-{workspace.code}",
        )
        product = Product.objects.create(
            workspace=workspace,
            category=category,
            sku=f"PUB-SKU-{workspace.code}",
            name="Publication fixture product",
            unit_price=Decimal("1000.00"),
            cost_price=Decimal("500.00"),
        )
        start = timezone.localdate() - datetime.timedelta(days=count - 1)
        for offset in range(count):
            day = start + datetime.timedelta(days=offset)
            order = Order.objects.create(
                workspace=workspace,
                order_number=f"PUB-{workspace.code}-{offset:04d}",
                customer=customer,
                order_date=day,
                order_timestamp=timezone.make_aware(
                    datetime.datetime.combine(day, datetime.time(12, 0))
                ),
                status=OrderStatus.COMPLETED,
                total_amount=Decimal(str(1000 + (offset % 7) * 100)),
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1 + (offset % 3),
                unit_price=Decimal("1000.00"),
            )

    def make_service_history(self, workspace, count):
        customer = Customer.objects.create(
            workspace=workspace,
            code=f"PUB-SVC-CUST-{workspace.code}",
            name="Publication Service Customer",
        )
        service = Service.objects.create(
            workspace=workspace,
            code="PUB-SERVICE",
            name="Publication Fixture Service",
        )
        start = timezone.localdate() - datetime.timedelta(days=count - 1)
        requests = []
        for offset in range(count):
            day = start + datetime.timedelta(days=offset)
            requests.append(ServiceRequest.objects.create(
                workspace=workspace,
                customer=customer,
                service=service,
                request_number=f"PUB-REQ-{offset:04d}",
                title="Publication fixture request",
                description="Canonical TEST request fixture.",
            ))
            ServiceRequest.objects.filter(pk=requests[-1].pk).update(
                created_at=timezone.make_aware(
                    datetime.datetime.combine(day, datetime.time(9, 0))
                )
            )

    def create_legacy_config(self, workspace, target, *, version=1, active=True):
        return ForecastModelConfig.objects.create(
            workspace=workspace,
            name=f"Existing {target} config",
            target_type=target,
            model_type=ModelType.XGBOOST_REGRESSOR,
            granularity=Granularity.DAILY,
            feature_config={"calendar_features": True},
            training_config={
                "n_estimators": 10,
                "max_depth": 2,
                "learning_rate": 0.05,
                "test_size": 0.20,
            },
            is_active=active,
            model_version=version,
        )

    def create_old_result(self, workspace, config, target):
        run = ForecastRun.objects.create(
            workspace=workspace,
            model_config=config,
            target_type=target,
            status=RunStatus.COMPLETED,
            dataset_row_count=12,
            train_row_count=9,
            test_row_count=3,
            model_metrics={"mae": 17.0, "r2": -1.0},
            baseline_metrics={"naive_mae": 10.0},
            job_parameters={"provenance": {"legacy_marker": "unchanged"}},
        )
        result = ForecastResult.objects.create(
            workspace=workspace,
            forecast_run=run,
            target_type=target,
            forecast_date=timezone.localdate() + datetime.timedelta(days=30),
            predicted_value=Decimal("123.45"),
            lower_bound=Decimal("100.00"),
            upper_bound=Decimal("150.00"),
        )
        return run, result

    def publish(self, *, release_id, workspaces, apply=False, all_targets=False):
        args = ["--release-id", release_id]
        for workspace_code in workspaces:
            args.extend(["--workspace", workspace_code])
        if apply:
            args.append("--apply")
        if all_targets:
            args.append("--all-targets")
        output = StringIO()
        call_command("publish_guarded_forecasts", *args, stdout=output)
        return output.getvalue()

    def test_default_command_is_a_read_only_canonical_data_plan(self):
        before = {
            "configs": ForecastModelConfig.objects.count(),
            "runs": ForecastRun.objects.count(),
            "results": ForecastResult.objects.count(),
            "audit": AuditLog.objects.count(),
            "orders": Order.objects.count(),
            "requests": ServiceRequest.objects.count(),
        }
        with patch(
            "apps.forecasting.guarded.fit_guarded",
            side_effect=AssertionError("plan mode must not fit a model"),
        ):
            self.publish(
                release_id="release-plan-only",
                workspaces=[self.retail.code, self.service.code],
            )

        after = {
            "configs": ForecastModelConfig.objects.count(),
            "runs": ForecastRun.objects.count(),
            "results": ForecastResult.objects.count(),
            "audit": AuditLog.objects.count(),
            "orders": Order.objects.count(),
            "requests": ServiceRequest.objects.count(),
        }
        self.assertEqual(after, before)

    def test_apply_appends_guarded_runs_and_replay_is_idempotent_without_rewriting_history(self):
        retail_config = self.create_legacy_config(self.retail, TargetType.RETAIL_REVENUE)
        service_config = self.create_legacy_config(self.service, TargetType.SERVICE_TICKET_VOLUME)
        old_retail_run, old_retail_result = self.create_old_result(
            self.retail, retail_config, TargetType.RETAIL_REVENUE
        )
        old_service_run, old_service_result = self.create_old_result(
            self.service, service_config, TargetType.SERVICE_TICKET_VOLUME
        )
        old_result_state = list(ForecastResult.objects.order_by("pk").values_list(
            "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        ))

        self.publish(
            release_id="release-append-only-1",
            workspaces=[self.retail.code, self.service.code],
            apply=True,
        )

        new_runs = list(ForecastRun.objects.filter(
            job_parameters__release_id="release-append-only-1"
        ).order_by("workspace__code"))
        self.assertEqual(len(new_runs), 2)
        self.assertEqual({run.workspace_id for run in new_runs}, {self.retail.pk, self.service.pk})
        for run in new_runs:
            self.assertEqual(run.status, RunStatus.COMPLETED)
            self.assertEqual(run.model_config.model_version, 2)
            self.assertEqual(run.model_config.training_config["strategy"], "guarded_direct_v1")
            self.assertTrue(run.model_config.is_active)
            self.assertEqual(run.results.count(), 14)
        retail_config.refresh_from_db()
        service_config.refresh_from_db()
        self.assertTrue(retail_config.is_active)
        self.assertTrue(service_config.is_active)
        self.assertEqual(old_retail_run.results.get().pk, old_retail_result.pk)
        self.assertEqual(old_service_run.results.get().pk, old_service_result.pk)
        self.assertEqual(list(ForecastResult.objects.order_by("pk").values_list(
            "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        ))[:2], old_result_state[:2])
        self.assertEqual(
            AuditLog.objects.filter(action="PUBLISH_GUARDED_FORECAST", actor_type=ActorType.SYSTEM_JOB,
                                    actor_user__isnull=True).count(),
            2,
        )

        counts = (ForecastModelConfig.objects.count(), ForecastRun.objects.count(),
                  ForecastResult.objects.count(), AuditLog.objects.count())
        self.publish(
            release_id="release-append-only-1",
            workspaces=[self.retail.code, self.service.code],
            apply=True,
        )
        self.assertEqual(
            (ForecastModelConfig.objects.count(), ForecastRun.objects.count(),
             ForecastResult.objects.count(), AuditLog.objects.count()),
            counts,
        )

    def test_apply_failure_rolls_back_only_new_release_rows_and_keeps_old_hashes(self):
        config = self.create_legacy_config(self.retail, TargetType.RETAIL_REVENUE)
        old_run, old_result = self.create_old_result(self.retail, config, TargetType.RETAIL_REVENUE)
        old_config_count = ForecastModelConfig.objects.count()
        old_run_count = ForecastRun.objects.count()
        old_result_rows = list(ForecastResult.objects.values_list(
            "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        ))
        old_audit_count = AuditLog.objects.count()

        with patch(
            "apps.forecasting.training.train_forecast_model",
            side_effect=RuntimeError("controlled prediction/training failure"),
        ):
            with self.assertRaises(CommandError):
                self.publish(
                    release_id="release-rollback-1",
                    workspaces=[self.retail.code],
                    apply=True,
                )

        config.refresh_from_db()
        old_run.refresh_from_db()
        old_result.refresh_from_db()
        self.assertEqual(ForecastModelConfig.objects.count(), old_config_count)
        self.assertEqual(ForecastRun.objects.count(), old_run_count)
        self.assertEqual(list(ForecastResult.objects.values_list(
            "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        )), old_result_rows)
        self.assertEqual(AuditLog.objects.count(), old_audit_count)
        self.assertTrue(config.is_active)
        self.assertEqual(old_run.status, RunStatus.COMPLETED)

    def test_apply_rolls_back_when_validation_selected_xgb_fails_matched_holdout_gate(self):
        config = self.create_legacy_config(self.retail, TargetType.RETAIL_REVENUE)
        old_run, old_result = self.create_old_result(self.retail, config, TargetType.RETAIL_REVENUE)
        before = {
            "configs": ForecastModelConfig.objects.count(),
            "runs": ForecastRun.objects.count(),
            "results": list(ForecastResult.objects.values_list(
                "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
            )),
            "audit": AuditLog.objects.count(),
        }
        rejection_fixture = {
            "artifact": {
                "format": "alphatech_guarded_forecast_v1",
                "effective_model": "XGBOOST_DIRECT",
                "calendar_mode": "none",
                "columns": [],
                "params": {},
                "booster": None,
            },
            "selection": {"effective_model": "XGBOOST_DIRECT", "reason": "validation_gates_passed", "params": {}},
            "model_metrics": {"mae": 11.0, "rmse": 12.0, "mape": 10.0, "r2": 0.0, "bias": 1.0, "count": 14},
            "baseline_metrics": {
                "ma7": {"mae": 10.0, "rmse": 11.0, "mape": 9.0, "r2": 0.0, "bias": 0.0, "count": 14},
                "seasonal_naive_7": {"mae": 15.0, "rmse": 16.0, "mape": 12.0, "r2": -0.1, "bias": 1.0, "count": 14},
            },
            "feature_importances": {},
            "evaluation": {
                "method": "chronological_validation_selection_then_separate_rolling_holdout",
                "partitions": {
                    "initial_fit": ["2026-01-01", "2026-01-13"],
                    "validation": ["2026-01-14", "2026-02-10"],
                    "holdout": ["2026-02-11", "2026-02-24"],
                },
                "counts": {"history": 55, "initial_fit": 13, "validation": 28, "holdout": 14},
                "intervals_calibrated": False,
            },
            "holdout_rows": [],
        }

        with patch("apps.forecasting.guarded.fit_guarded", return_value=rejection_fixture):
            with self.assertRaises(CommandError):
                self.publish(
                    release_id="release-holdout-rejected-1",
                    workspaces=[self.retail.code],
                    apply=True,
                )

        config.refresh_from_db()
        old_run.refresh_from_db()
        old_result.refresh_from_db()
        self.assertEqual(ForecastModelConfig.objects.count(), before["configs"])
        self.assertEqual(ForecastRun.objects.count(), before["runs"])
        self.assertEqual(list(ForecastResult.objects.values_list(
            "pk", "forecast_run_id", "forecast_date", "predicted_value", "lower_bound", "upper_bound"
        )), before["results"])
        self.assertEqual(AuditLog.objects.count(), before["audit"])
        self.assertTrue(config.is_active)
        self.assertEqual(old_run.status, RunStatus.COMPLETED)

    def test_unknown_or_inactive_workspace_is_rejected_without_writes(self):
        inactive = Workspace.objects.create(
            name="Inactive publication scope",
            code="inactive-publication-scope",
            workspace_type=WorkspaceType.RETAIL,
            is_active=False,
        )
        before = (ForecastModelConfig.objects.count(), ForecastRun.objects.count(), AuditLog.objects.count())
        with self.assertRaises(CommandError):
            self.publish(release_id="release-bad-scope", workspaces=["unknown-publication-scope"])
        with self.assertRaises(CommandError):
            self.publish(release_id="release-inactive-scope", workspaces=[inactive.code])
        self.assertEqual(
            (ForecastModelConfig.objects.count(), ForecastRun.objects.count(), AuditLog.objects.count()),
            before,
        )

    def test_all_targets_option_appends_only_existing_domain_targets(self):
        before = (ForecastModelConfig.objects.count(), ForecastRun.objects.count(),
                  ForecastResult.objects.count(), AuditLog.objects.count())
        self.publish(
            release_id="release-all-targets-1",
            workspaces=[self.retail.code, self.service.code],
            apply=True,
            all_targets=True,
        )
        runs = list(ForecastRun.objects.filter(job_parameters__release_id="release-all-targets-1"))
        self.assertEqual(len(runs), 4)
        self.assertEqual(
            {(run.workspace_id, run.target_type) for run in runs},
            {
                (self.retail.pk, TargetType.RETAIL_REVENUE),
                (self.retail.pk, TargetType.RETAIL_ORDER_VOLUME),
                (self.retail.pk, TargetType.RETAIL_PRODUCT_DEMAND),
                (self.service.pk, TargetType.SERVICE_TICKET_VOLUME),
            },
        )
        self.assertTrue(all(run.status == RunStatus.COMPLETED for run in runs))
        self.assertTrue(all(run.results.count() == 14 for run in runs))
        self.assertEqual(ForecastResult.objects.count(), before[2] + 56)
        self.assertEqual(AuditLog.objects.count(), before[3] + 4)
