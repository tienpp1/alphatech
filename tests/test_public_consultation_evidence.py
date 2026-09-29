"""Public consultation claims regression; no DB or external provider calls."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import SimpleTestCase, RequestFactory
from apps.public_web.views import public_copilot_api_view
from apps.public_web import alphatech_ai as ai


class PublicConsultationEvidenceTests(SimpleTestCase):
    def post(self, message):
        request = RequestFactory().post('/api/v1/public/copilot/',
                                        data=json.dumps({'message': message}), content_type='application/json')
        request.user = SimpleNamespace(is_authenticated=False)
        request.session = {}
        response = public_copilot_api_view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(set(data), {'reply', 'suggestions'})
        return data

    def test_unverified_policy_topics_do_not_promise_benefits(self):
        cases = [
            ('chính hãng CO/CQ', 'chưa có hồ sơ', '200%'),
            ('bồi hoàn 200%', 'chưa có hồ sơ', '200%'),
            ('thủ tục trả góp', 'chưa có chính sách', 'Lãi suất 0%'),
            ('hoàn tiền', 'chưa có chính sách', '1 – 3 ngày'),
            ('nâng cấp ram ssd', 'xác nhận', 'trọn đời'),
            ('cài win bản quyền', 'chưa có căn cứ', 'Windows 11 Pro'),
            ('báo giá doanh nghiệp', 'chưa có chính sách', 'b2b@alphatech.vn'),
            ('ISO 27001', 'chưa có bằng chứng', 'áp dụng quy trình an toàn thông tin chuẩn'),
            ('đặt thợ đến nhà', 'chưa có bảng phí', '150.000'),
            ('bảo hành', 'chưa có chính sách', '72 giờ'),
            ('hóa đơn VAT', 'chưa có bằng chứng', '24 giờ'),
            ('thu cũ đổi mới', 'chưa có chương trình', '15%'),
        ]
        for query, required, forbidden in cases:
            with self.subTest(query=query):
                data = self.post(query)
                self.assertIn(required, data['reply'])
                self.assertNotIn(forbidden, data['reply'])
                self.assertIn('](/', data['reply'])
                self.assertTrue(data['suggestions'])

    def test_greeting_does_not_promote_unverified_terms(self):
        for message in ('', 'xin chào'):
            text = json.dumps(self.post(message), ensure_ascii=False)
            for forbidden in ('0%', '72h', '24/7', 'SLA 15', '200%'):
                self.assertNotIn(forbidden, text)

    def test_empty_branch_directory_does_not_invent_addresses(self):
        with patch.object(ai.Branch, 'objects') as manager:
            manager.filter.return_value.order_by.return_value.__getitem__.return_value = []
            result = ai.handle_branch_locator('chi nhánh')['reply']
        self.assertIn('Chưa có chi nhánh', result)
        self.assertNotIn('1900', result)
        self.assertNotIn('Nguyễn Thị Minh Khai', result)

    def test_service_keeps_catalog_links_without_guarantees(self):
        service = SimpleNamespace(id=7, name='Cài đặt máy chủ', category='INSTALLATION', description='ISO 27001 GUARANTEED')
        with patch.object(ai.Service, 'objects') as manager:
            manager.filter.return_value.filter.return_value = [service]
            result = self.post('rớt mạng khẩn cấp')['reply']
        self.assertIn('service_id=7', result)
        self.assertIn('KHẨN CẤP', result)
        self.assertIn('cần được xác nhận', result)
        for unsupported in ('15 phút', '30 – 45 phút', 'ISO 27001', 'ngắt kết nối đường WAN'):
            self.assertNotIn(unsupported, result)

    def test_catalog_price_and_no_internal_cost(self):
        product = SimpleNamespace(id=9, name='Laptop Dell', sku='DELL', category=None, unit_price=18500000, cost_price=14000000)
        with patch.object(ai.Product, 'objects') as manager:
            qs = manager.filter.return_value.select_related.return_value
            qs.filter.return_value.__getitem__.return_value = [product]
            result = ai.handle_laptop_and_product_consulting('laptop dell', 'laptop dell')['reply']
        self.assertIn('18.500.000₫', result)
        self.assertIn('/san-pham/9/', result)
        for unsupported in ('14.000.000', '0%', 'trọn đời', 'có sẵn tại kho', 'đại lý phân phối ủy quyền'):
            self.assertNotIn(unsupported, result)

    def test_widget_copy_has_no_unverified_chips(self):
        text = (Path(settings.BASE_DIR) / 'templates/public/base_public.html').read_text(encoding='utf-8')
        self.assertIn('Trợ lý tự động', text)
        for unsupported in ('SLA &lt; 15m', 'DOA 72h', 'Trả góp 0%', 'Hotline 24/7'):
            self.assertNotIn(unsupported, text)
