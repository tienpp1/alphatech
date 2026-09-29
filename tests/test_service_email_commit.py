"""Real database commit boundaries; email transport is deliberately simulated."""
from unittest.mock import patch
from django.test import TransactionTestCase
from apps.workspaces.models import Workspace
from apps.service_ops.models import Service, ServiceRequest
from apps.public_web.models import CustomerEmailDelivery
from apps.public_web.email_service import deliver_outbox_record


class ServiceEmailCommitTests(TransactionTestCase):
    def test_committed_inquiry_warns_on_failed_email_and_retry_is_idempotent(self):
        ws = Workspace.objects.create(code="mail-service", name="Service", workspace_type="SERVICE")
        service = Service.objects.create(workspace=ws, code="S", name="Test")
        with patch("apps.public_web.email_service.send_mail", return_value=0):
            response = self.client.post("/yeu-cau-dich-vu/", {
                "customer_name": "Test", "phone": "0900000000", "email": "test@example.com",
                "service_id": service.pk, "description": "Test inquiry",
            })
        self.assertContains(response, "tiếp nhận thành công")
        self.assertTrue(response.context["email_warning"])
        inquiry = ServiceRequest.objects.get()
        delivery = CustomerEmailDelivery.objects.get(event_type="SERVICE_REQUEST")
        self.assertEqual(delivery.status, "FAILED")
        self.assertEqual(delivery.entity_id, str(inquiry.pk))
        with patch("apps.public_web.email_service.send_mail", return_value=1) as send:
            deliver_outbox_record(delivery)
            deliver_outbox_record(delivery)
            self.assertEqual(send.call_count, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "SENT")
        self.assertEqual(ServiceRequest.objects.count(), 1)
