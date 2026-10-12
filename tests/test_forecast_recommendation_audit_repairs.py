"""Regression evidence for truthful forecasts, rules and telemetry (isolated DB)."""
import datetime
import io
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Customer, Order, Category, Product
from apps.forecasting.models import ForecastModelConfig, ForecastRun, ForecastResult, TargetType
from apps.forecasting.diagnostics import assess_model_quality, assess_snapshot
from apps.forecasting.services import get_forecast_chart_data
from apps.forecasting.evaluation import compare_model_against_baseline
from apps.forecasting.management.commands.forecast_monitor import monitor_run
from apps.recommendations.models import Recommendation, RecommendationType
from apps.recommendations.rules import evaluate_retail_recommendations
from apps.recommendations.services import recommendation_review_state, accept_recommendation
from apps.approvals.registry import ToolValidationError


class ForecastDiagnosticTests(SimpleTestCase):
    def test_quality_keeps_negative_r2_and_prefers_better_baseline(self):
        result = assess_model_quality({"mae": 30, "rmse": 40, "r2": -1},
                                     {"naive_mae": 25, "naive_rmse": 35,
                                      "moving_average_7_mae": 20, "moving_average_7_rmse": 30})
        self.assertEqual(result["status"], "BASELINE_PREFERRED")
        self.assertEqual(result["comparisons"]["mae"]["best_baseline"], "moving_average_7")
        self.assertTrue(result["negative_r2"])
        self.assertFalse(result["operationally_validated"])

    def test_missing_or_nonfinite_metrics_are_unassessed(self):
        self.assertEqual(assess_model_quality({"mae": float("nan")}, {})["status"], "UNASSESSED")

    def test_boolean_or_numeric_string_is_not_a_measured_quality_metric(self):
        for invalid in (False, "0"):
            with self.subTest(value=invalid):
                self.assertEqual(assess_model_quality({"mae": invalid, "rmse": invalid},
                                                     {"naive_mae": 10, "naive_rmse": 10})["status"], "UNASSESSED")

    def test_metric_specific_winners_do_not_become_general_superiority(self):
        result = assess_model_quality({"mae": 9, "rmse": 15, "r2": 0.1},
                                     {"naive_mae": 10, "naive_rmse": 10,
                                      "moving_average_7_mae": 11, "moving_average_7_rmse": 12})
        self.assertTrue(result["comparisons"]["mae"]["beats_best_baseline"])
        self.assertFalse(result["comparisons"]["rmse"]["beats_best_baseline"])
        self.assertEqual(result["status"], "BASELINE_PREFERRED")

    def test_historical_horizon_cannot_be_operational(self):
        today = timezone.localdate()
        result = assess_snapshot(today - datetime.timedelta(days=30), [today - datetime.timedelta(days=29)])
        self.assertEqual(result["status"], "HISTORICAL")
        self.assertFalse(result["operational"])

    def test_stale_and_future_datasets_cannot_be_operational(self):
        today = timezone.localdate()
        self.assertEqual(assess_snapshot(today - datetime.timedelta(days=30))["status"], "STALE")
        self.assertEqual(assess_snapshot(today + datetime.timedelta(days=1))["status"], "FUTURE_DATA")

    def test_zero_or_missing_baseline_is_not_measured_equality_or_improvement(self):
        compared = compare_model_against_baseline({"mae": 1}, {"mae": 0, "naive_mae": 10})
        self.assertIsNone(compared["mae_improvement_pct"])
        self.assertIsNone(compared["rmse_improvement_pct"])
        self.assertIsNone(compared["mape_improvement_pct"])
        self.assertIsNone(compare_model_against_baseline({}, {"naive_mae": 10})["mae_improvement_pct"])

    def test_invalid_comparison_values_do_not_become_numeric_gains(self):
        for invalid in (True, "2", -1, float("nan"), float("inf"), None):
            with self.subTest(value=invalid):
                self.assertIsNone(compare_model_against_baseline({"mae": invalid}, {"naive_mae": 10})["mae_improvement_pct"])
                self.assertIsNone(compare_model_against_baseline({"mae": 2}, {"naive_mae": invalid})["mae_improvement_pct"])

    def test_valid_comparison_keeps_direction_zero_and_original_metrics(self):
        model, baseline = {"mae": 0, "rmse": 12, "mape": 10}, {"mae": 5, "rmse": 10, "mape": 10}
        self.assertEqual(compare_model_against_baseline(model, baseline),
                         {"mae_improvement_pct": 100, "rmse_improvement_pct": -20, "mape_improvement_pct": 0})
        self.assertEqual(model, {"mae": 0, "rmse": 12, "mape": 10})
        self.assertEqual(baseline, {"mae": 5, "rmse": 10, "mape": 10})


class ForecastRuleRepairTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code="audit-retail", name="Audit retail", workspace_type="RETAIL")
        cls.other = Workspace.objects.create(code="audit-other", name="Other", workspace_type="RETAIL")
        cls.customer = Customer.objects.create(workspace=cls.workspace, code="C1", name="Customer")
        cls.user = User.objects.create_superuser(username="audit-manager", email="audit@example.invalid", password="Test-only-Password123!")
        role = Role.objects.create(name="ADMIN")
        WorkspaceMembership.objects.create(user=cls.user, workspace=cls.workspace, role=role, is_default=True)
        cls.config = ForecastModelConfig.objects.create(workspace=cls.workspace, name="Revenue", target_type=TargetType.RETAIL_REVENUE)
        cls.category = Category.objects.create(workspace=cls.workspace, code="CAT", name="Category")
        cls.product = Product.objects.create(workspace=cls.workspace, category=cls.category, sku="SKU-A", name="Product", unit_price=10)

    def order(self, suffix, date, amount, status="COMPLETED"):
        return Order.objects.create(workspace=self.workspace, customer=self.customer, order_number="A-" + suffix,
                                    order_date=date, order_timestamp=timezone.now(), total_amount=Decimal(amount), status=status)

    def client_for_user(self):
        client = APIClient()
        client.force_authenticate(self.user)
        return client

    def test_malformed_chart_and_top_product_limits_return_400(self):
        client = self.client_for_user()
        for key, value in (("history_days", "abc"), ("horizon_days", "abc"), ("history_days", "-1"), ("horizon_days", "10000000")):
            with self.subTest(key=key, value=value):
                response = client.get("/api/v1/forecasting/chart-data/", {key: value}, HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
                self.assertEqual(response.status_code, 400)
        for value in ("abc", "-1", "101"):
            response = client.get("/api/v1/retail/analytics/top-products/", {"limit": value}, HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
            self.assertEqual(response.status_code, 400)

    def test_chart_reports_actual_horizon_and_localtime_without_mutating_run(self):
        today = timezone.localdate()
        end = today - datetime.timedelta(days=35)
        self.order("old", end, "100")
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config, target_type=TargetType.RETAIL_REVENUE,
                                         status="COMPLETED", dataset_period_end=end, model_metrics={"mae": 30, "rmse": 40, "r2": -1},
                                         baseline_metrics={"naive_mae": 25, "naive_rmse": 35}, job_parameters={"dimensions": {}})
        for index in range(1, 4):
            ForecastResult.objects.create(workspace=self.workspace, forecast_run=run, target_type=run.target_type,
                                          forecast_date=end + datetime.timedelta(days=index), predicted_value=10)
        result = get_forecast_chart_data(self.workspace)
        self.assertEqual(result["forecast_point_count"], 3)
        self.assertEqual(result["snapshot"]["status"], "HISTORICAL")
        self.assertEqual(result["run_date"], timezone.localtime(run.created_at).strftime("%d/%m/%Y %H:%M %Z"))
        run.refresh_from_db()
        self.assertEqual(run.model_metrics["r2"], -1)
        self.assertEqual(run.status, "COMPLETED")

    def test_dimension_chart_rejects_foreign_product(self):
        category = Category.objects.create(workspace=self.other, name="Other", code="OTHER")
        product = Product.objects.create(workspace=self.other, category=category, name="Hidden", sku="PRIVATE", unit_price=10)
        response = self.client_for_user().get("/api/v1/forecasting/chart-data/",
                    {"target_type": TargetType.RETAIL_PRODUCT_DEMAND, "product_id": product.pk}, HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Hidden", str(response.data))

    def test_old_snapshot_does_not_generate_current_decline_or_low_volume(self):
        self.order("old", timezone.localdate() - datetime.timedelta(days=35), "500")
        with patch("apps.recommendations.rules.evaluate_retail_stockout_recommendations", return_value=[]):
            self.assertEqual(evaluate_retail_recommendations(self.workspace), [])

    def test_good_mae_does_not_mean_declining_revenue(self):
        today = timezone.localdate()
        self.order("previous", today - datetime.timedelta(days=10), "100")
        self.order("now", today, "200")
        ForecastRun.objects.create(workspace=self.workspace, model_config=self.config, target_type=TargetType.RETAIL_REVENUE,
                                    status="COMPLETED", model_metrics={"mae_improvement_pct": 50})
        with patch("apps.recommendations.rules.evaluate_retail_stockout_recommendations", return_value=[]):
            rows = evaluate_retail_recommendations(self.workspace)
        self.assertFalse(any(row.recommendation_type == RecommendationType.RETAIL_DECLINING_REVENUE for row in rows))

    def test_decline_uses_completed_business_dates_and_equal_periods(self):
        today = timezone.localdate()
        self.order("previous", today - datetime.timedelta(days=10), "1000")
        self.order("now", today, "100")
        self.order("uncompleted", today, "50000000", "PENDING")
        with patch("apps.recommendations.rules.evaluate_retail_stockout_recommendations", return_value=[]):
            rows = evaluate_retail_recommendations(self.workspace)
        rec = next(row for row in rows if row.recommendation_type == RecommendationType.RETAIL_DECLINING_REVENUE)
        self.assertEqual(rec.supporting_data["recent_7d_revenue_vnd"], 100)
        self.assertEqual(rec.supporting_data["previous_7d_completed_revenue_vnd"], 1000)
        self.assertEqual(rec.supporting_data["scope"], "workspace")
        self.assertIsNotNone(rec.expires_at)
        self.assertNotIn("chi nhánh", rec.title)

    def test_old_pending_advice_is_marked_stale_and_accept_denied(self):
        rec = Recommendation.objects.create(workspace=self.workspace, title="Old", recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME)
        Recommendation.objects.filter(pk=rec.pk).update(created_at=timezone.now() - datetime.timedelta(days=35))
        rec.refresh_from_db()
        self.assertTrue(recommendation_review_state(rec)["stale"])
        with self.assertRaises(ToolValidationError):
            accept_recommendation(rec, self.user)
        rec.refresh_from_db()
        self.assertEqual(rec.status, "PENDING")

    def test_forecast_ui_keeps_negative_badge_and_dimensions_controls(self):
        self.client.force_login(self.user)
        response = self.client.get("/noibo/forecasting/", {"target": TargetType.RETAIL_PRODUCT_DEMAND, "product_id": self.product.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="product_id"')
        self.assertContains(response, 'name="category_id"')
        self.assertContains(response, 'name="branch_id"')
        self.assertEqual(response.context["chart_data"]["dimensions"], {"product_id": self.product.pk})
        self.assertNotContains(response, "Tương lai 14 Ngày")
        ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                    target_type=TargetType.RETAIL_REVENUE, status="COMPLETED",
                                    dataset_period_end=timezone.localdate(), job_parameters={"dimensions": {}},
                                    model_metrics={"mae": 30, "rmse": 40, "r2": -1, "mae_improvement_pct": -1.5},
                                    baseline_metrics={"naive_mae": 25, "naive_rmse": 35})
        revenue = self.client.get("/noibo/forecasting/", {"target": TargetType.RETAIL_REVENUE})
        self.assertContains(revenue, "MAE xấu đi")
        self.assertContains(revenue, "R² âm")
        self.assertNotContains(revenue, "+-")
        self.assertNotContains(revenue, '<span class="kpi-badge-gain">')

    def test_telemetry_does_not_publish_unmeasured_claims(self):
        self.client.force_login(self.user)
        response = self.client.get("/noibo/telemetry/")
        self.assertEqual(response.status_code, 200)
        for unsupported in ("OPTIMAL", "100% Tuân thủ", "Zero Polling Overhead", "Ping PostGIS Spatial Query", "PostGIS 3.4 &"):
            self.assertNotContains(response, unsupported)
        self.assertContains(response, "DATABASE SNAPSHOT")
        self.assertContains(response, "không phải benchmark AI/GIS")
        self.assertContains(response, "Đang kiểm tra HTTP /api/health/")
        self.assertNotContains(response, "Đang gửi truy vấn benchmark đo lường")

    def test_chart_weekly_actuals_follow_saved_run_granularity(self):
        self.order("weekly-a", datetime.date(2026, 1, 2), "20")
        self.order("weekly-b", datetime.date(2026, 1, 3), "30")
        run = ForecastRun.objects.create(
            workspace=self.workspace, model_config=self.config, target_type=TargetType.RETAIL_REVENUE,
            status="COMPLETED", dataset_period_end=datetime.date(2026, 1, 5),
            job_parameters={"dimensions": {}, "provenance": {"granularity": "WEEKLY"}},
            model_metrics={"mae": 12, "r2": -2},
        )
        ForecastResult.objects.create(workspace=self.workspace, forecast_run=run, target_type=run.target_type,
                                      forecast_date=datetime.date(2026, 1, 12), predicted_value=55)
        # Current config is DAILY; it must not rewrite a prior WEEKLY run's units.
        result = get_forecast_chart_data(self.workspace)
        self.assertEqual(result["granularity"], "WEEKLY")
        self.assertEqual(result["historical"], [{"date": "2026-01-05", "value": 50}])
        self.assertEqual(result["forecast"][0]["date"], "2026-01-12")
        self.assertEqual(result["metrics"]["r2"], -2)
        run.refresh_from_db()
        self.assertEqual(run.model_metrics, {"mae": 12, "r2": -2})

    def test_weekly_chart_cutoff_does_not_silently_drop_first_week_days(self):
        self.order("first-week-tue", datetime.date(2026, 1, 6), "20")
        self.order("first-week-thu", datetime.date(2026, 1, 8), "30")
        ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                   target_type=TargetType.RETAIL_REVENUE, status="COMPLETED",
                                   job_parameters={"provenance": {"granularity": "WEEKLY"}})
        with patch("apps.forecasting.services.timezone.localdate", return_value=datetime.date(2026, 1, 10)):
            result = get_forecast_chart_data(self.workspace, history_days=2)
        self.assertEqual(result["historical"], [{"date": "2026-01-12", "value": 50}])

    def test_monitor_excludes_imputed_and_future_days_but_keeps_observed_zero(self):
        self.order("observed", datetime.date(2026, 1, 1), "10")
        self.order("observed-zero", datetime.date(2026, 1, 3), "0")
        self.order("future", datetime.date(2026, 1, 5), "50")
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                         target_type=TargetType.RETAIL_REVENUE, status="COMPLETED",
                                         model_metrics={"mae": "invalid", "r2": -1})
        for day, predicted in ((1, 10), (2, 999), (3, 5), (4, 8), (5, 55)):
            ForecastResult.objects.create(workspace=self.workspace, forecast_run=run, target_type=run.target_type,
                                          forecast_date=datetime.date(2026, 1, day), predicted_value=predicted)
        report = monitor_run(run, datetime.date(2026, 1, 4))
        self.assertEqual(report["matched_actuals"], 2)
        self.assertEqual(report["realized_mae"], 2.5)
        self.assertEqual(report["imputed_forecast_points_excluded"], 1)
        self.assertEqual(report["source_observation_count"], 2)
        self.assertIsNone(report["holdout_mae"])
        self.assertIsNone(report["drift_warning"])
        run.refresh_from_db()
        self.assertEqual(run.model_metrics, {"mae": "invalid", "r2": -1})

    def test_monitor_zero_holdout_does_not_invent_relative_drift_threshold(self):
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                         target_type=TargetType.RETAIL_REVENUE, status="COMPLETED",
                                         model_metrics={"mae": 0, "r2": -2})
        for day in range(1, 8):
            date = datetime.date(2026, 1, day)
            self.order(f"zero-{day}", date, "0")
            ForecastResult.objects.create(workspace=self.workspace, forecast_run=run, target_type=run.target_type,
                                          forecast_date=date, predicted_value=1)
        report = monitor_run(run, datetime.date(2026, 1, 8))
        self.assertEqual(report["matched_actuals"], 7)
        self.assertEqual(report["realized_mae"], 1)
        self.assertEqual(report["holdout_mae"], 0)
        self.assertIsNone(report["drift_warning"])

    def test_monitor_weekly_snapshot_and_utc_midnight_use_local_business_dates(self):
        self.order("week-1", datetime.date(2026, 1, 2), "20")
        self.order("week-2", datetime.date(2026, 1, 3), "30")
        run = ForecastRun.objects.create(
            workspace=self.workspace, model_config=self.config, target_type=TargetType.RETAIL_REVENUE,
            status="COMPLETED", dataset_period_end=datetime.date(2026, 1, 5),
            job_parameters={"provenance": {"granularity": "WEEKLY", "dimensions": {}}},
            model_metrics={"mae": 2},
        )
        ForecastResult.objects.create(workspace=self.workspace, forecast_run=run, target_type=run.target_type,
                                      forecast_date=datetime.date(2026, 1, 5), predicted_value=55)
        stream = io.StringIO()
        # UTC 05/01 22:00 is already 06/01 in the active +07 business timezone.
        with timezone.override("Asia/Ho_Chi_Minh"), patch("django.utils.timezone.now", return_value=datetime.datetime(2026, 1, 5, 22, tzinfo=datetime.timezone.utc)):
            call_command("forecast_monitor", stdout=stream)
        report = json.loads(stream.getvalue())[0]
        self.assertEqual(report["as_of"], "2026-01-06")
        self.assertEqual(report["series_granularity"], "WEEKLY")
        self.assertEqual(report["granularity_source"], "saved_provenance")
        self.assertEqual(report["matched_actuals"], 1)
        self.assertEqual(report["realized_mae"], 5)
        self.assertIn("not verified daily completeness", report["note"])

    def test_monitor_invalid_legacy_context_does_not_hide_other_runs(self):
        ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                   target_type=TargetType.RETAIL_REVENUE, status="COMPLETED",
                                   job_parameters={"dimensions": "not-a-dict"})
        valid = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                                           target_type=TargetType.RETAIL_REVENUE, status="COMPLETED")
        stream = io.StringIO()
        call_command("forecast_monitor", stdout=stream)
        reports = json.loads(stream.getvalue())
        self.assertEqual(len(reports), 2)
        self.assertIn(valid.pk, [report["run_id"] for report in reports])
        invalid = next(report for report in reports if "error_code" in report)
        self.assertEqual(invalid["error_code"], "INVALID_SERIES_CONTEXT")
        self.assertEqual(invalid["assessment_status"], "UNASSESSED")
