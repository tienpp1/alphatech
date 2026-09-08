"""
Automated tests for Task model, status transitions, duration calculation, and APIs.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer
from apps.service_ops.models import Service, Employee, ServiceRequest, Task, TaskStatus
from apps.service_ops.services import create_task, transition_task_status


class ServiceTaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.perm_view = Permission.objects.create(codename="service.view_task", name="View", module="service_ops")
        self.perm_manage = Permission.objects.create(codename="service.manage_task", name="Manage", module="service_ops")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="task_admin",
            email="task_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

        self.customer = Customer.objects.create(workspace=self.workspace, code="CUST-01", name="Alpha Building")
        self.service = Service.objects.create(workspace=self.workspace, code="CCTV-01", name="CCTV Maintenance")
        self.tech = Employee.objects.create(workspace=self.workspace, code="TECH-01", full_name="Ha Le", phone="0901222333")
        self.req = ServiceRequest.objects.create(
            workspace=self.workspace,
            request_number="SR-TEST-0001",
            customer=self.customer,
            service=self.service,
            title="CCTV offline",
            description="NVR unreachable",
        )

    def test_task_creation_and_lifecycle(self):
        task = create_task(
            self.req,
            self.user,
            {
                "title": "Replace power adapter for NVR",
                "assigned_to_id": self.tech.id,
                "estimated_duration_minutes": 45,
            },
        )
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.assigned_to, self.tech)
        self.assertEqual(task.workspace, self.workspace)

        # 1. PENDING -> IN_PROGRESS
        task = transition_task_status(task, TaskStatus.IN_PROGRESS, self.user)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(task.started_at)

        # 2. IN_PROGRESS -> COMPLETED
        task = transition_task_status(task, TaskStatus.COMPLETED, self.user, actual_duration_minutes=40)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.actual_duration_minutes, 40)
        self.assertIsNotNone(task.completed_at)

    def test_task_invalid_transition_rejected(self):
        task = create_task(self.req, self.user, {"title": "Test Task"})
        # Direct PENDING -> COMPLETED is invalid (must go through IN_PROGRESS)
        with self.assertRaises(ValidationError):
            transition_task_status(task, TaskStatus.COMPLETED, self.user)
