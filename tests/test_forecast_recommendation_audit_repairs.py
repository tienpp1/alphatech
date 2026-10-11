"""Regression evidence for truthful forecasts, rules and telemetry (isolated DB)."""
import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Customer, Order, Category, Product
from apps.forecasting.models import ForecastModelConfig, ForecastRun, ForecastResult, TargetType
from apps.forecasting.diagnostics import assess_model_quality, assess_snapshot
from apps.forecasting.services import get_forecast_chart_data
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
