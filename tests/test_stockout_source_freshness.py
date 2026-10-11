"""Stockout heuristic provenance and immutable forecast history regressions."""
import copy
import datetime
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase, RequestFactory
from django.http import Http404
from django.utils import timezone

from apps.forecasting.diagnostics import assess_model_quality
from apps.accounts.models import User
from apps.retail.models import Branch, Category, Customer, Order, OrderItem, Product, StockBalance
from apps.retail.stockout_services import evaluate_product_stockout_risk, predict_product_daily_demand, get_stockout_risk_dashboard_data
from apps.retail.ui_views import retail_stockout_risk_view
from apps.recommendations.models import Recommendation, RecommendationType
from apps.recommendations.rules import evaluate_retail_stockout_recommendations
from apps.recommendations.services import recommendation_review_state, accept_recommendation
from apps.approvals.registry import ToolValidationError
from apps.workspaces.models import Workspace


class StockoutSourceFreshnessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code="stockout-fresh", name="Freshness", workspace_type="RETAIL")
        cls.customer = Customer.objects.create(workspace=cls.workspace, code="C", name="Customer")
        cls.category = Category.objects.create(workspace=cls.workspace, code="cat", name="Category")
        cls.product = Product.objects.create(workspace=cls.workspace, category=cls.category, sku="P", name="Product", unit_price=10)
        cls.branch = Branch.objects.create(workspace=cls.workspace, code="A", name="Branch A", address="A")
        cls.other_branch = Branch.objects.create(workspace=cls.workspace, code="B", name="Branch B", address="B")
        cls.other_workspace = Workspace.objects.create(code="stockout-other", name="Other", workspace_type="RETAIL")
        cls.foreign_branch = Branch.objects.create(workspace=cls.other_workspace, code="F", name="Foreign", address="F")
        cls.user = User.objects.create(username="stockout-admin", is_active=True, is_staff=True, is_superuser=True)

    def completed_order(self, suffix, days_ago, quantity, branch=None):
        order = Order.objects.create(workspace=self.workspace, customer=self.customer,
                                     order_number="F-" + suffix, branch=branch or self.branch,
                                     order_date=timezone.localdate() - datetime.timedelta(days=days_ago),
                                     order_timestamp=timezone.now(), status="COMPLETED", total_amount=quantity * 10)
        OrderItem.objects.create(order=order, product=self.product, quantity=quantity, unit_price=10, subtotal=quantity * 10)
        return order

    def test_old_all_time_fallback_is_explicitly_not_current_xgboost(self):
        self.completed_order("old", 100, 100)
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch, current_stock=100)
        self.assertEqual(result["predicted_daily_demand"], 1.0)
        assessment = result["demand_assessment"]
        self.assertEqual(assessment["method"], "ALL_TIME_AVERAGE_HEURISTIC")
        self.assertEqual(assessment["status"], "STALE_HISTORY")
        self.assertEqual(assessment["age_days"], 100)
        self.assertFalse(assessment["operationally_validated"])
        self.assertNotEqual(result["risk_label_vi"], "Tồn kho an toàn")

    def test_first_observation_is_scoped_to_selected_branch(self):
        self.completed_order("other-old", 300, 300, self.other_branch)
        self.completed_order("selected-old", 100, 100)
        self.assertEqual(predict_product_daily_demand(self.workspace, self.product, self.branch), 1.0)

    def test_future_completed_order_cannot_supply_historical_demand(self):
        self.completed_order("future", -3, 1000)
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch, current_stock=100)
        self.assertEqual(result["predicted_daily_demand"], 0)
        self.assertEqual(result["demand_assessment"]["status"], "NO_DATA")
        self.assertEqual(result["demand_assessment"]["method"], "NO_OBSERVATIONS")

    def test_no_observations_does_not_claim_safe_inventory(self):
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch, current_stock=100)
        self.assertEqual(result["risk_label_vi"], "Chưa đủ dữ liệu nhu cầu")
        self.assertEqual(result["risk_badge"], "badge-warning")
        self.assertIsNone(result["demand_assessment"]["latest_observation_date"])

    def test_recent_positive_sales_retain_weighted_formula_and_truthful_method(self):
        today = timezone.localdate()
        history = {today - datetime.timedelta(days=index): 2 for index in range(1, 15)}
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch,
                                               current_stock=4, historical_daily_data=history)
        self.assertEqual(result["predicted_daily_demand"], 2)
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertEqual(result["demand_assessment"]["method"], "WEIGHTED_LAG_HEURISTIC")
        self.assertEqual(result["demand_assessment"]["status"], "CURRENT_HISTORY")
        self.assertFalse(result["demand_assessment"]["operationally_validated"])

    def test_recent_window_with_only_old_sales_is_stale(self):
        history = {timezone.localdate() - datetime.timedelta(days=40): 10}
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch,
                                               current_stock=4, historical_daily_data=history)
        self.assertEqual(result["demand_assessment"]["status"], "STALE_HISTORY")
        self.assertNotEqual(result["risk_label_vi"], "Tồn kho an toàn")

    def test_missing_balance_does_not_certify_stockout_but_retains_numeric_contract(self):
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch)
        self.assertEqual(result["current_stock"], 0)
        self.assertEqual(result["risk_level"], "OUT_OF_STOCK")
        self.assertEqual(result["inventory_assessment"]["status"], "MISSING_BALANCE")
        self.assertFalse(result["inventory_assessment"]["verified_record"])
        self.assertFalse(result["risk_level_is_operational"])
        self.assertEqual(result["risk_label_vi"], "Chưa ghi nhận tồn kho")

    def test_recorded_zero_balance_is_distinct_from_missing(self):
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=0)
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch)
        self.assertEqual(result["inventory_assessment"]["status"], "RECORDED_BALANCE")
        self.assertTrue(result["inventory_assessment"]["verified_record"])
        self.assertTrue(result["risk_level_is_operational"])
        self.assertEqual(result["risk_label_vi"], "Hết hàng")

    def test_negative_balance_requires_reconciliation(self):
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=-2)
        result = evaluate_product_stockout_risk(self.workspace, self.product, self.branch)
        self.assertEqual(result["current_stock"], -2)
        self.assertEqual(result["inventory_assessment"]["status"], "NEGATIVE_BALANCE")
        self.assertFalse(result["risk_level_is_operational"])
        self.assertEqual(result["risk_label_vi"], "Tồn kho âm — cần đối soát")

    def test_aggregate_detects_negative_branch_even_when_total_positive(self):
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=-2)
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.other_branch, quantity_on_hand=10)
        result = get_stockout_risk_dashboard_data(self.workspace)["all_products"][0]
        self.assertEqual(result["current_stock"], 8)
        self.assertEqual(result["inventory_assessment"]["status"], "NEGATIVE_BALANCE")
        self.assertEqual(result["inventory_assessment"]["source_record_count"], 2)
        self.assertFalse(result["risk_level_is_operational"])

    def test_dashboard_does_not_count_missing_balance_as_verified_stockout(self):
        result = get_stockout_risk_dashboard_data(self.workspace, branch_id=self.branch.id)
        self.assertEqual(result["out_of_stock_count"], 1)
        self.assertEqual(result["verified_out_of_stock_count"], 0)
        self.assertEqual(result["inventory_unverified_count"], 1)

    def request_for(self, branch_id):
        request = RequestFactory().get("/noibo/retail/stockout-risk/", {"branch_id": branch_id})
        request.user, request.active_workspace = self.user, self.workspace
        return request

    def test_stockout_view_malformed_branch_is_400_not_500(self):
        for invalid in ("abc", "-1", "0", "1.5", "²", "9" * 100):
            with self.subTest(branch_id=invalid):
                self.assertEqual(retail_stockout_risk_view(self.request_for(invalid)).status_code, 400)

    def test_stockout_view_foreign_or_missing_branch_is_404(self):
        for branch_id in (self.foreign_branch.id, 999999):
            with self.subTest(branch_id=branch_id), self.assertRaises(Http404):
                retail_stockout_risk_view(self.request_for(branch_id))

    def test_dashboard_foreign_branch_never_broadens_scope(self):
        with self.assertRaises(Http404):
            get_stockout_risk_dashboard_data(self.workspace, branch_id=self.foreign_branch.id)

    def test_dashboard_rejects_nonpositive_or_malformed_branch(self):
        for invalid in (0, -1, "bad", True, "²", "9" * 100):
            with self.subTest(branch_id=invalid), self.assertRaises(ValueError):
                get_stockout_risk_dashboard_data(self.workspace, branch_id=invalid)

    def test_missing_or_negative_inventory_cannot_create_urgent_recommendation(self):
        self.assertEqual(evaluate_retail_stockout_recommendations(self.workspace), [])
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=-2)
        self.assertEqual(evaluate_retail_stockout_recommendations(self.workspace), [])
        self.assertFalse(Recommendation.objects.exists())

    def test_stale_history_zero_stock_remains_explicit_advisory_and_cannot_accept(self):
        self.completed_order("old-rec", 100, 100)
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=0)
        row = evaluate_retail_stockout_recommendations(self.workspace)[0]
        self.assertEqual(row.proposed_action, "")
        self.assertEqual(row.priority, "MEDIUM")
        self.assertIn("đã ghi nhận bằng 0", row.explanation["why"])
        self.assertIn("ước tính lịch sử/kịch bản", row.explanation["why"])
        self.assertIn("chưa có cam kết", row.explanation["why"])
        self.assertEqual(row.explanation["evidence"]["demand_assessment"]["status"], "STALE_HISTORY")
        self.assertTrue(recommendation_review_state(row)["stale"])
        self.assertGreater(row.expires_at, timezone.now())
        with self.assertRaises(ToolValidationError):
            accept_recommendation(row, self.user)
        row.refresh_from_db()
        self.assertEqual(row.status, "PENDING")

    def test_current_recorded_zero_history_can_acknowledge_without_mapping_mutation(self):
        for index in range(1, 15):
            self.completed_order("new-rec-" + str(index), index, 2)
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=0)
        row = evaluate_retail_stockout_recommendations(self.workspace)[0]
        self.assertFalse(recommendation_review_state(row)["stale"])
        self.assertTrue(recommendation_review_state(row)["stockout_evidence_current"])
        self.assertEqual(row.proposed_action, "")
        self.assertIn("không phải dự báo XGBoost", row.explanation["why"])
        self.assertEqual(accept_recommendation(row, self.user).status, "ACCEPTED")

    def test_no_demand_and_legacy_stockout_evidence_cannot_be_accepted(self):
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=0)
        row = evaluate_retail_stockout_recommendations(self.workspace)[0]
        self.assertTrue(recommendation_review_state(row)["stale"])
        self.assertEqual(row.explanation["evidence"]["demand_assessment"]["status"], "NO_DATA")
        with self.assertRaises(ToolValidationError):
            accept_recommendation(row, self.user)
        legacy = Recommendation.objects.create(workspace=self.workspace, recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
                                                title="Legacy", supporting_data={"current_stock": 0},
                                                expires_at=timezone.now() + datetime.timedelta(days=1))
        self.assertTrue(recommendation_review_state(legacy)["stale"])
        with self.assertRaises(ToolValidationError):
            accept_recommendation(legacy, self.user)
        legacy.refresh_from_db()
        self.assertEqual(legacy.supporting_data, {"current_stock": 0})
        self.assertEqual(legacy.status, "PENDING")

    def test_legacy_predictor_output_is_advisory_not_an_urgent_real_stockout(self):
        legacy = dict(product_id=self.product.id, product_sku="P", product_name="Product", current_stock=0,
                      predicted_daily_demand=2, days_to_stockout=0, lead_time_days=3,
                      suggested_reorder_quantity=6, unit="cái", risk_level="OUT_OF_STOCK",
                      expected_stockout_date="2026-09-15", safety_buffer_days=0)
        with patch("apps.retail.stockout_services.get_stockout_risk_dashboard_data", return_value={"products_at_risk": [legacy]}):
            row = evaluate_retail_stockout_recommendations(self.workspace)[0]
        self.assertEqual(row.priority, "MEDIUM")
        self.assertIn("Chưa đủ bằng chứng", row.explanation["why"])
        self.assertNotIn("hiện tại đã hết hàng", row.explanation["why"])
        self.assertTrue(recommendation_review_state(row)["stale"])

    def test_unknown_or_mislabelled_old_evidence_is_not_current(self):
        today = timezone.localdate()
        data = {"inventory_assessment": {"status": "RECORDED_BALANCE", "verified_record": True, "as_of": today.isoformat()},
                "demand_assessment": {"status": "CURRENT_HISTORY", "as_of": today.isoformat(),
                                      "latest_observation_date": (today - datetime.timedelta(days=100)).isoformat()}}
        row = Recommendation.objects.create(workspace=self.workspace, recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
                                             title="Stale mislabeled", supporting_data=data)
        self.assertTrue(recommendation_review_state(row)["stale"])
        with self.assertRaises(ToolValidationError):
            accept_recommendation(row, self.user)

    def test_expired_stockout_does_not_block_new_evaluation_or_get_retrofitted(self):
        self.completed_order("fresh-dedup", 1, 10)
        StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=0)
        old_data = {"evaluated_on": timezone.localdate().isoformat(), "current_stock": 0}
        old = Recommendation.objects.create(workspace=self.workspace, recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
                                             title="Old", supporting_data=old_data, source_references=[f"product:{self.product.id}"],
                                             expires_at=timezone.now() - datetime.timedelta(seconds=1))
        rows = evaluate_retail_stockout_recommendations(self.workspace)
        self.assertEqual(len(rows), 1)
        self.assertEqual(evaluate_retail_stockout_recommendations(self.workspace), [])
        old.refresh_from_db()
        self.assertEqual(old.supporting_data, old_data)
        self.assertEqual(old.status, "PENDING")


