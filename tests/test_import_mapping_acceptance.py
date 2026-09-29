"""CSV parser -> staging -> canonical Customer acceptance (no provider mocks)."""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import PermissionDenied
from apps.accounts.models import User
from apps.workspaces.models import Workspace
from apps.integration.models import DataSource, ImportJob, RawImportRecord
from apps.integration.services import execute_import_job
from apps.mapping.models import RuleType
from apps.mapping.services import create_mapping_profile, add_mapping_rule, apply_mapping_to_domain
from apps.retail.models import Customer


class ImportMappingAcceptanceTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code="import-a", name="A", workspace_type="RETAIL")
        self.other = Workspace.objects.create(code="import-b", name="B", workspace_type="RETAIL")
        self.user = User.objects.create_user(username="import-review", email="import@example.com")
        self.source = DataSource.objects.create(workspace=self.ws, name="CSV", source_type="CSV")
        self.profile = create_mapping_profile(self.ws, self.user, "Customers", "Customer", data_source=self.source)
        for source, target in (("code", "customer_id"), ("name", "name")):
            add_mapping_rule(self.profile, self.user, source, target, RuleType.FIELD_MAPPING)

    def ingest(self, rows):
        return execute_import_job(self.ws, self.user, self.source,
            SimpleUploadedFile("customers.csv", ("code,name\n" + rows).encode("utf-8")))

    def apply(self, job, strict=True):
        return apply_mapping_to_domain(**dict(workspace=self.ws, user=self.user,
            profile=self.profile, import_job=job, strict=strict))

    def test_csv_duplicate_business_key_upserts_only_current_workspace(self):
        foreign = Customer.objects.create(workspace=self.other, code="C1", name="Private")
        job = self.ingest("C1,Nguyễn An\nC1,Nguyễn Bình\n")
        self.assertEqual(job.raw_records.count(), 2)
        self.assertEqual(self.apply(job)["status"], "COMPLETED")
        self.assertEqual(self.apply(job)["status"], "COMPLETED")
        self.assertEqual(Customer.objects.filter(workspace=self.ws).count(), 1)
        self.assertEqual(Customer.objects.get(workspace=self.ws).name, "Nguyễn Bình")
        foreign.refresh_from_db()
        self.assertEqual(foreign.name, "Private")

    def test_malformed_csv_strict_rejects_all_then_partial_keeps_only_valid(self):
        job = self.ingest("C1,Valid\nC2,Bad,unexpected\n")
        self.assertEqual(job.failed_rows, 1)
        self.assertEqual(self.apply(job)["status"], "FAILED")
        self.assertFalse(Customer.objects.filter(workspace=self.ws).exists())
        result = self.apply(job, strict=False)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(list(Customer.objects.filter(workspace=self.ws).values_list("code", flat=True)), ["C1"])

    def test_canonical_missing_name_rolls_back_strict_batch(self):
        job = self.ingest("C1,Valid\nC2,\n")
        self.assertEqual(self.apply(job)["status"], "FAILED")
        self.assertFalse(Customer.objects.filter(workspace=self.ws).exists())

    def test_foreign_datasource_rejected_before_job_creation(self):
        source = DataSource.objects.create(workspace=self.other, name="Private", source_type="CSV")
        with self.assertRaises(PermissionDenied):
            execute_import_job(self.ws, self.user, source)
        self.assertFalse(ImportJob.objects.exists())

    def test_foreign_job_and_malformed_raw_workspace_are_rejected(self):
        job = self.ingest("C1,Valid\n")
        with self.assertRaises(PermissionDenied):
            apply_mapping_to_domain(self.other, self.user, self.profile, job)
        RawImportRecord.objects.filter(import_job=job).update(workspace=self.other)
        with self.assertRaises(PermissionDenied):
            self.apply(job)
        self.assertFalse(Customer.objects.exists())

    def test_foreign_profile_rejected_with_authorized_job(self):
        job = self.ingest("C1,Valid\n")
        profile = create_mapping_profile(self.other, self.user, "Foreign", "Customer")
        with self.assertRaises(PermissionDenied):
            apply_mapping_to_domain(self.ws, self.user, profile, job)
        self.assertFalse(Customer.objects.exists())
