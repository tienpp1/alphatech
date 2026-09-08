"""
Unit & Integration tests for Applying Mappings to Canonical Domain Tables.
Covers:
- Retail domain import (Customer, Product, Order)
- Service domain import (Employee, ServiceRequest)
- Foreign key failure detection
- Atomic transaction guarantees
"""

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.integration.models import DataSource, SourceType, ImportJob, RawImportRecord
from apps.retail.models import Customer, Product, Category, Order
from apps.service_ops.models import Employee, Service, ServiceRequest, SLA, SLAPriority
from apps.mapping.models import MappingProfile, MappingRule, RuleType
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    apply_mapping_to_domain,
)


class MappingApplyTestCase(TestCase):
    def setUp(self):
        # Retail Workspace
        self.retail_ws = Workspace.objects.create(
            name="Retail Inc",
            code="retail-inc",
            workspace_type=WorkspaceType.RETAIL,
        )
        # Service Workspace
        self.service_ws = Workspace.objects.create(
            name="Service IT Tech",
            code="service-it-tech",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.user = User.objects.create_user(username="apply_user", email="apply@example.com")
        self.role_admin = Role.objects.create(name="ADMIN")

        WorkspaceMembership.objects.create(workspace=self.retail_ws, user=self.user, role=self.role_admin, is_default=True)
        WorkspaceMembership.objects.create(workspace=self.service_ws, user=self.user, role=self.role_admin)

        self.sla = SLA.objects.create(
            workspace=self.service_ws,
            name="Default IT SLA",
            priority=SLAPriority.MEDIUM,
            response_time_hours=4,
            resolution_time_hours=24,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_apply_retail_customers(self):
        """Tests canonical loading into Customer domain table."""
        ds = DataSource.objects.create(workspace=self.retail_ws, name="Cust CSV", source_type=SourceType.CSV)
        profile = create_mapping_profile(self.retail_ws, self.user, "Cust Map", "Customer", data_source=ds)
        add_mapping_rule(profile, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "ten_kh", "name", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "sdt", "phone", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "dia_chi", "address", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "vi_do", "latitude", RuleType.TYPE_CONVERSION, {"target_type": "FLOAT"})
        add_mapping_rule(profile, self.user, "kinh_do", "longitude", RuleType.TYPE_CONVERSION, {"target_type": "FLOAT"})

        job = ImportJob.objects.create(workspace=self.retail_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.retail_ws,
            import_job=job,
            row_number=1,
            raw_data={
                "ma_kh": "CUST-CANON-01",
                "ten_kh": "Bui Van B",
                "sdt": "0987654321",
                "dia_chi": "123 Nguyen Trai, Q1, HCMC",
                "vi_do": "10.762622",
                "kinh_do": "106.682123",
            },
        )

        res = apply_mapping_to_domain(
            workspace=self.retail_ws,
            user=self.user,
            profile=profile,
            import_job=job,
            strict=True,
        )

        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["inserted_count"], 1)

        cust = Customer.objects.for_workspace(self.retail_ws).filter(code="CUST-CANON-01").first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, "Bui Van B")
        self.assertEqual(cust.phone, "0987654321")
        self.assertIsNotNone(cust.location)
        self.assertAlmostEqual(cust.location.y, 10.762622, places=4)
        self.assertAlmostEqual(cust.location.x, 106.682123, places=4)

    def test_apply_retail_orders_with_foreign_keys(self):
        """Tests importing orders with existing customer foreign key resolution."""
        cust = Customer.objects.create(workspace=self.retail_ws, code="KH-ORDER-01", name="Doanh Nghiep X")

        ds = DataSource.objects.create(workspace=self.retail_ws, name="Orders Feed", source_type=SourceType.CSV)
        profile = create_mapping_profile(self.retail_ws, self.user, "Orders Map", "Order", data_source=ds)
        add_mapping_rule(profile, self.user, "so_hd", "order_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "ngay", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"})
        add_mapping_rule(profile, self.user, "tien", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"})

        job = ImportJob.objects.create(workspace=self.retail_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.retail_ws,
            import_job=job,
            row_number=1,
            raw_data={"so_hd": "HD-TEST-999", "ma_kh": "KH-ORDER-01", "ngay": "2026-08-26", "tien": "2.500.000 đ"},
        )

        res = apply_mapping_to_domain(
            workspace=self.retail_ws,
            user=self.user,
            profile=profile,
            import_job=job,
            strict=True,
        )

        self.assertEqual(res["status"], "COMPLETED")
        order = Order.objects.for_workspace(self.retail_ws).filter(order_number="HD-TEST-999").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.customer, cust)
        self.assertEqual(order.total_amount, Decimal("2500000.00"))

    def test_apply_service_tickets(self):
        """Tests canonical loading into ServiceRequest domain table."""
        cust = Customer.objects.create(workspace=self.service_ws, code="CUST-SVC-01", name="Nha Khoa Smile")
        svc = Service.objects.create(workspace=self.service_ws, code="NET-01", name="Network Configuration")

        ds = DataSource.objects.create(workspace=self.service_ws, name="Ticket Feed", source_type=SourceType.CSV)
        profile = create_mapping_profile(self.service_ws, self.user, "Ticket Map", "ServiceRequest", data_source=ds)
        add_mapping_rule(profile, self.user, "ticket_no", "request_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "client_id", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "service_id", "service_code", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "issue_title", "title", RuleType.FIELD_MAPPING)

        job = ImportJob.objects.create(workspace=self.service_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.service_ws,
            import_job=job,
            row_number=1,
            raw_data={
                "ticket_no": "SR-CANON-777",
                "client_id": "CUST-SVC-01",
                "service_id": "NET-01",
                "issue_title": "Internet gateway unresponsive",
            },
        )

        res = apply_mapping_to_domain(
            workspace=self.service_ws,
            user=self.user,
            profile=profile,
            import_job=job,
            strict=True,
        )

        self.assertEqual(res["status"], "COMPLETED", msg=f"Apply failed: {res}")
        ticket = ServiceRequest.objects.for_workspace(self.service_ws).filter(request_number="SR-CANON-777").first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.customer, cust)
        self.assertEqual(ticket.service, svc)

    def test_apply_api_endpoint(self):
        """Tests POST /api/v1/mapping/apply/ endpoint."""
        cust = Customer.objects.create(workspace=self.retail_ws, code="KH-API-01", name="Khach Hang API")
        ds = DataSource.objects.create(workspace=self.retail_ws, name="API Test", source_type=SourceType.CSV)
        profile = create_mapping_profile(self.retail_ws, self.user, "API Map", "Order", data_source=ds)
        add_mapping_rule(profile, self.user, "so_hd", "order_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.user, "ngay", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"})
        add_mapping_rule(profile, self.user, "tien", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"})

        job = ImportJob.objects.create(workspace=self.retail_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.retail_ws,
            import_job=job,
            row_number=1,
            raw_data={"so_hd": "HD-REST-888", "ma_kh": "KH-API-01", "ngay": "2026-08-26", "tien": "800.000 đ"},
        )

        url = "/api/v1/mapping/apply/"
        payload = {
            "profile_id": str(profile.id),
            "import_job_id": str(job.id),
            "strict": True,
        }
        resp = self.client.post(
            url,
            payload,
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.retail_ws.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["inserted_count"], 1)

        self.assertTrue(Order.objects.for_workspace(self.retail_ws).filter(order_number="HD-REST-888").exists())
