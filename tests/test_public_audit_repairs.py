"""Public audit regressions: real isolated DB; provider sends remain simulated."""
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import hashlib
import json
from pathlib import Path
import time
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core import signing
from django.core.management import call_command, CommandError
from django.db import close_old_connections, connections, connection
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.public_web import customer_identity
from apps.audit.models import AuditLog
from apps.public_web.models import CustomerEmailDelivery, OrderDeliveryAddress
from apps.retail.models import Category, Customer, Order, Product, ProductImage
from apps.service_ops.models import Service, ServiceRequest
from apps.workspaces.models import Workspace


class PublicCheckoutLayoutContractTests(SimpleTestCase):
    def test_header_brand_text_shrinks_without_compressing_logo_or_overlapping_cart(self):
        # Source regression; actual mobile geometry is measured in browser QA.
        template = (Path(settings.BASE_DIR) / "templates/public/base_public.html").read_text(encoding="utf-8")
        self.assertRegex(template, r"\.pub-brand-text\s*\{[^}]*min-width:\s*0;")
        self.assertRegex(template, r"\.pub-brand-logo\s*\{[^}]*flex-shrink:\s*0;")
        self.assertRegex(template, r"\.pub-brand-title\s*\{[^}]*text-overflow:\s*ellipsis;")

    def test_public_stylesheet_uses_configured_static_storage(self):
        template = (Path(settings.BASE_DIR) / "templates/public/base_public.html").read_text(encoding="utf-8")
        self.assertIn("{% load static %}", template)
        self.assertIn("{% static 'css/public_pages.css' %}", template)
        self.assertNotIn('href="/static/css/public_pages.css"', template)

    def test_checkout_intrinsic_widths_can_shrink_without_clipping_content(self):
        # This asserts the source contract, not a substitute for viewport QA.
        css = (Path(settings.BASE_DIR) / "static/css/public_pages.css").read_text(encoding="utf-8")
        for rule in (
            "grid-template-columns: minmax(0, 1.8fr) minmax(0, 1.2fr);",
            ".checkout-grid-layout > *,",
            ".checkout-delivery-switcher > * {\n    min-width: 0;",
            ".checkout-grid-layout .pub-form-control,",
            ".checkout-delivery-card > div {\n    min-width: 0;\n    overflow-wrap: anywhere;",
            "grid-template-columns: minmax(0, 1fr) !important;",
        ):
            self.assertIn(rule, css)


class PublicOrderRecipientSnapshotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code="snapshot-retail", name="Retail", workspace_type="RETAIL")
        cls.owner = get_user_model().objects.create_user(username="snapshot-owner", email="owner@example.test")
        cls.other = get_user_model().objects.create_user(username="snapshot-other", email="other@example.test")
        cls.customer = Customer.objects.create(workspace=cls.workspace, user=cls.owner, code="PROFILE",
            name="Tên hồ sơ hiện tại", phone="0999000001", email="profile@example.test")
        cls.order = Order.objects.create(workspace=cls.workspace, customer=cls.customer, created_by=cls.owner,
            order_number="ORD-SNAPSHOT-TEST", order_date=timezone.localdate(), order_timestamp=timezone.now())
        cls.snapshot = OrderDeliveryAddress.objects.create(order=cls.order, recipient_name="Người nhận lúc đặt",
            phone="0888000002", email="delivery@example.test", address_line="12 Đường Giao Nhận",
            district="Quận Kiểm Thử", city="Thành Phố Kiểm Thử", delivery_method="HOME_DELIVERY")
        cls.legacy = Order.objects.create(workspace=cls.workspace, customer=cls.customer, created_by=cls.owner,
            order_number="ORD-LEGACY-TEST", order_date=timezone.localdate(), order_timestamp=timezone.now())

    def paths(self, order=None):
        number = (order or self.order).order_number
        return (f"/dat-hang-thanh-cong/{number}/", f"/tai-khoan/don-hang/{number}/")

    def test_both_views_use_snapshot_even_after_customer_profile_changes(self):
        self.client.force_login(self.owner)
        Customer.objects.filter(pk=self.customer.pk).update(name="Hồ sơ đã đổi", phone="0777000003", email="changed@example.test")
        for path in self.paths():
            response = self.client.get(path)
            for value in ("Người nhận lúc đặt", "0888000002", "delivery@example.test",
                          "12 Đường Giao Nhận, Quận Kiểm Thử, Thành Phố Kiểm Thử", "Giao hàng tận nơi"):
                self.assertContains(response, value)
            for value in ("Hồ sơ đã đổi", "0777000003", "changed@example.test"):
                self.assertNotContains(response, value)
            self.assertEqual(response.context["delivery_address"].pk, self.snapshot.pk)

    def test_blank_snapshot_contact_does_not_fallback_to_customer_fields(self):
        self.client.force_login(self.owner)
        OrderDeliveryAddress.objects.filter(pk=self.snapshot.pk).update(phone="", email="", address_line="", district="", city="")
        for path in self.paths():
            response = self.client.get(path)
            self.assertContains(response, "Chưa cung cấp")
            self.assertNotContains(response, self.customer.phone)
            self.assertNotContains(response, self.customer.email)

    def test_legacy_order_without_snapshot_preserves_customer_fallback(self):
        self.client.force_login(self.owner)
        for path in self.paths(self.legacy):
            response = self.client.get(path)
            for value in (self.customer.name, self.customer.phone, self.customer.email):
                self.assertContains(response, value)
            self.assertIsNone(response.context["delivery_address"])

    def test_another_authenticated_customer_cannot_read_snapshot(self):
        self.client.force_login(self.other)
        for path in self.paths():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(self.snapshot.email, response.content.decode())

    def test_guest_snapshot_is_visible_only_to_owning_browser_session(self):
        guest = Order.objects.create(workspace=self.workspace, customer=self.customer,
            order_number="ORD-GUEST-SNAPSHOT", order_date=timezone.localdate(), order_timestamp=timezone.now())
        OrderDeliveryAddress.objects.create(order=guest, recipient_name="TEST guest recipient", phone="0666000004",
            email="guest-delivery@example.test", delivery_method="STORE_PICKUP")
        success, detail = self.paths(guest)
        self.assertEqual(self.client.get(success).status_code, 404)
        session = self.client.session
        session["public_order_success_numbers"] = [guest.order_number]
        session.save()
        self.assertContains(self.client.get(success), "guest-delivery@example.test")
        self.assertContains(self.client.get(success), "Nhận tại chi nhánh")
        self.assertEqual(Client().get(success).status_code, 404)
        self.assertEqual(self.client.get(detail).status_code, 302)

    def test_snapshot_content_is_escaped_in_both_views(self):
        self.client.force_login(self.owner)
        attack = '<script>alert("unsafe")</script>'
        OrderDeliveryAddress.objects.filter(pk=self.snapshot.pk).update(recipient_name=attack, address_line=attack)
        for path in self.paths():
            response = self.client.get(path)
            self.assertContains(response, "&lt;script&gt;")
            self.assertNotContains(response, attack)

    def test_reading_both_views_never_rewrites_profile_snapshot_or_notes(self):
        self.client.force_login(self.owner)
        snapshot_before = OrderDeliveryAddress.objects.get(pk=self.snapshot.pk).__dict__.copy()
        customer_before = Customer.objects.get(pk=self.customer.pk).__dict__.copy()
        notes_before = self.order.notes
        for path in self.paths():
            self.assertEqual(self.client.get(path).status_code, 200)
        snapshot_after = OrderDeliveryAddress.objects.get(pk=self.snapshot.pk).__dict__.copy()
        customer_after = Customer.objects.get(pk=self.customer.pk).__dict__.copy()
        for values in (snapshot_before, snapshot_after, customer_before, customer_after):
            values.pop("_state")
        self.assertEqual(snapshot_before, snapshot_after)
        self.assertEqual(customer_before, customer_after)
        self.order.refresh_from_db()
        self.assertEqual(self.order.notes, notes_before)


class PublicServicePriorityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code="priority-service", name="Service", workspace_type="SERVICE")
        cls.service = Service.objects.create(workspace=cls.workspace, code="TEST", name="TEST support")
        cls.owner = get_user_model().objects.create_user(username="priority-owner", email="priority-owner@example.test")

    def payload(self, **changes):
        return {"customer_name": "Khách ưu tiên TEST", "phone": "0999000001", "email": "form-priority@example.test",
                "service_id": str(self.service.pk), "description": "Mô tả riêng TEST", **changes}

    def old_key(self, data):
        material = [f"user:{self.owner.pk}", str(self.service.pk), data["customer_name"], data["email"].casefold(),
                    data["phone"], data["description"], data.get("address", ""), data.get("preferred_time", "")]
        if data.get("submission_token"):
            material.append(signing.loads(data["submission_token"], salt="public_web.service_submission.v1", max_age=3600))
        return "REQ-PUB-" + hashlib.sha256(json.dumps(material, ensure_ascii=False).encode()).hexdigest()[:40].upper()

    def test_rendered_default_is_p2_medium(self):
        response = self.client.get("/yeu-cau-dich-vu/")
        self.assertEqual(response.context["selected_priority"], "MEDIUM")
        self.assertContains(response, 'id="service-priority" name="priority" value="MEDIUM"')
        self.assertContains(response, 'class="priority-card selected" id="pcard-p2"')
        self.assertContains(response, "Ưu tiên P2: Ví dụ mô phỏng 30 phút")

    def test_valid_priorities_are_recorded_without_sla_deadline_or_dispatch(self):
        self.client.force_login(self.owner)
        for priority in ("HIGH", "MEDIUM", "LOW"):
            response = self.client.post("/yeu-cau-dich-vu/", self.payload(priority=priority))
            self.assertEqual(response.status_code, 302)
            request = ServiceRequest.objects.get(priority=priority)
            self.assertEqual(request.workspace, self.workspace)
            self.assertEqual(request.status, "OPEN")
            self.assertIsNone(request.sla_id)
            self.assertIsNone(request.assigned_employee_id)
            self.assertIsNone(request.response_deadline_at)
            self.assertIsNone(request.resolution_deadline_at)
            self.assertIsNone(request.scheduled_at)
            self.assertEqual(request.tasks.count(), 0)
            audit = AuditLog.objects.get(action="REQUEST_CREATED", entity_id=str(request.pk))
            self.assertEqual(audit.workspace, self.workspace)
            self.assertEqual(audit.actor_user, self.owner)
            self.assertEqual(audit.changes["priority"], priority)
            metadata = json.dumps(audit.changes)
            for private in ("Khách ưu tiên TEST", "0999000001", "form-priority@example.test", "Mô tả riêng TEST"):
                self.assertNotIn(private, metadata)
        self.assertEqual(ServiceRequest.objects.count(), 3)
        self.assertFalse(self.owner.workspace_memberships.exists())

    def test_invalid_priority_is_rejected_before_any_record_or_delivery(self):
        for priority in ("", "CRITICAL", "P3", "low", "1", "<script>"):
            response = self.client.post("/yeu-cau-dich-vu/", self.payload(priority=priority))
            self.assertContains(response, "Mức ưu tiên không hợp lệ")
            self.assertEqual(response.context["selected_priority"], "MEDIUM")
        self.assertFalse(ServiceRequest.objects.exists())
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="REQUEST_CREATED").exists())

    def test_legacy_missing_and_explicit_medium_keep_identical_pre_release_key(self):
        self.client.force_login(self.owner)
        data = self.payload()
        expected = self.old_key(data)
        self.client.post("/yeu-cau-dich-vu/", data)
        self.client.post("/yeu-cau-dich-vu/", {**data, "priority": "MEDIUM"})
        self.assertEqual(ServiceRequest.objects.get().request_number, expected)
        self.assertEqual(ServiceRequest.objects.get().priority, "MEDIUM")
        self.assertEqual(AuditLog.objects.filter(action="REQUEST_CREATED").count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.count(), 2)
        self.assertSetEqual(set(CustomerEmailDelivery.objects.values_list("recipient", flat=True)),
                            {self.owner.email, data["email"]})

    def test_signed_medium_retry_reuses_pre_release_request_without_retrofit(self):
        self.client.force_login(self.owner)
        token = self.client.get("/yeu-cau-dich-vu/").context["submission_token"]
        data = self.payload(submission_token=token, address="Địa chỉ TEST", preferred_time="2026-10-20T09:00")
        customer = customer_identity.customer_for_submission(workspace=self.workspace, user=self.owner, name="Old profile")
        old = ServiceRequest.objects.create(workspace=self.workspace, request_number=self.old_key(data), customer=customer,
            service=self.service, title="Old persisted title", description="Old persisted description", priority="MEDIUM")
        before = (old.title, old.description, old.priority, old.updated_at)
        self.assertEqual(self.client.post("/yeu-cau-dich-vu/", {**data, "priority": "MEDIUM"}).status_code, 302)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        old.refresh_from_db()
        self.assertEqual((old.title, old.description, old.priority, old.updated_at), before)
        self.assertFalse(AuditLog.objects.filter(action="REQUEST_CREATED").exists())

    def test_audit_failure_rolls_back_request_customer_and_outbox(self):
        with patch("apps.public_web.views.log_action", side_effect=RuntimeError("TEST audit unavailable")):
            response = self.client.post("/yeu-cau-dich-vu/", self.payload(priority="LOW"))
        self.assertContains(response, "Không thể ghi nhận yêu cầu lúc này")
        self.assertFalse(ServiceRequest.objects.exists())
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())

    def test_validation_error_retains_the_valid_priority_selection(self):
        response = self.client.post("/yeu-cau-dich-vu/", self.payload(priority="LOW", email="bad-email"))
        self.assertContains(response, 'id="service-priority" name="priority" value="LOW"')
        self.assertContains(response, 'class="priority-card selected" id="pcard-p3"')
        self.assertFalse(ServiceRequest.objects.exists())


class PublicAuditRepairTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.retail = Workspace.objects.create(code="audit-public-retail", name="Retail", workspace_type="RETAIL")
        cls.service_ws = Workspace.objects.create(code="audit-public-service", name="Service", workspace_type="SERVICE")
        cls.service = Service.objects.create(workspace=cls.service_ws, code="SUPPORT", name="Kiểm tra thiết bị")
        laptop = Category.objects.create(workspace=cls.retail, code="LAPTOP", name="Laptop")
        accessories = Category.objects.create(workspace=cls.retail, code="CABLE", name="Thiết bị mạng")
        cls.cheap_laptop = Product.objects.create(workspace=cls.retail, category=laptop, sku="LAP-14", name="Laptop Dell 14", unit_price=14000000)
        cls.expensive_laptop = Product.objects.create(workspace=cls.retail, category=laptop, sku="LAP-20", name="Laptop Dell 20", unit_price=20000000)
        cls.cable = Product.objects.create(workspace=cls.retail, category=accessories, sku="UG-CAT6", name="Cáp mạng Ugreen Cat6", unit_price=95000)
        cls.user = get_user_model().objects.create_user(username="audit-public-owner", email="owner@example.com")
        cls.other_user = get_user_model().objects.create_user(username="audit-public-other", email="other@example.com")

    def payload(self, **extra):
        return dict(customer_name="Khách kiểm thử", phone="0900000000", email="form@example.com",
                    service_id=str(self.service.pk), description="Kiểm tra thiết bị TEST", **extra)

    def token(self, client=None):
        return (client or self.client).get("/yeu-cau-dich-vu/").context["submission_token"]

    def ask(self, message):
        response = self.client.post("/api/v1/public/copilot/", json.dumps({"message": message}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        return response.json()["reply"]

    def test_laptop_budget_never_substitutes_accessories(self):
        reply = self.ask("Tôi muốn laptop văn phòng dưới 15 triệu")
        self.assertIn(self.cheap_laptop.name, reply)
        self.assertNotIn(self.expensive_laptop.name, reply)
        self.assertNotIn(self.cable.name, reply)
        no_match = self.ask("Laptop dưới 5 triệu")
        self.assertIn("Chưa tìm thấy sản phẩm", no_match)
        self.assertNotIn(self.cable.name, no_match)

    def test_exact_network_product_does_not_route_to_service(self):
        other = Product.objects.create(workspace=self.retail, category=self.cable.category,
                                       sku="UG-CAT5", name="Cáp mạng Ugreen Cat5", unit_price=50000)
        reply = self.ask("Cáp mạng Ugreen Cat6 giá bao nhiêu?")
        self.assertIn(self.cable.name, reply)
        self.assertIn("95.000₫", reply)
        self.assertNotIn("Các gói dịch vụ tiêu biểu", reply)
        self.assertNotIn(self.cheap_laptop.name, reply)
        self.assertNotIn(other.name, reply)

    def test_ordering_howto_and_compound_policy_answers(self):
        self.assertIn("/thanh-toan/", self.ask("Mua hàng như thế nào?"))
        reply = self.ask("Có ISO 27001, hóa đơn VAT và trả góp không?")
        for required in ("ISO 27001", "hóa đơn VAT", "Thông tin mua trả góp", "chưa có"):
            self.assertIn(required, reply)
        self.assertNotIn("Lãi suất 0%", reply)

    def test_empty_and_stale_cart_do_not_charge_shipping(self):
        response = self.client.get("/gio-hang/api/").json()
        self.assertEqual(response["shipping_fee"], 0)
        self.assertEqual(response["total_amount"], 0)
        session = self.client.session
        session["public_shopping_cart"] = {str(self.cheap_laptop.pk): 1}
        session.save()
        self.cheap_laptop.is_active = False
        self.cheap_laptop.save(update_fields=["is_active"])
        response = self.client.get("/gio-hang/api/").json()
        self.assertEqual(response["items_count"], 0)
        self.assertEqual(response["shipping_fee"], 0)
        self.assertEqual(response["total_amount"], 0)

    def test_service_validation_has_no_customer_or_email_side_effect(self):
        for value in ("", "abc", "99999999999999999999999999999999", str(self.service.pk + 9999)):
            data = self.payload()
            data["service_id"] = value
            response = self.client.post("/yeu-cau-dich-vu/", data)
            self.assertEqual(response.status_code, 200)
            self.assertIn("dịch vụ", response.context["error_message"])
        for email in ("bad-email", "bad@@example.com"):
            data = self.payload()
            data["email"] = email
            response = self.client.post("/yeu-cau-dich-vu/", data)
            self.assertContains(response, "Địa chỉ email không hợp lệ")
            self.assertEqual(response.context["form_data"]["description"], data["description"])
        self.assertFalse(ServiceRequest.objects.exists())
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())

    def test_inactive_and_retail_services_are_not_accepted(self):
        self.service.is_active = False
        self.service.save(update_fields=["is_active"])
        self.assertContains(self.client.post("/yeu-cau-dich-vu/", self.payload()), "không hợp lệ")
        foreign = Service.objects.create(workspace=self.retail, code="NOT-PUBLIC", name="Wrong workspace")
        data = self.payload()
        data["service_id"] = str(foreign.pk)
        self.assertContains(self.client.post("/yeu-cau-dich-vu/", data), "không hợp lệ")
        self.assertFalse(ServiceRequest.objects.exists())
        self.service.is_active = True
        self.service.save(update_fields=["is_active"])
        self.service_ws.is_active = False
        self.service_ws.save(update_fields=["is_active"])
        self.assertContains(self.client.post("/yeu-cau-dich-vu/", self.payload()), "không hợp lệ")
        self.assertFalse(ServiceRequest.objects.exists())

    def test_signed_submission_double_post_and_get_refresh_create_one_request(self):
        data = self.payload(submission_token=self.token())
        with patch("apps.public_web.views.dispatch_new_service_request_notification") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post("/yeu-cau-dich-vu/", data)
            self.assertRedirects(response, "/yeu-cau-dich-vu/", fetch_redirect_response=False)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/yeu-cau-dich-vu/", data)
            self.assertEqual(notify.call_count, 1)
        self.assertContains(self.client.get("/yeu-cau-dich-vu/"), "tiếp nhận thành công")
        self.client.get("/yeu-cau-dich-vu/")
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.filter(event_type="SERVICE_REQUEST").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="REQUEST_CREATED", entity_type="ServiceRequest").count(), 1)

    def test_new_form_nonce_allows_intentional_identical_request(self):
        self.client.post("/yeu-cau-dich-vu/", self.payload(submission_token=self.token()))
        self.client.post("/yeu-cau-dich-vu/", self.payload(submission_token=self.token()))
        self.assertEqual(ServiceRequest.objects.count(), 2)

    def test_request_key_never_attaches_another_account_or_guest(self):
        nonce = self.token()
        for user in (self.user, self.other_user):
            self.client.force_login(user)
            data = self.payload(submission_token=nonce)
            data["email"] = ""
            self.assertEqual(self.client.post("/yeu-cau-dich-vu/", data).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.post("/yeu-cau-dich-vu/", self.payload(submission_token=nonce)).status_code, 302)
        self.assertEqual(ServiceRequest.objects.count(), 3)
        self.assertSetEqual(set(Customer.objects.values_list("user_id", flat=True)), {self.user.pk, self.other_user.pk, None})
        for inquiry in ServiceRequest.objects.select_related("customer"):
            self.assertEqual(inquiry.workspace_id, inquiry.customer.workspace_id)

    def test_tampered_nonce_is_rejected_before_side_effects(self):
        self.assertContains(self.client.post("/yeu-cau-dich-vu/", self.payload(submission_token="tampered")), "Phiên gửi yêu cầu")
        self.assertFalse(ServiceRequest.objects.exists())

    def test_expired_nonce_is_rejected_before_side_effects(self):
        token = self.token()
        with patch("django.core.signing.time.time", return_value=time.time() + 3602):
            response = self.client.post("/yeu-cau-dich-vu/", self.payload(submission_token=token))
            self.assertContains(response, "Phiên gửi yêu cầu")
            self.assertNotEqual(response.context["submission_token"], token)
        self.assertFalse(ServiceRequest.objects.exists())

    def test_contact_acknowledgment_does_not_promise_unapproved_sla(self):
        response = self.client.post("/lien-he/", {"name": "Khách", "email": "contact@example.com", "message": "TEST"})
        self.assertContains(response, "Tin nhắn đã được ghi nhận")
        self.assertNotIn("24 giờ", response.context["success_message"])

    def test_missing_product_photo_is_explicit_and_cart_launcher_is_inline(self):
        for url in ("/san-pham/", f"/san-pham/{self.cable.pk}/"):
            response = self.client.get(url)
            self.assertContains(response, "Chưa có ảnh sản phẩm")
            self.assertContains(response, "Ảnh minh họa AI — không phải ảnh sản phẩm thực tế")
            self.assertContains(response, "public/images/technology-illustration-ai-v1.png")
        self.assertFalse(ProductImage.objects.exists())
        response = self.client.get("/gio-hang/")
        self.assertContains(response, 'class="copilot-inline-launcher"')
        self.assertNotContains(response, 'class="copilot-launcher"')
        self.assertContains(response, 'class="page-hero-container"')

    def test_actual_product_image_takes_precedence_over_ai_illustration(self):
        # A test-only DB reference is enough; no file or production media is written.
        ProductImage.objects.create(workspace=self.retail, product=self.cable,
                                    image="products/test-actual-cat6.jpg", is_primary=True)
        response = self.client.get(f"/san-pham/{self.cable.pk}/")
        self.assertContains(response, "products/test-actual-cat6.jpg")
        self.assertNotContains(response, "public/images/technology-illustration-ai-v1.png")
        self.assertNotContains(response, "Ảnh minh họa AI — không phải ảnh sản phẩm thực tế")

    def test_public_hero_content_is_not_inside_inert_decorative_grid(self):
        for url in ("/gioi-thieu/", "/lien-he/", "/san-pham/", "/dich-vu/", "/yeu-cau-dich-vu/"):
            response = self.client.get(url)
            self.assertContains(response, '<div class="page-hero-grid" aria-hidden="true"></div>')
            self.assertContains(response, 'class="page-hero-container"')

    @override_settings(HOME_DELIVERY_FULFILLMENT_POLICY="legacy", HOME_DELIVERY_DEFAULT_BRANCH_CODE="BR-D1", HOME_DELIVERY_FALLBACK_BRANCH_CODES=())
    def test_preflight_strict_fails_closed_without_changing_data_or_policy(self):
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("check_fulfillment_stock", workspace=self.retail.code, strict=True, stdout=output)
        report = json.loads(output.getvalue())
        self.assertFalse(report["data_complete"])
        self.assertEqual(report["policy"], "legacy")
        self.assertEqual(Product.objects.count(), 3)


