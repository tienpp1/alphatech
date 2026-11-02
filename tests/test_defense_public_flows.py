"""Customer defense regressions; real CSRF/ownership, disposable TEST database."""
import json
import re

from django.test import Client, TestCase
from django.utils import timezone

from apps.retail.models import Category, Customer, Order, Product
from apps.workspaces.models import Workspace


class DefensePublicFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code="defense-public", name="Retail", workspace_type="RETAIL")
        category = Category.objects.create(workspace=cls.workspace, code="CABLE", name="Cable")
        cls.product = Product.objects.create(workspace=cls.workspace, category=category, sku="DEFENSE", name="TEST cable", unit_price=95000)
        customer = Customer.objects.create(workspace=cls.workspace, code="GUEST", name="TEST guest")
        cls.order = Order.objects.create(workspace=cls.workspace, customer=customer,
            order_number="ORD-20261102-GUEST", order_date=timezone.localdate(), order_timestamp=timezone.now(), total_amount=125000)

    def test_fresh_public_pages_bootstrap_csrf_for_guest_copilot(self):
        for path in ("/", "/san-pham/", "/dich-vu/", "/gioi-thieu/"):
            with self.subTest(path=path):
                browser = Client(enforce_csrf_checks=True)
                self.assertEqual(browser.get(path).status_code, 200)
                self.assertIn("csrftoken", browser.cookies)
                response = browser.post("/api/v1/public/copilot/", json.dumps({"message": "xin chào"}),
                    content_type="application/json", HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value)
                self.assertEqual(response.status_code, 200)
                self.assertIn("reply", response.json())

    def test_guest_drawer_updates_require_csrf_and_return_authoritative_cart(self):
        browser = Client(enforce_csrf_checks=True)
        browser.get("/san-pham/")
        self.assertIn("csrftoken", browser.cookies)
        token = browser.cookies["csrftoken"].value
        url = f"/gio-hang/them/{self.product.pk}/"
        self.assertEqual(browser.post(url, {"quantity": 1}).status_code, 403)
        response = browser.post(url, {"quantity": 1, "format": "json"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.json()["cart"]["total_amount"], 125000)
        update = f"/gio-hang/cap-nhat/{self.product.pk}/"
        self.assertEqual(browser.post(update, {"quantity": 9}).status_code, 403)
        response = browser.post(update, {"quantity": 2, "format": "json"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.json()["cart"]["total_amount"], 220000)
        self.assertEqual(browser.get("/gio-hang/api/?delivery_method=STORE_PICKUP").json()["total_amount"], 190000)

    def test_guest_tracking_link_preserves_session_ownership(self):
        browser = Client()
        session = browser.session
        session["public_order_success_numbers"] = [self.order.order_number]
        session.save()
        response = browser.post("/api/v1/public/copilot/", json.dumps({"message": f"tra cứu đơn hàng {self.order.order_number}"}), content_type="application/json")
        reply = response.json()["reply"]
        link = re.search(r"\[Chi tiết đơn hàng\]\(([^)]+)\)", reply).group(1)
        self.assertEqual(link, "/dat-hang-thanh-cong/ORD-20261102-GUEST/")
        self.assertEqual(browser.get(link).status_code, 200)
        self.assertEqual(Client().get(link).status_code, 404)
