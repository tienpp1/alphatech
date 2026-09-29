"""Email composition must not export internal knowledge or invent contracts."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.utils import timezone
from apps.public_web.email_service import send_order_confirmation_email, send_service_request_confirmation_email


class CustomerEmailPolicyBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.customer = SimpleNamespace(name='Customer fixture', email='customer@example.test')

    def compose(self, function, entity):
        with patch('apps.knowledge.services.get_grounded_policy_snippet',
                   return_value={'document_title': 'PRIVATE POLICY', 'content_snippet': 'PRIVATE-TENANT-SECRET'}) as lookup:
            with patch('apps.public_web.email_service.queue_and_deliver_email') as queue:
                function(entity)
            lookup.assert_not_called()
        payload = queue.call_args.kwargs
        self.assertEqual(payload['recipient'], self.customer.email)
        for body in (payload['plain_body'], payload['html_body']):
            for forbidden in ('PRIVATE-TENANT-SECRET', 'PRIVATE POLICY', 'ISO 27001', 'bảo mật tuyệt đối'):
                self.assertNotIn(forbidden, body)
        return payload

    def test_order_keeps_totals_without_internal_policy_or_tax_claim(self):
        items = MagicMock()
        items.select_related.return_value.all.return_value = [SimpleNamespace(
            product=SimpleNamespace(name='Fixture device', sku='FIXTURE'), quantity=2,
            unit_price=Decimal('100'), subtotal=Decimal('200'))]
        order = SimpleNamespace(pk=1, customer=self.customer, order_number='FIXTURE-ORDER',
            order_timestamp=timezone.now(), items=items, subtotal_amount=Decimal('200'),
            total_amount=Decimal('200'), branch=None, notes='Fixture destination')
        payload = self.compose(send_order_confirmation_email, order)
        self.assertIn('FIXTURE-ORDER', payload['plain_body'])
        self.assertIn('Fixture device', payload['plain_body'])
        self.assertIn('200 VNĐ', payload['plain_body'])
        self.assertNotIn('Đã bao gồm VAT', payload['plain_body'])
        self.assertNotIn('Đã bao gồm trong giá', payload['html_body'])
        self.assertIn('xác nhận điều kiện bảo hành', payload['plain_body'])

    def test_service_preserves_priority_without_fabricated_response_time(self):
        for priority, label in [('LOW', 'Thấp'), ('MEDIUM', 'Trung bình'), ('HIGH', 'Cao'), ('CRITICAL', 'Khẩn cấp')]:
            with self.subTest(priority=priority):
                request = SimpleNamespace(pk=2, customer=self.customer, request_number='FIXTURE-SERVICE',
                    service=SimpleNamespace(name='Fixture service'), created_at=timezone.now(), priority=priority)
                payload = self.compose(send_service_request_confirmation_email, request)
                self.assertIn('FIXTURE-SERVICE', payload['plain_body'])
                self.assertIn(label, payload['plain_body'])
                self.assertIn('không xác lập cam kết SLA mới', payload['plain_body'])
                for body in (payload['plain_body'], payload['html_body']):
                    self.assertNotIn('30 phút', body)
                    self.assertNotIn('Phản hồi trong ngày', body)
                    self.assertNotIn('24/7', body)
