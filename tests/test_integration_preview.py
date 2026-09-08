"""
Unit & Integration Tests for Ingestion Preview Engine & Preview API.
"""

import io
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.integration.models import DataSource, SourceType
from apps.integration.parsers.preview_engine import generate_preview_metadata, infer_column_types


class ImportPreviewEngineTests(TestCase):
    def test_infer_column_types(self):
        columns = ["id", "price", "order_date", "is_active", "notes"]
        rows = [
            {"raw_data": {"id": "101", "price": "1,500.50", "order_date": "2026-08-20", "is_active": "true", "notes": "Urgent"}},
            {"raw_data": {"id": "102", "price": "2,300.00", "order_date": "2026-08-21", "is_active": "false", "notes": "Normal"}},
            {"raw_data": {"id": "103", "price": "750.00", "order_date": "2026-08-22", "is_active": "yes", "notes": "VIP"}},
        ]
        types = infer_column_types(columns, rows)
        self.assertEqual(types["id"], "INTEGER")
        self.assertEqual(types["price"], "DECIMAL")
        self.assertEqual(types["order_date"], "DATE")
        self.assertEqual(types["is_active"], "BOOLEAN")
        self.assertEqual(types["notes"], "STRING")

    def test_generate_preview_metadata_success(self):
        parse_res = {
            "columns": ["code", "amount", "status"],
            "rows": [
                {"row_number": 1, "raw_data": {"code": "C1", "amount": "100", "status": "OK"}, "is_valid": True, "errors": []},
                {"row_number": 2, "raw_data": {"code": "C2", "amount": "200", "status": "OK"}, "is_valid": True, "errors": []},
            ],
            "total_rows": 2,
            "encoding": "utf-8",
            "warnings": [],
            "is_valid": True,
        }
        preview = generate_preview_metadata(parse_res, sample_count=5)
        self.assertTrue(preview["is_valid"])
        self.assertEqual(preview["total_rows"], 2)
        self.assertEqual(len(preview["sample_rows"]), 2)
        self.assertEqual(preview["detected_types"]["amount"], "INTEGER")


class ImportPreviewApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test_admin", email="test_admin@example.com", password="AdminPass123!")
        self.role = Role.objects.create(name="ADMIN", description="Admin")
        self.ws = Workspace.objects.create(name="Retail WS", code="retail-ws", workspace_type=WorkspaceType.RETAIL)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=self.role, is_default=True)
        self.client.force_login(self.user)

    def test_preview_csv_upload_api(self):
        csv_bytes = b"ma_sp,ten_sp,gia,ngay_nhap\nSP-01,Ban phim,1500000,2026-08-20\nSP-02,Chuot,800000,2026-08-21\n"
        uploaded_file = SimpleUploadedFile("products.csv", csv_bytes, content_type="text/csv")

        res = self.client.post(
            "/api/v1/integration/imports/preview/",
            {"file": uploaded_file, "source_type": "CSV"},
            HTTP_X_WORKSPACE_ID=str(self.ws.id),
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        preview_data = data["data"]
        self.assertTrue(preview_data["is_valid"])
        self.assertEqual(preview_data["total_rows"], 2)
        self.assertEqual(preview_data["columns"], ["ma_sp", "ten_sp", "gia", "ngay_nhap"])
        self.assertEqual(preview_data["detected_types"]["gia"], "INTEGER")

    def test_preview_mock_api_source(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="Mock Orders Feed",
            source_type=SourceType.MOCK_API,
            connection_config={"url": "/api/v1/mock-external/retail/orders/"},
            created_by=self.user,
        )

        res = self.client.post(
            "/api/v1/integration/imports/preview/",
            {"data_source_id": str(ds.id)},
            HTTP_X_WORKSPACE_ID=str(self.ws.id),
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["data"]["is_valid"])
        self.assertEqual(data["data"]["total_rows"], 5)
        self.assertIn("ma_don_hang", data["data"]["columns"])
