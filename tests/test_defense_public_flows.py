"""Customer defense regressions; real CSRF/ownership, disposable TEST database."""
import json
import re
import threading
import time
from html.parser import HTMLParser
from unittest.mock import patch

from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.retail.models import Branch, Category, Customer, Order, Product, StockBalance
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

    def test_cart_add_get_is_read_only_and_post_still_requires_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        browser.get("/san-pham/")
        url = f"/gio-hang/them/{self.product.pk}/"
        response = browser.get(url, {"quantity": 9, "format": "json"})
        self.assertEqual(response.status_code, 405)
        self.assertNotIn("public_shopping_cart", browser.session)
        self.assertEqual(browser.post(url, {"quantity": 9}).status_code, 403)
        self.assertNotIn("public_shopping_cart", browser.session)


class CheckoutReviewFixtures:
    def setUp(self):
        self.workspace = Workspace.objects.create(code="review-retail", name="Retail", workspace_type="RETAIL")
        category = Category.objects.create(workspace=self.workspace, code="CABLE", name="Cable")
        self.product = Product.objects.create(workspace=self.workspace, category=category, sku="REVIEW", name="TEST cable", unit_price=95000)
        self.branch = Branch.objects.create(workspace=self.workspace, code="REVIEW", name="TEST branch")
        self.stock = StockBalance.objects.create(workspace=self.workspace, product=self.product, branch=self.branch, quantity_on_hand=10)
        self.browser = Client()
        self.browser.post(f"/gio-hang/them/{self.product.pk}/", {"quantity": 1})
        self.form = {"name": "TEST recipient", "phone": "0900000000", "email": "review@example.test",
                     "address": "TEST address", "delivery_method": "STORE_PICKUP", "branch_id": self.branch.pk}

    def review(self, browser=None, method="STORE_PICKUP"):
        response = (browser or self.browser).get("/thanh-toan/", {"delivery_method": method})
        self.assertEqual(response.status_code, 200)
        token = response.context.get("checkout_review_token")
        self.assertTrue(token, "Actual checkout must issue a signed review token")
        return token

    def assert_no_business_writes(self):
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 10)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)


