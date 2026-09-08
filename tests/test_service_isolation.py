"""
Automated tests for Strict Multi-Tenant Isolation across Service Operations Domain.
Ensures zero data leakage between distinct workspaces.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer
from apps.service_ops.models import Service, Employee, ServiceRequest


class ServiceIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace_a = Workspace.objects.create(
            name="Service A",
            code="service-a",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.workspace_b = Workspace.objects.create(
            name="Service B",
            code="service-b",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.perm_view = Permission.objects.create(codename="service.view_service", name="View Service", module="service_ops")
        self.perm_req_view = Permission.objects.create(codename="service.view_request", name="View Request", module="service_ops")
        self.perm_emp_view = Permission.objects.create(codename="service.view_employee", name="View Employee", module="service_ops")

        self.role = Role.objects.create(name="OPERATOR")
        self.role.permissions.add(self.perm_view, self.perm_req_view, self.perm_emp_view)

        self.user_a = User.objects.create_user(
            username="user_svc_a",
            email="user_svc_a@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.user_a, workspace=self.workspace_a, role=self.role, is_default=True)

        self.user_b = User.objects.create_user(
            username="user_svc_b",
            email="user_svc_b@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.user_b, workspace=self.workspace_b, role=self.role, is_default=True)

        # Populate Workspace A
        self.svc_a = Service.objects.create(workspace=self.workspace_a, code="SVC-A", name="Service A")
        self.emp_a = Employee.objects.create(workspace=self.workspace_a, code="EMP-A", full_name="Tech A")
        self.cust_a = Customer.objects.create(workspace=self.workspace_a, code="CUST-A", name="Cust A")
        self.req_a = ServiceRequest.objects.create(
            workspace=self.workspace_a, request_number="SR-A-01", customer=self.cust_a, service=self.svc_a, title="Ticket A"
        )

        # Populate Workspace B
        self.svc_b = Service.objects.create(workspace=self.workspace_b, code="SVC-B", name="Service B")
        self.emp_b = Employee.objects.create(workspace=self.workspace_b, code="EMP-B", full_name="Tech B")
        self.cust_b = Customer.objects.create(workspace=self.workspace_b, code="CUST-B", name="Cust B")
        self.req_b = ServiceRequest.objects.create(
            workspace=self.workspace_b, request_number="SR-B-01", customer=self.cust_b, service=self.svc_b, title="Ticket B"
        )

    def test_user_a_cannot_see_services_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("service_api_services")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = [s["code"] for s in res.data["data"]]
        self.assertIn("SVC-A", codes)
        self.assertNotIn("SVC-B", codes)

    def test_user_a_cannot_see_technicians_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("service_api_employees")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = [e["code"] for e in res.data["data"]]
        self.assertIn("EMP-A", codes)
        self.assertNotIn("EMP-B", codes)

    def test_user_a_cannot_see_requests_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("service_api_requests")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ticket_nums = [r["request_number"] for r in res.data["data"]]
        self.assertIn("SR-A-01", ticket_nums)
        self.assertNotIn("SR-B-01", ticket_nums)

    def test_user_a_cannot_access_ticket_detail_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("service_api_request_detail", kwargs={"pk": self.req_b.id})
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_access_workspace_b_with_spoofed_header(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("service_api_requests")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_b.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
