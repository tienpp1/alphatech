"""
Unit & Integration Tests for Ingestion Job Lifecycle, Execution, and Staging Records.
"""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.integration.models import (
    DataSource,
    ImportJob,
    RawImportRecord,
    SourceType,
    EntityType,
    ImportStatus,
)
from apps.integration.services import execute_import_job


class ImportJobExecutionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test_admin_job", email="test_admin_job@example.com", password="AdminPass123!")
        self.role = Role.objects.create(name="ADMIN", description="Admin")
        self.ws = Workspace.objects.create(name="Retail WS", code="retail-ws", workspace_type=WorkspaceType.RETAIL)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=self.role, is_default=True)
        self.client.force_login(self.user)

    def test_execute_csv_import_job_completed(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="Retail POS Orders CSV",
            source_type=SourceType.CSV,
            created_by=self.user,
        )

        csv_bytes = (
            b"ma_don,khach_hang,tong_tien,ngay_dat\n"
            b"ORD-001,KH-01,1500000,2026-08-20\n"
            b"ORD-002,KH-02,2300000,2026-08-21\n"
            b"ORD-003,KH-03,850000,2026-08-22\n"
        )
        file_obj = SimpleUploadedFile("orders.csv", csv_bytes, content_type="text/csv")

        job = execute_import_job(
            workspace=self.ws,
            user=self.user,
            data_source=ds,
            file_obj=file_obj,
            entity_type=EntityType.RETAIL_ORDERS,
        )

        self.assertEqual(job.status, ImportStatus.COMPLETED)
        self.assertEqual(job.total_rows, 3)
        self.assertEqual(job.successful_rows, 3)
        self.assertEqual(job.failed_rows, 0)
        self.assertEqual(job.success_rate, 100.0)

        # Check raw records staged
        staged_records = RawImportRecord.objects.filter(import_job=job)
        self.assertEqual(staged_records.count(), 3)
        self.assertEqual(staged_records.first().raw_data["ma_don"], "ORD-001")
        self.assertTrue(staged_records.first().is_valid)

    def test_execute_csv_import_job_partial_status(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="Retail Mismatched CSV",
            source_type=SourceType.CSV,
            created_by=self.user,
        )

        csv_bytes = (
            b"col1,col2,col3\n"
            b"val1,val2,val3\n"
            b"bad_val1,bad_val2,bad_val3,extra4\n"
            b"val4,val5,val6\n"
        )
        file_obj = SimpleUploadedFile("mismatched.csv", csv_bytes, content_type="text/csv")

        job = execute_import_job(
            workspace=self.ws,
            user=self.user,
            data_source=ds,
            file_obj=file_obj,
        )

        self.assertEqual(job.status, ImportStatus.PARTIAL)
        self.assertEqual(job.total_rows, 3)
        self.assertEqual(job.successful_rows, 2)
        self.assertEqual(job.failed_rows, 1)
        self.assertGreater(len(job.error_summary), 0)

        # Check raw records
        bad_rec = RawImportRecord.objects.get(import_job=job, row_number=2)
        self.assertFalse(bad_rec.is_valid)
        self.assertIn("column mismatch", bad_rec.validation_errors[0])

    def test_execute_mock_api_import_job(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="External Orders API",
            source_type=SourceType.MOCK_API,
            connection_config={"url": "/api/v1/mock-external/retail/orders/"},
            created_by=self.user,
        )

        job = execute_import_job(
            workspace=self.ws,
            user=self.user,
            data_source=ds,
            entity_type=EntityType.RETAIL_ORDERS,
        )

        self.assertEqual(job.status, ImportStatus.COMPLETED)
        self.assertEqual(job.total_rows, 5)
        self.assertEqual(job.successful_rows, 5)
        self.assertEqual(job.raw_records.count(), 5)
        self.assertEqual(job.raw_records.first().raw_data["ma_don_hang"], "DH-EXT-202608-001")

    def test_import_job_rest_apis(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="Orders API Feed",
            source_type=SourceType.MOCK_API,
            connection_config={"url": "/api/v1/mock-external/retail/orders/"},
            created_by=self.user,
        )
        job = execute_import_job(workspace=self.ws, user=self.user, data_source=ds)

        # 1. List jobs
        res = self.client.get("/api/v1/integration/import-jobs/", HTTP_X_WORKSPACE_ID=str(self.ws.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)

        # 2. Detail job
        res = self.client.get(f"/api/v1/integration/import-jobs/{job.id}/", HTTP_X_WORKSPACE_ID=str(self.ws.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["status"], "COMPLETED")

        # 3. Raw records
        res = self.client.get(f"/api/v1/integration/import-jobs/{job.id}/raw-records/", HTTP_X_WORKSPACE_ID=str(self.ws.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 5)