class PublicServiceConcurrencyRepairTests(TransactionTestCase):
    def test_duplicate_guest_posts_rollback_losing_customer(self):
        self.assertEqual(connection.vendor, "postgresql")
        workspace = Workspace.objects.create(code="service-post-race", name="Service", workspace_type="SERVICE")
        service = Service.objects.create(workspace=workspace, code="RACE", name="TEST")
        original = Client()
        token = original.get("/yeu-cau-dich-vu/").context["submission_token"]
        clients = [Client(), Client()]
        for client in clients:
            client.cookies = original.cookies.copy()
        barrier = Barrier(2, timeout=15)
        real_customer = customer_identity.customer_for_submission
        def synchronized_customer(**kwargs):
            customer = real_customer(**kwargs)
            barrier.wait()
            return customer
        def submit(client):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '15s'")
                    cursor.execute("SET statement_timeout = '20s'")
                return client.post("/yeu-cau-dich-vu/", dict(customer_name="TEST", phone="0900000000", email="race@example.com",
                    service_id=str(service.pk), description="TEST race", submission_token=token)).status_code
            finally:
                connections.close_all()
        with patch.object(customer_identity, "customer_for_submission", side_effect=synchronized_customer):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, clients))
        self.assertEqual(results, [302, 302])
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.filter(event_type="SERVICE_REQUEST").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="REQUEST_CREATED", entity_type="ServiceRequest").count(), 1)
