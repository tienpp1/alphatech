"""Focused regressions for legacy Service/GIS workspace and RBAC boundaries."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User
from apps.retail.models import Customer
from apps.service_ops.models import Employee, Service, ServiceRequest, ServiceRequestStatus, Task
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


class InternalAuthorizationRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first_service_workspace = Workspace.objects.create(
            name="A Unrelated Service Workspace",
            code="unrelated-service",
            workspace_type=WorkspaceType.SERVICE,
        )
        cls.authorized_workspace = Workspace.objects.create(
            name="B Authorized Service Workspace",
            code="authorized-service",
            workspace_type=WorkspaceType.SERVICE,
        )
        cls.retail_workspace = Workspace.objects.create(
            name="Retail Membership Only",
            code="retail-only",
            workspace_type=WorkspaceType.RETAIL,
        )

        permission_codes = [
            "service.view_service",
            "service.view_employee",
            "service.view_request",
            "service.view_task",
            "service.view_schedule",
            "service.view_sla",
            "service.view_analytics",
            "service.manage_request",
            "service.assign_request",
            "service.manage_task",
            "service.manage_employee",
            "gis.view_spatial_layers",
        ]
        cls.permissions = {
            code: Permission.objects.create(codename=code, name=code, module=code.split(".")[0])
            for code in permission_codes
        }

        cls.admin_role = Role.objects.create(name="AUTHZ_ADMIN")
        cls.admin_role.permissions.set(cls.permissions.values())
        cls.manager_role = Role.objects.create(name="AUTHZ_MANAGER")
        cls.manager_role.permissions.set(cls.permissions.values())
        cls.employee_role = Role.objects.create(name="AUTHZ_EMPLOYEE")
        cls.employee_role.permissions.set(
            [
                cls.permissions["service.view_service"],
                cls.permissions["service.view_request"],
                cls.permissions["gis.view_spatial_layers"],
            ]
        )
        cls.retail_role = Role.objects.create(name="AUTHZ_RETAIL_ONLY")
        cls.retail_role.permissions.set(
            [cls.permissions["service.view_request"], cls.permissions["gis.view_spatial_layers"]]
        )

        cls.admin = cls._create_member("authz_admin", cls.admin_role, cls.authorized_workspace)
        cls.manager = cls._create_member("authz_manager", cls.manager_role, cls.authorized_workspace)
        cls.employee_user = cls._create_member("authz_employee", cls.employee_role, cls.authorized_workspace)
        cls.cross_workspace_user = cls._create_member(
            "authz_cross", cls.manager_role, cls.first_service_workspace
        )
        cls.retail_only_user = cls._create_member(
            "authz_retail", cls.retail_role, cls.retail_workspace
        )
        cls.public_customer = User.objects.create_user(
            username="authz_public", email="authz_public@example.com", password="Password123!"
        )

        cls.authorized_employee = Employee.objects.create(
            workspace=cls.authorized_workspace,
            user=cls.employee_user,
            code="TECH-AUTH",
            full_name="Authorized Technician",
            hourly_labor_rate=Decimal("150000"),
            current_location=Point(106.70, 10.77, srid=4326),
        )
        cls.unrelated_employee = Employee.objects.create(
            workspace=cls.first_service_workspace,
            code="TECH-SECRET",
            full_name="Unrelated First Technician",
            hourly_labor_rate=Decimal("150000"),
            current_location=Point(106.71, 10.78, srid=4326),
        )
        cls.authorized_ticket = cls._create_ticket(cls.authorized_workspace, "SR-AUTH")
        cls.unrelated_ticket = cls._create_ticket(cls.first_service_workspace, "SR-SECRET")
        cls.authorized_task = Task.objects.create(
            service_request=cls.authorized_ticket,
            assigned_to=cls.authorized_employee,
            title="Authorized task",
        )

    @classmethod
    def _create_member(cls, username, role, workspace):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=user, workspace=workspace, role=role, is_default=True
        )
        return user

    @classmethod
    def _create_ticket(cls, workspace, request_number):
        customer = Customer.objects.create(
            workspace=workspace,
            code=f"C-{request_number}",
            name=f"Customer {request_number}",
        )
        service = Service.objects.create(
            workspace=workspace,
            code=f"S-{request_number}",
            name=f"Service {request_number}",
            base_fee=Decimal("100000"),
        )
        return ServiceRequest.objects.create(
            workspace=workspace,
            request_number=request_number,
            customer=customer,
            service=service,
            title=f"Ticket {request_number}",
            description="Authorization regression fixture",
        )

    def _browser(self, user, workspace=None):
        client = Client()
        client.force_login(user)
        if workspace:
            session = client.session
            session["active_workspace_id"] = str(workspace.id)
            session.save()
        return client

    def test_first_global_service_workspace_is_never_used_as_fallback(self):
        client = self._browser(self.retail_only_user, self.retail_workspace)
        response = client.get("/services/requests/")
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "SR-SECRET", status_code=403)

    def test_authorized_member_resolves_service_membership_from_other_domain(self):
        WorkspaceMembership.objects.create(
            user=self.manager,
            workspace=self.retail_workspace,
            role=self.retail_role,
        )
        client = self._browser(self.manager, self.retail_workspace)
        response = client.get("/services/requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SR-AUTH")
        self.assertNotContains(response, "SR-SECRET")

    def test_public_customer_cannot_open_legacy_service_or_gis_ui(self):
        client = self._browser(self.public_customer)
        self.assertEqual(client.get("/services/requests/").status_code, 403)
        self.assertEqual(client.get("/services/gis/").status_code, 403)

    def test_service_detail_lookup_is_scoped_against_idor(self):
        client = self._browser(self.manager, self.authorized_workspace)
        response = client.get(f"/services/requests/{self.unrelated_ticket.id}/")
        self.assertEqual(response.status_code, 404)

    def test_admin_and_manager_can_read_and_manage_authorized_ticket(self):
        for user in (self.admin, self.manager):
            client = self._browser(user, self.authorized_workspace)
            self.assertEqual(client.get("/services/").status_code, 200)
            detail = client.get(f"/services/requests/{self.authorized_ticket.id}/")
            self.assertEqual(detail.status_code, 200)
            self.assertContains(detail, 'value="start"')
            mutation = client.post(
                f"/services/requests/{self.authorized_ticket.id}/",
                {"action": "start"},
            )
            self.assertEqual(mutation.status_code, 302)
            self.authorized_ticket.refresh_from_db()
            self.assertEqual(self.authorized_ticket.status, ServiceRequestStatus.IN_PROGRESS)
            self.authorized_ticket.status = ServiceRequestStatus.OPEN
            self.authorized_ticket.save(update_fields=["status"])

    def test_employee_can_read_but_cannot_change_ticket_status(self):
        client = self._browser(self.employee_user, self.authorized_workspace)
        detail = client.get(f"/services/requests/{self.authorized_ticket.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, 'value="start"')
        self.assertNotContains(detail, 'value="assign"')
        response = client.post(
            f"/services/requests/{self.authorized_ticket.id}/",
            {"action": "start"},
        )
        self.assertEqual(response.status_code, 403)
        self.authorized_ticket.refresh_from_db()
        self.assertEqual(self.authorized_ticket.status, ServiceRequestStatus.OPEN)
        assign_response = client.post(
            f"/services/requests/{self.authorized_ticket.id}/",
            {"action": "assign", "employee_id": self.authorized_employee.id},
        )
        self.assertEqual(assign_response.status_code, 403)
        self.authorized_ticket.refresh_from_db()
        self.assertIsNone(self.authorized_ticket.assigned_employee_id)

    def test_service_api_status_mutation_requires_manage_request(self):
        client = APIClient()
        client.force_authenticate(self.employee_user)
        response = client.post(
            f"/api/v1/service-ops/requests/{self.authorized_ticket.id}/start/",
            {},
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.id),
        )
        self.assertEqual(response.status_code, 403)

    def test_cross_workspace_api_ticket_mutation_is_not_found(self):
        client = APIClient()
        client.force_authenticate(self.manager)
        response = client.post(
            f"/api/v1/service-ops/requests/{self.unrelated_ticket.id}/start/",
            {},
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.id),
        )
        self.assertEqual(response.status_code, 404)

    def test_member_without_employee_profile_cannot_log_labor_for_someone_else(self):
        client = APIClient()
        client.force_authenticate(self.retail_only_user)
        WorkspaceMembership.objects.create(
            user=self.retail_only_user,
            workspace=self.authorized_workspace,
            role=self.employee_role,
        )
        now = timezone.now()
        response = client.post(
            "/api/v1/service-ops/labor-entries/",
            {
                "task_id": self.authorized_task.id,
                "employee_id": self.authorized_employee.id,
                "started_at": (now - timedelta(hours=1)).isoformat(),
                "ended_at": now.isoformat(),
                "duration_minutes": 60,
            },
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.id),
        )
        self.assertEqual(response.status_code, 403)

    def test_gis_ui_and_api_require_authorized_membership_and_permission(self):
        authorized = self._browser(self.employee_user, self.authorized_workspace)
        page = authorized.get("/services/gis/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "B Authorized Service Workspace")
        self.assertNotContains(page, "A Unrelated Service Workspace")

        authorized_api = APIClient()
        authorized_api.force_authenticate(self.employee_user)
        data = authorized_api.get(
            "/api/v1/gis/service/technicians/",
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.id),
        )
        self.assertEqual(data.status_code, 200)
        names = [feature["properties"]["full_name"] for feature in data.json()["data"]["features"]]
        self.assertIn("Authorized Technician", names)
        self.assertNotIn("Unrelated First Technician", names)

        unauthorized = APIClient()
        unauthorized.force_authenticate(self.retail_only_user)
        response = unauthorized.get(
            "/api/v1/gis/service/technicians/",
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.id),
        )
        self.assertEqual(response.status_code, 403)
