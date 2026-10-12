"""Canonical order failures remain safe UI responses, not partial mutations."""
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.audit.models import AuditLog
from apps.retail.models import Branch, Category, Customer, Order, OrderItem, Product, StockBalance
from apps.workspaces.models import Workspace, WorkspaceMembership


class OrderStatusUIRecoveryTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(code="status-ui", name="Status UI", workspace_type="RETAIL")
        self.manager = User.objects.create_user(username="status-ui-manager", email="status-ui@example.test", password=None)
        role = Role.objects.create(name="MANAGER")
        for codename in ("retail.view_order", "retail.manage_order"):
            permission, _ = Permission.objects.get_or_create(codename=codename, defaults={"name": codename, "module": "retail"})
            role.permissions.add(permission)
        self.role = role
        WorkspaceMembership.objects.create(user=self.manager, workspace=self.workspace, role=role, is_default=True)
        self.customer = Customer.objects.create(workspace=self.workspace, code="STATUS-C", name="TEST customer")
        self.branch = Branch.objects.create(workspace=self.workspace, code="STATUS-B", name="TEST branch")
        category = Category.objects.create(workspace=self.workspace, code="STATUS-CAT", name="TEST category")
        self.product = Product.objects.create(workspace=self.workspace, category=category, sku="STATUS-SKU", name="TEST product", unit_price=100)
        self.order = Order.objects.create(workspace=self.workspace, customer=self.customer, branch=self.branch,
            order_number="TEST-STATUS-UI", order_date=timezone.localdate(), order_timestamp=timezone.now())
        self.url = f"/noibo/retail/orders/{self.order.pk}/"
        self.client.force_login(self.manager)

    def assert_safe_failure(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Không thể cập nhật trạng thái đơn hàng", status_code=400)
        self.assertContains(response, 'role="alert"', status_code=400)
        self.assertNotContains(response, "Invalid order transition", status_code=400)

    def test_duplicate_confirmation_is_safe_and_does_not_repeat_domain_audit(self):
        self.assertEqual(self.client.post(self.url, {"action": "confirm"}).status_code, 302)
        self.assert_safe_failure(self.client.post(self.url, {"action": "confirm"}))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "CONFIRMED")
        self.assertEqual(AuditLog.objects.filter(action="ORDER_CONFIRMED", entity_id=str(self.order.pk)).count(), 1)

    def test_terminal_cancellation_cannot_release_stock_again(self):
        stock = StockBalance.objects.create(workspace=self.workspace, branch=self.branch, product=self.product, quantity_on_hand=5)
        self.order.status = "CANCELLED"
        self.order.fulfillment_stock_reserved = True
        self.order.fulfillment_stock_released_at = timezone.now()
        self.order.save()
        self.assert_safe_failure(self.client.post(self.url, {"action": "cancel"}))
        self.order.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELLED")
        self.assertEqual(stock.quantity_on_hand, 5)
        self.assertFalse(AuditLog.objects.filter(action="ORDER_FULFILLMENT_STOCK_RELEASED").exists())

    def test_unknown_action_is_rejected_without_a_false_success_redirect(self):
        self.assert_safe_failure(self.client.post(self.url, {"action": "ship-now"}))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")
        self.assertFalse(AuditLog.objects.filter(entity_type="Order", entity_id=str(self.order.pk)).exists())

    def test_missing_inventory_cancellation_remains_pending_without_partial_audit(self):
        self.order.fulfillment_stock_reserved = True
        self.order.save()
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, unit_price=100)
        self.assert_safe_failure(self.client.post(self.url, {"action": "cancel"}))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")
        self.assertIsNone(self.order.fulfillment_stock_released_at)
        self.assertFalse(AuditLog.objects.filter(action="ORDER_CANCELLED").exists())

    def test_validation_error_content_is_not_disclosed(self):
        with patch("apps.retail.ui_views.transition_order_status", side_effect=ValidationError("private-inventory-diagnostic")):
            response = self.client.post(self.url, {"action": "cancel"})
        self.assert_safe_failure(response)
        self.assertNotContains(response, "private-inventory-diagnostic", status_code=400)

    def test_foreign_workspace_order_stays_404_not_validation_failure(self):
        other = Workspace.objects.create(code="status-other", name="Other", workspace_type="RETAIL")
        customer = Customer.objects.create(workspace=other, code="OTHER-C", name="Other customer")
        order = Order.objects.create(workspace=other, customer=customer, order_number="TEST-FOREIGN-STATUS",
            order_date=timezone.localdate(), order_timestamp=timezone.now())
        response = self.client.post(f"/noibo/retail/orders/{order.pk}/", {"action": "cancel"})
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")

    def test_missing_management_permission_stays_403(self):
        self.role.permissions.remove(Permission.objects.get(codename="retail.manage_order"))
        self.assertEqual(self.client.post(self.url, {"action": "cancel"}).status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")