class ForecastHistoryImmutabilityTests(SimpleTestCase):
    def test_partial_baselines_do_not_claim_two_complete_comparisons(self):
        result = assess_model_quality({"mae": 5, "rmse": 6, "r2": 0.8}, {"naive_mae": 10, "naive_rmse": 12})
        self.assertEqual(result["status"], "BEATS_BASELINES_ON_HOLDOUT")
        self.assertNotIn("hai baseline", result["message"])
        self.assertFalse(result["operationally_validated"])

    def test_assessment_preserves_every_original_nested_and_failed_metric(self):
        metrics = {"mae": 40.25, "rmse": 85.75, "r2": -1.9, "mae_improvement": -76.2,
                   "per_fold": [{"r2": -3.5}], "notes": "original failed benchmark"}
        baselines = {"naive_mae": 10, "naive_rmse": 20, "moving_average_7_mae": 20,
                     "moving_average_7_rmse": 30, "raw": {"holdout_count": 14}}
        original_metrics, original_baselines = copy.deepcopy(metrics), copy.deepcopy(baselines)
        assessment = assess_model_quality(metrics, baselines)
        self.assertEqual(assessment["status"], "BASELINE_PREFERRED")
        self.assertEqual(metrics, original_metrics)
        self.assertEqual(baselines, original_baselines)
