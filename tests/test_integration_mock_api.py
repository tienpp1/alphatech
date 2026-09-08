"""
Unit & Integration Tests for Mock External REST APIs and API Parser.
"""

from django.test import TestCase, Client
from apps.integration.parsers.api_parser import fetch_and_parse_api


class MockExternalApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mock_retail_orders_endpoint(self):
        res = self.client.get("/api/v1/mock-external/retail/orders/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["count"], 0)
        first_item = data["data"][0]
        self.assertIn("ma_don_hang", first_item)
        self.assertIn("tong_thanh_toan", first_item)
        self.assertIn("trang_thai_don", first_item)

    def test_mock_retail_customers_endpoint(self):
        res = self.client.get("/api/v1/mock-external/retail/customers/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        first_item = data["data"][0]
        self.assertIn("ma_kh", first_item)
        self.assertIn("ho_ten", first_item)
        self.assertIn("phan_khuc", first_item)

    def test_mock_retail_products_endpoint(self):
        res = self.client.get("/api/v1/mock-external/retail/products/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        first_item = data["data"][0]
        self.assertIn("ma_sp", first_item)
        self.assertIn("gia_niem_yet", first_item)

    def test_mock_service_tickets_endpoint(self):
        res = self.client.get("/api/v1/mock-external/service/tickets/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        first_item = data["data"][0]
        self.assertIn("ma_ticket", first_item)
        self.assertIn("muc_do_uu_tien", first_item)
        self.assertIn("loai_dich_vu", first_item)

    def test_mock_service_technicians_endpoint(self):
        res = self.client.get("/api/v1/mock-external/service/technicians/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        first_item = data["data"][0]
        self.assertIn("ma_ky_thuat_vien", first_item)
        self.assertIn("don_gia_gio", first_item)

    def test_fetch_and_parse_api_local_mock_success(self):
        res = fetch_and_parse_api("/api/v1/mock-external/retail/orders/")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 5)
        self.assertIn("ma_don_hang", res["columns"])
        self.assertIn("tong_thanh_toan", res["columns"])
        self.assertEqual(len(res["rows"]), 5)
        self.assertEqual(res["rows"][0]["raw_data"]["ma_don_hang"], "DH-EXT-202608-001")

    def test_fetch_and_parse_api_404_url(self):
        res = fetch_and_parse_api("/api/v1/mock-external/non-existent-feed/")
        self.assertFalse(res["is_valid"])
        self.assertIn("404", res["error_message"])

    def test_fetch_and_parse_api_empty_url(self):
        res = fetch_and_parse_api("")
        self.assertFalse(res["is_valid"])
        self.assertIn("required", res["error_message"].lower())
