"""
Automated Test Suite for Retail Stockout Prediction & Reorder Recommendation.
Validates Mathematical Formulas, Demand Forecasting, Risk Level Tiers, and AI Tools.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import (
    Category,
    Product,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    StockBalance,
)
from apps.retail.stockout_services import (
    predict_product_daily_demand,
    evaluate_product_stockout_risk,
    get_stockout_risk_dashboard_data,
)
from apps.recommendations.models import Recommendation, RecommendationType, RecommendationStatus
from apps.recommendations.rules import evaluate_retail_stockout_recommendations
from apps.knowledge.tools import get_stockout_risk_summary, get_stock_balance_summary


class RetailStockoutPredictionTestCase(TestCase):
    def setUp(self):
        # 1. Setup Workspace & User
        self.workspace = Workspace.objects.create(
            code="abc-retail-test",
            name="ABC Tech Test Store",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.user = User.objects.create_user(
            username="analyst_user",
            email="analyst@example.com",
            password="Password123!",
            is_superuser=True,
        )

        # 2. Setup Category & Products
        self.category_laptop = Category.objects.create(
            workspace=self.workspace,
            name="Laptop",
            code="laptop",
        )
        self.category_mouse = Category.objects.create(
            workspace=self.workspace,
            name="Chuột & Bàn phím",
            code="accessories",
        )

        self.prod_asus = Product.objects.create(
            workspace=self.workspace,
            category=self.category_laptop,
            sku="ASUS-VIVO-14",
            name="ASUS VivoBook 14",
            unit="chiếc",
            unit_price=Decimal("15000000.00"),
            cost_price=Decimal("12000000.00"),
        )
        self.prod_lenovo = Product.objects.create(
            workspace=self.workspace,
            category=self.category_laptop,
            sku="LENOVO-IDEA-3",
            name="Lenovo IdeaPad 3",
            unit="chiếc",
            unit_price=Decimal("14000000.00"),
            cost_price=Decimal("11000000.00"),
        )
        self.prod_mouse = Product.objects.create(
            workspace=self.workspace,
            category=self.category_mouse,
            sku="LOGI-GPRO",
            name="Chuột Logitech G Pro",
            unit="cái",
            unit_price=Decimal("2500000.00"),
            cost_price=Decimal("1800000.00"),
        )

        # 3. Setup Branches
        self.branch_a = Branch.objects.create(
            workspace=self.workspace,
            code="BR-Q1",
            name="Chi nhánh Quận 1",
            address="123 Nguyễn Huệ, Q.1",
        )
        self.branch_b = Branch.objects.create(
            workspace=self.workspace,
            code="BR-Q3",
            name="Chi nhánh Quận 3",
            address="456 CMT8, Q.3",
        )

        # 4. Setup Customer
        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-001",
            name="Nguyễn Văn Test",
            phone="0901234567",
        )

        # 5. Create Historical Completed Orders for Asus VivoBook (e.g. 2 units/day average over past 14 days)
        today = timezone.now().date()
        for i in range(1, 15):
            order_date_val = today - timedelta(days=i)
            order = Order.objects.create(
                workspace=self.workspace,
                order_number=f"ORD-TEST-{i:03d}",
                customer=self.customer,
                branch=self.branch_a,
                order_date=order_date_val,
                order_timestamp=timezone.now() - timedelta(days=i),
                status=OrderStatus.COMPLETED,
                total_amount=Decimal("30000000.00"),
            )
            OrderItem.objects.create(
                order=order,
                product=self.prod_asus,
                quantity=2,
                unit_price=Decimal("15000000.00"),
                subtotal=Decimal("30000000.00"),
            )

    def test_predict_product_daily_demand(self):
        """Tests that product daily demand forecasting correctly estimates velocity."""
        demand = predict_product_daily_demand(self.workspace, self.prod_asus, self.branch_a)
        # Expected around 2.0 units per day
        self.assertGreaterEqual(demand, 1.5)
        self.assertLessEqual(demand, 2.5)

    def test_stockout_risk_formulas_high_risk(self):
        """
        Tests High Risk condition:
        Stock = 4, Demand = 2.0/day
        days_to_stockout = 4 / 2.0 = 2.0 days (< 7 lead time) -> HIGH risk.
        Target coverage = 7 + 3 = 10 days (20 units needed).
        Suggested reorder = 20 - 4 = 16 units.
        """
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_a,
            product=self.prod_asus,
            quantity_on_hand=4,
        )

        analysis = evaluate_product_stockout_risk(self.workspace, self.prod_asus, self.branch_a)
        self.assertEqual(analysis["risk_level"], "HIGH")
        self.assertEqual(analysis["risk_label_vi"], "Nguy cơ hết hàng cao")
        self.assertLess(analysis["days_to_stockout"], 7.0)
        self.assertGreater(analysis["suggested_reorder_quantity"], 0)
        self.assertEqual(analysis["current_stock"], 4)

    def test_stockout_risk_formulas_out_of_stock(self):
        """Tests Out of Stock condition (current_stock = 0)."""
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_a,
            product=self.prod_asus,
            quantity_on_hand=0,
        )

        analysis = evaluate_product_stockout_risk(self.workspace, self.prod_asus, self.branch_a)
        self.assertEqual(analysis["risk_level"], "OUT_OF_STOCK")
        self.assertEqual(analysis["risk_label_vi"], "Hết hàng")
        self.assertEqual(analysis["days_to_stockout"], 0.0)
        self.assertEqual(analysis["expected_stockout_date"], timezone.now().date().strftime("%Y-%m-%d"))

    def test_stockout_risk_formulas_safe_stock(self):
        """Tests Low Risk / Safe Stock condition (current_stock = 100)."""
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_a,
            product=self.prod_asus,
            quantity_on_hand=100,
        )

        analysis = evaluate_product_stockout_risk(self.workspace, self.prod_asus, self.branch_a)
        self.assertEqual(analysis["risk_level"], "LOW")
        self.assertEqual(analysis["risk_label_vi"], "Tồn kho an toàn")
        self.assertGreater(analysis["days_to_stockout"], 10.0)
        self.assertEqual(analysis["suggested_reorder_quantity"], 0)

    def test_recommendation_engine_generates_explainable_stockout_alert(self):
        """Tests that evaluate_retail_stockout_recommendations produces explainable recommendations."""
        # Set Asus to High Risk (4 units)
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_a,
            product=self.prod_asus,
            quantity_on_hand=4,
        )

        recs = evaluate_retail_stockout_recommendations(self.workspace)
        self.assertGreaterEqual(len(recs), 1)

        asus_recs = [r for r in recs if "ASUS" in r.title]
        self.assertTrue(len(asus_recs) > 0)
        asus_rec = asus_recs[0]
        self.assertIn("ASUS VivoBook 14", asus_rec.title)
        
        # Verify 4 required explainability fields
        exp = asus_rec.explanation
        self.assertIn("what", exp)
        self.assertIn("why", exp)
        self.assertIn("evidence", exp)
        self.assertIn("expected_effect", exp)

        # Verify evidence payload
        ev = exp["evidence"]
        self.assertEqual(ev["product_id"], self.prod_asus.id)
        self.assertEqual(ev["current_stock"], 4)
        self.assertIn("predicted_daily_demand", ev)
        self.assertIn("days_to_stockout", ev)
        self.assertIn("suggested_reorder_quantity", ev)

    def test_ai_tools_stockout_and_stock_balance(self):
        """Tests get_stockout_risk_summary and get_stock_balance_summary AI tools."""
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_a,
            product=self.prod_asus,
            quantity_on_hand=4,
        )
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_b,
            product=self.prod_asus,
            quantity_on_hand=18,
        )

        # 1. Stockout risk tool
        risk_res = get_stockout_risk_summary(self.workspace, self.user, category="laptop")
        self.assertEqual(risk_res["tool"], "get_stockout_risk_summary")
        self.assertIn("products_at_risk", risk_res)

        # 2. Stock balance tool
        bal_res = get_stock_balance_summary(self.workspace, self.user, category="laptop")
        self.assertEqual(bal_res["tool"], "get_stock_balance_summary")
        self.assertEqual(bal_res["total_stock_units"], 22)
        self.assertEqual(len(bal_res["balances"]), 2)
