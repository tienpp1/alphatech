from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.public_web.customer_identity import customer_for_submission
from apps.retail.models import Customer, Order
from apps.workspaces.models import Workspace


class CustomerAccountIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ws = Workspace.objects.create(code="identity-retail", name="Retail", workspace_type="RETAIL")
        cls.other = Workspace.objects.create(code="identity-service", name="Service", workspace_type="SERVICE")
        cls.user = get_user_model().objects.create_user(username="owner", email="owner@example.com")
        cls.customer = customer_for_submission(workspace=cls.ws, user=cls.user, name="Owner")

    def test_account_profile_is_unique_per_workspace(self):
        self.assertEqual(customer_for_submission(workspace=self.ws, user=self.user, name="New"), self.customer)
        other = customer_for_submission(workspace=self.other, user=self.user, name="Owner")
        self.assertNotEqual(other.pk, self.customer.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Customer.objects.create(workspace=self.ws, user=self.user, code="duplicate", name="Duplicate")

    def test_guest_cannot_reuse_account_profile_by_contact_details(self):
        guest = customer_for_submission(workspace=self.ws, user=AnonymousUser(), name="Owner", email=self.user.email)
        self.assertIsNone(guest.user_id)
        self.assertNotEqual(guest.pk, self.customer.pk)

    def test_form_email_does_not_link_another_account(self):
        profile = customer_for_submission(workspace=self.ws, user=self.user, name="Owner", email="victim@example.com")
        self.assertEqual(profile.email, self.user.email)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "owner@example.com")

    def test_matching_email_or_name_does_not_grant_order_access(self):
        guest = Customer.objects.create(workspace=self.ws, code="guest", name="Owner", email=self.user.email)
        order = Order.objects.create(workspace=self.ws, customer=guest, order_number="IDENTITY-GUEST",
                                     order_date=timezone.now().date(), order_timestamp=timezone.now())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 404)
        self.assertEqual(self.client.get(f"/tai-khoan/don-hang/{order.order_number}/").status_code, 404)
        self.assertNotContains(self.client.get("/tai-khoan/don-hang/"), order.order_number)

    def test_historical_creator_can_read_without_email_link(self):
        order = Order.objects.create(workspace=self.ws, customer=self.customer, created_by=self.user,
                                     order_number="IDENTITY-OWN", order_date=timezone.now().date(),
                                     order_timestamp=timezone.now())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 200)
        self.assertEqual(self.client.get(f"/tai-khoan/don-hang/{order.order_number}/").status_code, 200)

    def test_contact_is_persisted_and_deduplicated(self):
        from apps.public_web.models import ContactSubmission
        self.client.force_login(self.user)
        data = dict(name="Owner", email=self.user.email, message="Xin hỗ trợ đơn hàng")
        self.assertEqual(self.client.post("/lien-he/", data).status_code, 200)
        self.assertEqual(self.client.post("/lien-he/", data).status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        contact = ContactSubmission.objects.get()
        self.assertEqual(contact.user, self.user)
        self.assertEqual(contact.workspace, self.ws)
