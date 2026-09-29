from django.test import TestCase
from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Category, Product, Branch, StockBalance
from apps.knowledge.tools import explain_root_cause, ToolPermissionDenied


class RootCauseGroundingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ws = Workspace.objects.create(code="ground-a", name="A", workspace_type="RETAIL")
        cls.other = Workspace.objects.create(code="ground-b", name="B", workspace_type="RETAIL")
        cls.user = User.objects.create_user(username="reader")
        role = Role.objects.create(name="READER")
        permission = Permission.objects.create(codename="retail.view_product", name="View", module="retail")
        role.permissions.add(permission)
        WorkspaceMembership.objects.create(workspace=cls.ws, user=cls.user, role=role)
        category = Category.objects.create(workspace=cls.ws, name="Hardware", code="HW")
        cls.product = Product.objects.create(workspace=cls.ws, category=category, name="Exact product", sku="P1", unit_price=100)
        branch = Branch.objects.create(workspace=cls.ws, code="B", name="Branch", address="A", region="R")
        StockBalance.objects.create(workspace=cls.ws, product=cls.product, branch=branch, quantity_on_hand=17)

    def test_stock_evidence_uses_actual_quantity_not_invented_forecast(self):
        data = explain_root_cause(self.ws, self.user, target_type="STOCKOUT_WARNING", entity_id=self.product.pk)
        self.assertEqual(data["evidence_factors"][0]["value"], "17 cái")
        self.assertIn("chưa đủ bằng chứng", data["explanation"])
        self.assertNotIn("2.5", str(data))
        self.assertNotIn("3 ngày", str(data))

    def test_no_entity_does_not_select_first_product(self):
        data = explain_root_cause(self.ws, self.user, target_type="STOCKOUT_WARNING")
        self.assertEqual(data["evidence_factors"], [])
        self.assertNotIn(self.product.name, data["explanation"])

    def test_missing_balance_is_not_reported_as_zero(self):
        StockBalance.objects.filter(product=self.product).delete()
        data = explain_root_cause(self.ws, self.user, target_type="STOCKOUT_WARNING", entity_id=self.product.pk)
        self.assertEqual(data["evidence_factors"], [])
        self.assertIn("Chưa có bản ghi tồn kho", data["explanation"])

    def test_duplicate_names_require_disambiguation(self):
        Product.objects.create(workspace=self.ws, category=self.product.category, name=self.product.name, sku="P2", unit_price=100)
        data = explain_root_cause(self.ws, self.user, target_type="STOCKOUT_WARNING", entity_name=self.product.name)
        self.assertEqual(data["evidence_factors"], [])

    def test_cross_workspace_and_missing_permission_denied(self):
        with self.assertRaises(ToolPermissionDenied):
            explain_root_cause(self.other, self.user, target_type="STOCKOUT_WARNING", entity_id=self.product.pk)
        with self.assertRaises(ToolPermissionDenied):
            explain_root_cause(self.ws, None, target_type="STOCKOUT_WARNING")

    def test_sla_and_recommendation_do_not_invent_measurements(self):
        for target in ("SLA_AT_RISK", "RECOMMENDATION"):
            data = explain_root_cause(self.ws, self.user, target_type=target)
            self.assertEqual(data["evidence_factors"], [])
            self.assertIn("chưa đủ bằng chứng", data["explanation"])
            for invented in ("40%", "20%", "4 giờ"):
                self.assertNotIn(invented, str(data))
