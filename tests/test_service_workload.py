"""
Automated tests for Technician Workload metrics, score computation, and dashboard aggregations.
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer
from apps.service_ops.models import Service, Employee, ServiceRequest, Task, TaskStatus
from apps.service_ops.selectors import (
    get_service_dashboard_summary,
    get_technicians_workload_breakdown,
)
from apps.service_ops.services import recalculate_employee_workload


class ServiceWorkloadTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.user = User.objects.create_user(
            username="workload_tester",
            email="workload_tester@example.com",
            password="Password123!",
        )

        self.customer = Customer.objects.create(workspace=self.workspace, code="CUST-01", name="Alpha Building")
        self.service = Service.objects.create(workspace=self.workspace, code="HVAC-01", name="HVAC Maintenance")
        self.tech = Employee.objects.create(workspace=self.workspace, code="TECH-01", full_name="Son Nguyen", phone="0901222333")
        self.req = ServiceRequest.objects.create(
            workspace=self.workspace,
            request_number="SR-TEST-WL",
            customer=self.customer,
            service=self.service,
            title="Workload Test Ticket",
        )

    def test_workload_score_calculation(self):
        now = timezone.now()
        # Task 1: on time pending
        Task.objects.create(
            service_request=self.req,
            assigned_to=self.tech,
            title="Active Task 1",
            status=TaskStatus.PENDING,
            due_at=now + timedelta(hours=5),
        )
        # Task 2: overdue pending
        Task.objects.create(
            service_request=self.req,
            assigned_to=self.tech,
            title="Overdue Task 2",
            status=TaskStatus.IN_PROGRESS,
            due_at=now - timedelta(hours=2),
        )
        # Task 3: completed task (does not count towards active workload)
        Task.objects.create(
            service_request=self.req,
            assigned_to=self.tech,
            title="Completed Task 3",
            status=TaskStatus.COMPLETED,
        )

        # Expected score = 2 active tasks * 1.0 + (1 overdue task * 1.5) = 3.5
        score = recalculate_employee_workload(self.tech)
        self.assertEqual(score, 3.5)

    def test_dashboard_summary_selector(self):
        summary = get_service_dashboard_summary(self.workspace)
        self.assertEqual(summary["total_requests"], 1)
        self.assertEqual(summary["total_technicians"], 1)
        self.assertEqual(summary["available_technicians"], 1)