class DefenseCheckoutReviewTests(CheckoutReviewFixtures, TestCase):
    def test_strict_empty_cart_rejection_preserves_draft_and_disables_review(self):
        for unavailable in ("removed", "inactive", "missing_token"):
            with self.subTest(unavailable=unavailable):
                Product.objects.filter(pk=self.product.pk).update(is_active=True)
                session = self.browser.session
                session["public_shopping_cart"] = {str(self.product.pk): 1}
                session.save()
                token = self.review()
                if unavailable == "inactive":
                    Product.objects.filter(pk=self.product.pk).update(is_active=False)
                else:
                    self.browser.post(f"/gio-hang/cap-nhat/{self.product.pk}/", {"quantity": 0})
                draft = {**self.form, "name": 'TEST <img src=x onerror="alert(1)">',
                         "city": "TEST city", "district": "TEST district", "notes": "TEST notes"}
                data = dict(draft)
                if unavailable != "missing_token":
                    data["checkout_review_token"] = token
                response = self.browser.post("/thanh-toan/dat-hang/?review=1", data)
                self.assertEqual(response.status_code, 409)
                self.assert_no_business_writes()
                for context_key, field in (("customer_name", "name"), ("customer_phone", "phone"),
                        ("customer_email", "email"), ("customer_address", "address"), ("customer_city", "city"),
                        ("customer_district", "district"), ("customer_notes", "notes"), ("delivery_method", "delivery_method")):
                    self.assertEqual(response.context[context_key], draft[field])
                self.assertEqual(response.context["selected_branch_id"], str(self.branch.pk))
                self.assertEqual(response.context["items"], [])
                self.assertEqual(response.context["summary"]["total_amount"], 0)
                self.assertEqual(response.context["checkout_review_token"], "")
                self.assertIn("giỏ hàng", response.context["error_message"].lower())
                self.assertContains(response, '&lt;img src=x', status_code=409)
                self.assertNotContains(response, '<img src=x onerror=', status_code=409)
                fields = {}
                class Fields(HTMLParser):
                    def handle_starttag(self, tag, attrs):
                        attrs = dict(attrs)
                        if attrs.get("id"):
                            fields[attrs["id"]] = attrs
                Fields().feed(response.content.decode())
                self.assertIn("disabled", fields["btn-place-order"])
                self.assertEqual(fields["checkout-review-token"]["value"], "")

    def test_legacy_unsigned_empty_post_still_redirects_without_business_writes(self):
        self.browser.post(f"/gio-hang/cap-nhat/{self.product.pk}/", {"quantity": 0})
        response = self.browser.post("/thanh-toan/dat-hang/", self.form)
        self.assertRedirects(response, "/gio-hang/", fetch_redirect_response=False)
        self.assert_no_business_writes()

    def test_stale_review_renders_409_with_safe_draft_and_updated_review(self):
        token = self.review()
        Product.objects.filter(pk=self.product.pk).update(unit_price=120000)
        draft = {**self.form, "name": 'TEST <img src=x onerror="alert(1)">',
                 "city": "TEST city", "district": "TEST district", "notes": "TEST instructions"}
        response = self.browser.post("/thanh-toan/dat-hang/?review=1", {**draft, "checkout_review_token": token})
        self.assertEqual(response.status_code, 409)
        self.assert_no_business_writes()
        for context_key, field in (("customer_name", "name"), ("customer_phone", "phone"), ("customer_email", "email"),
                ("customer_address", "address"), ("customer_city", "city"), ("customer_district", "district"),
                ("customer_notes", "notes"), ("delivery_method", "delivery_method")):
            self.assertEqual(response.context[context_key], draft[field])
        self.assertEqual(response.context["selected_branch_id"], str(self.branch.pk))
        self.assertContains(response, '&lt;img src=x', status_code=409)
        self.assertNotContains(response, '<img src=x onerror=', status_code=409)
        self.assertIn("xem lại", response.context["error_message"].lower())
        self.assertTrue(response.context["checkout_review_token"])
        self.assertNotEqual(response.context["checkout_review_token"], token)
        self.assertEqual(response.context["summary"]["total_amount"], 120000)

    def test_actual_form_requires_token_even_if_late_session_save_loses_issued_marker(self):
        self.review()
        session = self.browser.session
        session.pop("public_checkout_review_required", None)
        session.save()
        response = self.browser.post("/thanh-toan/dat-hang/?review=1", self.form)
        self.assertEqual(response.status_code, 409)
        self.assert_no_business_writes()
        self.assertIn("xem lại", response.context["error_message"].lower())

    def test_actual_ui_missing_or_malformed_token_never_writes(self):
        self.review()
        for value in (None, "", "not-signed", "x" * 20000):
            with self.subTest(token_kind="missing" if value is None else len(value)):
                data = dict(self.form)
                if value is not None:
                    data["checkout_review_token"] = value
                self.browser.post("/thanh-toan/dat-hang/?review=1", data)
                self.assert_no_business_writes()

    def test_locked_live_price_change_rejects_old_review_before_stock_or_customer(self):
        token = self.review()
        Product.objects.filter(pk=self.product.pk).update(unit_price=120000)
        self.browser.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token})
        self.assert_no_business_writes()

    def test_review_is_bound_to_server_delivery_method(self):
        token = self.review(method="HOME_DELIVERY")
        self.browser.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token})
        self.assert_no_business_writes()

    def test_review_cannot_be_used_in_another_browser_session(self):
        token = self.review()
        outsider = Client()
        outsider.post(f"/gio-hang/them/{self.product.pk}/", {"quantity": 1})
        outsider.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token})
        self.assert_no_business_writes()

    def test_review_expires_without_business_writes(self):
        with patch("django.core.signing.time.time", return_value=time.time() - 1900):
            token = self.review()
        self.browser.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token})
        self.assert_no_business_writes()

    def test_unchanged_review_places_exact_snapshot_and_ignores_posted_totals(self):
        token = self.review()
        response = self.browser.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token,
            "total_amount": 1, "unit_price": 1})
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.total_amount, 95000)
        self.assertEqual(order.items.get().quantity, 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 9)

    def test_authoritative_get_issues_review_for_selected_method(self):
        self.review()
        response = self.browser.get("/gio-hang/api/", {"delivery_method": "STORE_PICKUP", "review": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("checkout_review_token"))
        self.assertEqual(response.json()["total_amount"], 95000)

    def test_review_get_does_not_save_existing_empty_or_stale_session(self):
        for stale in (False, True):
            browser = Client()
            session = browser.session
            if stale:
                session["public_shopping_cart"] = {str(self.product.pk): 1}
                Product.objects.filter(pk=self.product.pk).update(is_active=False)
            session.save()
            saved = []
            original_save = SessionStore.save
            def record_save(session, *args, **kwargs):
                saved.append(True)
                return original_save(session, *args, **kwargs)
            with patch.object(SessionStore, "save", record_save):
                response = browser.get("/gio-hang/api/", {"review": "1"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["items"], [])
            self.assertEqual(saved, [], "Read-only cart review cannot save its old session snapshot")
            if stale:
                self.assertEqual(browser.session["public_shopping_cart"], {str(self.product.pk): 1})

    def test_empty_first_review_get_does_not_create_session_or_usable_token(self):
        browser = Client()
        response = browser.get("/gio-hang/api/", {"review": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sessionid", browser.cookies)
        self.assertFalse(response.json().get("checkout_review_token"))


class DefenseCheckoutLateSessionTests(CheckoutReviewFixtures, TransactionTestCase):
    def test_old_review_get_cannot_save_over_a_newer_confirmed_cart_post(self):
        """Let an old GET reach session persistence, then complete a newer POST."""
        reader_ready, release_save = threading.Event(), threading.Event()
        errors, results, saves = [], [], []
        reader = Client()
        reader.cookies = self.browser.cookies.copy()
        original_save = SessionStore.save

        def delayed_save(session, *args, **kwargs):
            if threading.current_thread().name == "old-review-reader":
                saves.append(True)
                reader_ready.set()
                if not release_save.wait(15):
                    raise RuntimeError("TEST reader save release timeout")
            return original_save(session, *args, **kwargs)

        def read():
            from django.db import close_old_connections
            close_old_connections()
            try:
                results.append(reader.get("/gio-hang/api/", {"review": "1"}).json())
            except Exception as exc:
                errors.append(exc)
            finally:
                reader_ready.set()  # Fixed path finishes without any save.
                close_old_connections()

        with patch.object(SessionStore, "save", delayed_save):
            thread = threading.Thread(target=read, name="old-review-reader")
            thread.start()
            try:
                self.assertTrue(reader_ready.wait(15))
                updated = self.browser.post(f"/gio-hang/cap-nhat/{self.product.pk}/", {"quantity": 2, "format": "json"})
                self.assertEqual(updated.json()["cart"]["total_quantity"], 2)
            finally:
                release_save.set()
                thread.join(15)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results[0]["total_quantity"], 1)
        self.assertEqual(self.browser.get("/gio-hang/api/").json()["total_quantity"], 2)
        self.assertEqual(saves, [])

    def test_late_aborted_post_saves_after_old_get_then_placement_rejects_review(self):
        """Pause actual mutation session persistence, not merely its JS response."""
        save_reached, release_save = threading.Event(), threading.Event()
        errors = []
        writer = Client()
        writer.cookies = self.browser.cookies.copy()
        original_save = SessionStore.save

        def delayed_save(session, *args, **kwargs):
            if threading.current_thread().name == "late-cart-writer":
                save_reached.set()
                if not release_save.wait(15):
                    raise RuntimeError("TEST late save release timeout")
            return original_save(session, *args, **kwargs)

        def mutate():
            from django.db import close_old_connections
            close_old_connections()
            try:
                writer.post(f"/gio-hang/cap-nhat/{self.product.pk}/", {"quantity": 2, "format": "json"})
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        with patch.object(SessionStore, "save", delayed_save):
            thread = threading.Thread(target=mutate, name="late-cart-writer")
            thread.start()
            try:
                self.assertTrue(save_reached.wait(15))
                page = self.browser.get("/thanh-toan/", {"delivery_method": "STORE_PICKUP"})
                self.assertEqual(page.status_code, 200)
                token = page.context.get("checkout_review_token") or "unsigned-before-repair"
                old = self.browser.get("/gio-hang/api/", {"delivery_method": "STORE_PICKUP", "review": "1"}).json()
                self.assertEqual(old["total_quantity"], 1)
                token = old.get("checkout_review_token") or token
            finally:
                release_save.set()
                thread.join(15)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.browser.get("/gio-hang/api/").json()["total_quantity"], 2)
        self.browser.post("/thanh-toan/dat-hang/?review=1", {**self.form, "checkout_review_token": token})
        self.assert_no_business_writes()
