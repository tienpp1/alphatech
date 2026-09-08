"""
Unit & Integration tests for Data Mapping Simulation / Preview Engine.
Ensures preview is strictly read-only and non-mutating.
"""

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.integration.models import DataSource, SourceType, ImportJob, RawImportRecord
from apps.retail.models import Customer, Order
from apps.mapping.models import MappingProfile, MappingRule, RuleType
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    generate_mapping_preview,
)


class MappingPreviewTestCase(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Retail Corp",
            code="retail-corp",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.user = User.objects.create_user(username="previewer", email="previewer@example.com")
        self.role_admin = Role.objects.create(name="ADMIN")
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=self.role_admin,
            is_default=True,
        )

        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="KH001",
            name="Cong ty TNHH Thuong Mai ABC",
        )

        self.data_source = DataSource.objects.create(
            workspace=self.workspace,
            name="POS Legacy API",
            source_type=SourceType.MOCK_API,
        )

        self.profile = create_mapping_profile(
            workspace=self.workspace,
            user=self.user,
            name="Orders Preview Profile",
            target_entity="Order",
            data_source=self.data_source,
        )

        # Rules
        add_mapping_rule(self.profile, self.user, "ma_don", "order_number", RuleType.FIELD_MAPPING, order=1)
        add_mapping_rule(self.profile, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING, order=2)
        add_mapping_rule(self.profile, self.user, "ngay_dat", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"}, order=3)
        add_mapping_rule(self.profile, self.user, "tong_tien", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"}, order=4)

        self.import_job = ImportJob.objects.create(
            workspace=self.workspace,
            data_source=self.data_source,
            total_rows=2,
        )
        RawImportRecord.objects.create(
            workspace=self.workspace,
            import_job=self.import_job,
            row_number=1,
            raw_data={"ma_don": "ORD-101", "ma_kh": "KH001", "ngay_dat": "2026-08-25", "tong_tien": "1.500.000 đ"},
        )
        RawImportRecord.objects.create(
            workspace=self.workspace,
            import_job=self.import_job,
            row_number=2,
            raw_data={"ma_don": "ORD-102", "ma_kh": "KH_UNKNOWN_99", "ngay_dat": "invalid-date", "tong_tien": "not-a-number"},
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_service_preview_simulation(self):
        """Verifies preview engine transforms sample records and captures errors without database insertion."""
        orders_count_before = Order.objects.for_workspace(self.workspace).count()

        preview = generate_mapping_preview(
            workspace=self.workspace,
            profile=self.profile,
            import_job=self.import_job,
            sample_count=5,
        )

        # Verify no records written to Order domain table
        self.assertEqual(Order.objects.for_workspace(self.workspace).count(), orders_count_before)

        self.assertEqual(preview["sample_count"], 2)
        self.assertEqual(preview["valid_count"], 1)
        self.assertEqual(preview["invalid_count"], 1)
        self.assertFalse(preview["is_valid"])

        # Row 1 check
        sample_row_1 = preview["transformed_samples"][0]
        self.assertTrue(sample_row_1["is_valid"])
        self.assertEqual(sample_row_1["canonical_output"]["order_number"], "ORD-101")
        self.assertEqual(sample_row_1["canonical_output"]["revenue"], Decimal("1500000.00"))

        # Row 2 check (invalid date, invalid decimal, unknown customer foreign key)
        sample_row_2 = preview["transformed_samples"][1]
        self.assertFalse(sample_row_2["is_valid"])
        self.assertTrue(len(sample_row_2["errors"]) > 0)

    def test_preview_api_endpoint(self):
        """Tests POST /api/v1/mapping/preview/ endpoint."""
        url = "/api/v1/mapping/preview/"
        payload = {
            "profile_id": str(self.profile.id),
            "import_job_id": str(self.import_job.id),
            "sample_count": 5,
        }
        resp = self.client.post(
            url,
            payload,
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["target_entity"], "Order")
        self.assertEqual(resp.data["data"]["valid_count"], 1)
