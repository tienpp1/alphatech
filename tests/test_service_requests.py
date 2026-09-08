"""
Automated tests for ServiceRequest model, lifecycle state transitions, assignment, and APIs.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.audit.models import AuditLog
from apps.retail.models import Customer
from apps.service_ops.models import Service, Employee, SLA, ServiceRequest, ServiceRequestStatus, Task, TaskStatus
from apps.service_ops.services import (
    create_service_request,
    assign_service_request,
    transition_service_request_status,
)


class ServiceRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.perm_view = Permission.objects.create(codename="service.view_request", name="View", module="service_ops")
        self.perm_create = Permission.objects.create(codename="service.create_request", name="Create", module="service_ops")
        self.perm_assign = Permission.objects.create(codename="service.assign_request", name="Assign", module="service_ops")
        self.perm_manage = Permission.objects.create(codename="service.manage_request", name="Manage", module="service_ops")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_create, self.perm_assign, self.perm_manage)

        self.user = User.objects.create_user(
            username="sr_admin",
            email="sr_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

        self.customer = Customer.objects.create(workspace=self.workspace, code="CUST-01", name="Bitexco Tower")
        self.service = Service.objects.create(workspace=self.workspace, code="HVAC-01", name="Chiller Maintenance", standard_duration_minutes=120)
        self.tech = Employee.objects.create(workspace=self.workspace, code="TECH-01", full_name="Minh Tran", phone="0901222333")

    def test_create_service_request_and_audit(self):
        req = create_service_request(
            self.workspace,
            self.user,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "Chiller vibration high",
                "description": "Floor 12 Chiller unit reporting bearing error",
                "priority": "HIGH",
            },
        )
        self.assertEqual(req.status, ServiceRequestStatus.OPEN)
        self.assertIsNotNone(req.request_number)
        self.assertIsNotNone(req.response_deadline_at)

        # Audit log verified
        audit = AuditLog.objects.filter(action="REQUEST_CREATED", entity_id=str(req.id)).first()
        self.assertIsNotNone(audit)

    def test_assign_service_request_creates_task_and_transitions_status(self):
        req = create_service_request(
            self.workspace,
            self.user,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "Chiller vibration high",
                "priority": "HIGH",
            },
        )
        self.assertEqual(req.status, ServiceRequestStatus.OPEN)

        req = assign_service_request(req, self.tech, self.user)
        self.assertEqual(req.status, ServiceRequestStatus.ASSIGNED)
        self.assertEqual(req.assigned_employee, self.tech)
        self.assertIsNotNone(req.responded_at)

        # Verify task created
        task = req.tasks.first()
        self.assertIsNotNone(task)
        self.assertEqual(task.assigned_to, self.tech)

    def test_lifecycle_state_machine_and_rejection_of_invalid_transitions(self):
        req = create_service_request(
            self.workspace,
            self.user,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "Lifecycle Test Ticket",
            },
        )
        self.assertEqual(req.status, ServiceRequestStatus.OPEN)

        # 1. OPEN -> IN_PROGRESS (Valid)
        req = transition_service_request_status(req, ServiceRequestStatus.IN_PROGRESS, self.user)
        self.assertEqual(req.status, ServiceRequestStatus.IN_PROGRESS)

        # 2. IN_PROGRESS -> RESOLVED (Valid)
        req = transition_service_request_status(req, ServiceRequestStatus.RESOLVED, self.user)
        self.assertEqual(req.status, ServiceRequestStatus.RESOLVED)
        self.assertIsNotNone(req.resolved_at)

        # 3. RESOLVED -> CLOSED (Valid)
        req = transition_service_request_status(req, ServiceRequestStatus.CLOSED, self.user)
        self.assertEqual(req.status, ServiceRequestStatus.CLOSED)
        self.assertIsNotNone(req.closed_at)

        # 4. CLOSED -> OPEN (Invalid: terminal state)
        with self.assertRaises(ValidationError):
            transition_service_request_status(req, ServiceRequestStatus.OPEN, self.user)

    def test_service_request_api_lifecycle(self):
        url = reverse("service_api_requests")
        post_res = self.client.post(
            url,
            {
                "customer_id": self.customer.id,
                "service_id": self.service.id,
                "title": "API Created Ticket",
                "description": "API description",
                "priority": "HIGH",
            },
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        req_id = post_res.data["data"]["id"]

        # Assign via API
        assign_url = reverse("service_api_request_assign", kwargs={"pk": req_id})
        assign_res = self.client.post(
            assign_url,
            {"employee_id": self.tech.id},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(assign_res.status_code, status.HTTP_200_OK)
        self.assertEqual(assign_res.data["data"]["status"], "ASSIGNED")
