"""
Automated tests for Employee / Technician model, JSON skills, coordinate storage, and APIs.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.service_ops.models import Employee
from apps.service_ops.services import create_employee, update_employee


class ServiceEmployeeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Service WS 1",
            code="svc-ws-1",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.perm_view = Permission.objects.create(codename="service.view_employee", name="View", module="service_ops")
        self.perm_manage = Permission.objects.create(codename="service.manage_employee", name="Manage", module="service_ops")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="emp_admin",
            email="emp_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_employee_with_skills_and_coordinates(self):
        emp = create_employee(
            workspace=self.workspace1,
            user=self.user,
            data={
                "code": "TECH-100",
                "full_name": "Nguyen Van B",
                "phone": "0901999888",
                "email": "vanb@example.com",
                "skills": ["HVAC", "Electrical"],
                "latitude": 10.7765,
                "longitude": 106.7035,
            },
        )
        self.assertEqual(emp.code, "TECH-100")
        self.assertEqual(emp.skills, ["HVAC", "Electrical"])
        self.assertIsNotNone(emp.current_location)
        self.assertAlmostEqual(float(emp.latitude), 10.7765, places=4)
        self.assertEqual(emp.current_workload_score, 0.0)

    def test_invalid_coordinates_rejected(self):
        with self.assertRaises(ValidationError):
            create_employee(
                workspace=self.workspace1,
                user=self.user,
                data={
                    "code": "TECH-INV",
                    "full_name": "Invalid Tech",
                    "latitude": 95.0,  # Invalid
                    "longitude": 106.7035,
                },
            )

    def test_employee_api_list_and_filter_by_skill(self):
        create_employee(
            self.workspace1,
            self.user,
            {"code": "TECH-1", "full_name": "Fiber Ha", "skills": ["Fiber Optics", "Network"]},
        )
        create_employee(
            self.workspace1,
            self.user,
            {"code": "TECH-2", "full_name": "Plumbing Minh", "skills": ["Plumbing"]},
        )

        url = reverse("service_api_employees")
        # Filter by skill
        res = self.client.get(url, {"skill": "Fiber Optics"}, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["data"][0]["code"], "TECH-1")
