"""
Automated tests for SLA policy model, deterministic deadline math, and status compliance calculations.
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer
from apps.service_ops.models import Service, SLA, SLAPriority, ServiceRequest, ServiceRequestStatus
from apps.service_ops.services import create_sla_policy, create_service_request
from apps.service_ops.sla_engine import calculate_sla_status, SLAComplianceStatus


class ServiceSLATests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.user = User.objects.create_user(
            username="sla_tester",
            email="sla_tester@example.com",
            password="Password123!",
        )

        self.sla_critical = create_sla_policy(
            self.workspace,
            self.user,
            {"name": "Critical SLA", "priority": "CRITICAL", "response_time_hours": 2, "resolution_time_hours": 4},
        )
        self.sla_medium = create_sla_policy(
            self.workspace,
            self.user,
            {"name": "Medium SLA", "priority": "MEDIUM", "response_time_hours": 12, "resolution_time_hours": 24},
        )

        self.customer = Customer.objects.create(workspace=self.workspace, code="CUST-01", name="Alpha Tower")
        self.service = Service.objects.create(workspace=self.workspace, code="SVC-01", name="Alarm Check")

    def test_sla_policy_uniqueness_per_priority(self):
        with self.assertRaises(ValidationError):
            create_sla_policy(
                self.workspace,
                self.user,
                {"name": "Duplicate Critical", "priority": "CRITICAL", "response_time_hours": 1, "resolution_time_hours": 2},
            )

    def test_request_deadline_calculation_from_sla(self):
        req = create_service_request(
            self.workspace,
            self.user,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "Fire alarm check",
                "priority": "CRITICAL",
            },
        )
        # Expected response deadline = created_at + 2 hours
        # Expected resolution deadline = created_at + 4 hours
        diff_resp = req.response_deadline_at - req.created_at
        diff_resol = req.resolution_deadline_at - req.created_at
        self.assertEqual(round(diff_resp.total_seconds() / 3600), 2)
        self.assertEqual(round(diff_resol.total_seconds() / 3600), 4)

    def test_sla_compliance_status_calculation(self):
        req = create_service_request(
            self.workspace,
            self.user,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "Fire alarm check",
                "priority": "CRITICAL",
            },
        )

        now = req.created_at
        # 1. At creation time, both response & resolution are ON_TIME
        sla_1 = calculate_sla_status(req, reference_time=now + timedelta(minutes=10))
        self.assertEqual(sla_1["response_status"], SLAComplianceStatus.ON_TIME)
        self.assertEqual(sla_1["resolution_status"], SLAComplianceStatus.ON_TIME)
        self.assertEqual(sla_1["overall_status"], SLAComplianceStatus.ON_TIME)

        # 2. When 3 hours pass without response, response deadline (2h) is BREACHED
        sla_2 = calculate_sla_status(req, reference_time=now + timedelta(hours=3))
        self.assertEqual(sla_2["response_status"], SLAComplianceStatus.BREACHED)
        self.assertEqual(sla_2["overall_status"], SLAComplianceStatus.BREACHED)

        # 3. When 5 hours pass without resolution, resolution deadline (4h) is BREACHED
        sla_3 = calculate_sla_status(req, reference_time=now + timedelta(hours=5))
        self.assertEqual(sla_3["resolution_status"], SLAComplianceStatus.BREACHED)
        self.assertEqual(sla_3["overall_status"], SLAComplianceStatus.BREACHED)
