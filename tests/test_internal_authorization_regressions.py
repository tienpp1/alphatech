"""Focused regressions for legacy Service/GIS workspace and RBAC boundaries."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import shutil
from unittest.mock import patch

from django.conf import settings
from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User
from apps.retail.models import Customer
from apps.service_ops.models import Employee, Service, ServiceRequest, ServiceRequestStatus, Task, LaborEntry
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


class InternalAuthorizationRegressionTests(TestCase):
    def test_service_read_endpoints_require_their_permission(self):
        from apps.service_ops.models import Schedule
        schedule = Schedule.objects.create(task=self.authorized_task,
            employee=self.authorized_employee, start_time=timezone.now(),
            end_time=timezone.now()+timedelta(hours=1))
        role = Role.objects.create(name="READ_MATRIX")
        user = self._create_member("read_matrix", role, self.authorized_workspace)
        client = APIClient()
        client.force_authenticate(user)
        endpoints = {
            "service.view_service": ["services/", f"services/{self.authorized_ticket.service_id}/"],
            "service.view_employee": ["employees/", f"employees/{self.authorized_employee.pk}/"],
            "service.view_sla": ["slas/"],
            "service.view_request": ["requests/", f"requests/{self.authorized_ticket.pk}/"],
            "service.view_task": ["tasks/", f"tasks/{self.authorized_task.pk}/", f"tasks/{self.authorized_task.pk}/labor/"],
            "service.view_schedule": ["schedules/", f"schedules/{schedule.pk}/"],
            "service.view_analytics": ["labor-entries/", f"requests/{self.authorized_ticket.pk}/cost/"],
        }
        for permission, paths in endpoints.items():
            for path in paths:
                url = "/api/v1/service-ops/" + path
                with self.subTest(permission=permission, path=path):
                    role.permissions.clear()
                    for method in (client.get, client.head):
                        self.assertEqual(method(url, HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.pk)).status_code, 403)
                    role.permissions.add(self.permissions[permission])
                    self.assertEqual(client.get(url, HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.pk)).status_code, 200)
                    self.assertEqual(client.get(url, HTTP_X_WORKSPACE_ID=str(self.first_service_workspace.pk)).status_code, 403)

    def test_service_read_permissions_do_not_grant_mutation(self):
        client = APIClient()
        client.force_authenticate(self.employee_user)
        response = client.post("/api/v1/service-ops/services/", {"name": "Forbidden"},
            HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.pk))
        self.assertEqual(response.status_code, 403)

    def test_analytics_denial_happens_before_sensitive_selectors(self):
        client = APIClient()
        for user in (self.employee_user, self.public_customer, self.cross_workspace_user):
            client.force_authenticate(user)
            for endpoint in ("overview", "workload", "sla"):
                with self.subTest(user=user.username, endpoint=endpoint), patch(
                    "apps.service_ops.views.get_service_dashboard_summary"
                ) as summary, patch(
                    "apps.service_ops.views.get_technicians_workload_breakdown"
                ) as workload:
                    response = client.get(f"/api/v1/service-ops/analytics/{endpoint}/",
                        HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.pk))
                    self.assertEqual(response.status_code, 403)
                    summary.assert_not_called()
                    workload.assert_not_called()

    def test_analytics_authorized_roles_remain_workspace_scoped(self):
        client = APIClient()
        for user in (self.admin, self.manager):
            client.force_authenticate(user)
            for endpoint in ("overview", "workload", "sla"):
                with self.subTest(user=user.username, endpoint=endpoint):
                    response = client.get(f"/api/v1/service-ops/analytics/{endpoint}/",
                        HTTP_X_WORKSPACE_ID=str(self.authorized_workspace.pk))
                    self.assertEqual(response.status_code, 200)
                    data = response.json()["data"]
                    if endpoint == "overview":
                        self.assertEqual(data["total_requests"], 1)
                        self.assertEqual(data["total_technicians"], 1)
                    elif endpoint == "workload":
                        self.assertEqual([row["code"] for row in data], ["TECH-AUTH"])
                    else:
                        self.assertEqual(set(data), {"on_time_count", "at_risk_count",
                                                   "breached_count", "compliance_rate",
                                                   "unknown_count", "evaluated_count"})
                        self.assertIsNone(data["compliance_rate"])
                        self.assertEqual(data["unknown_count"], 1)
                        self.assertEqual(data["evaluated_count"], 0)

    def test_missing_sla_dashboard_and_list_labels(self):
        client = self._browser(self.manager, self.authorized_workspace)
        for path in ("/noibo/services/", "/noibo/services/requests/"):
            page = client.get(path)
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, "Chưa đủ dữ liệu")
            self.assertNotContains(page, "100.0%")
            if path == "/noibo/services/" and getattr(settings, "EVIDENCE_REPORT_DIR", None):
                directory = Path(settings.EVIDENCE_REPORT_DIR) / "service_ui"
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "sla_dashboard.html").write_text(page.content.decode(), encoding="utf-8")


    def test_missing_sla_deadlines_are_not_presented_as_compliant(self):
        client = self._browser(self.manager, self.authorized_workspace)
        url = f"/noibo/services/requests/{self.authorized_ticket.pk}/"
        page = client.get(url)
        self.assertContains(page, "CHƯA ĐỦ DỮ LIỆU ĐÁNH GIÁ SLA")
        self.assertContains(page, "Chưa gắn chính sách SLA")
        self.assertNotContains(page, "ĐÚNG HẠN")
        self.authorized_ticket.response_deadline_at = timezone.now() - timedelta(hours=1)
        self.authorized_ticket.save(update_fields=["response_deadline_at"])
        page = client.get(url)
        self.assertContains(page, "CHƯA ĐỦ DỮ LIỆU ĐÁNH GIÁ SLA")
        self.assertContains(page, "Vi phạm")
        self.assertContains(page, "Chưa cấu hình hạn giải quyết")
        self.authorized_ticket.resolution_deadline_at = timezone.now() + timedelta(hours=1)
        self.authorized_ticket.save(update_fields=["resolution_deadline_at"])
        page = client.get(url)
        self.assertContains(page, "VI PHẠM SLA")
        self.assertNotContains(page, "CHƯA ĐỦ DỮ LIỆU ĐÁNH GIÁ SLA")

    def test_detail_post_foreign_employee_preserves_404(self):
        client = self._browser(self.manager, self.authorized_workspace)
        for prefix in ("/services/", "/noibo/services/"):
            for action in ("assign", "log_labor"):
                with self.subTest(prefix=prefix, action=action):
                    response = client.post(f"{prefix}requests/{self.authorized_ticket.pk}/", {
                        "action": action, "employee_id": self.unrelated_employee.pk,
                        "task_id": self.authorized_task.pk, "duration_minutes": 30,
                    })
                    self.assertEqual(response.status_code, 404)
                    self.assertNotContains(response, "TECH-SECRET", status_code=404)
        self.assertFalse(LaborEntry.objects.exists())
        self.authorized_ticket.refresh_from_db()
        self.assertIsNone(self.authorized_ticket.assigned_employee_id)

    def test_detail_post_foreign_task_preserves_404(self):
        task = Task.objects.create(service_request=self.unrelated_ticket, title="Foreign task")
        client = self._browser(self.manager, self.authorized_workspace)
        response = client.post(f"/noibo/services/requests/{self.authorized_ticket.pk}/", {
            "action": "log_labor", "employee_id": self.authorized_employee.pk,
            "task_id": task.pk, "duration_minutes": 30,
        })
        self.assertEqual(response.status_code, 404)
        self.assertFalse(LaborEntry.objects.exists())

    def test_own_labor_options_and_forged_other_employee(self):
        other = Employee.objects.create(workspace=self.authorized_workspace,
            code="SECOND", full_name="Other technician", hourly_labor_rate=100)
        client = self._browser(self.employee_user, self.authorized_workspace)
        url = f"/noibo/services/requests/{self.authorized_ticket.pk}/"
        page = client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(list(page.context["labor_technicians"]), [self.authorized_employee])
        self.assertContains(page, 'for="labor-employee"')
        self.assertNotContains(page, 'value="assign"')
        denied = client.post(url, {"action": "log_labor", "employee_id": other.pk,
                                 "task_id": self.authorized_task.pk, "duration_minutes": 30})
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(LaborEntry.objects.exists())
        allowed = client.post(url, {"action": "log_labor", "employee_id": self.authorized_employee.pk,
                                  "task_id": self.authorized_task.pk, "duration_minutes": 30})
        self.assertEqual(allowed.status_code, 302)
        entry = LaborEntry.objects.get()
        self.assertEqual(entry.employee_id, self.authorized_employee.pk)
        self.assertEqual(entry.duration_minutes, 30)
        self.assertEqual(entry.labor_cost, Decimal("75000"))

    def test_role_template_snapshots_and_manager_choices(self):
        other = Employee.objects.create(workspace=self.authorized_workspace,
            code="SECOND", full_name="Other technician", hourly_labor_rate=100)
        url = f"/noibo/services/requests/{self.authorized_ticket.pk}/"
        for name, user in (("manager", self.manager), ("technician", self.employee_user)):
            page = self._browser(user, self.authorized_workspace).get(url)
            self.assertEqual(page.status_code, 200)
            if name == "manager":
                self.assertSetEqual(set(page.context["labor_technicians"]), {other, self.authorized_employee})
                self.assertContains(page, 'value="assign"')
            evidence = getattr(settings, "EVIDENCE_REPORT_DIR", None)
            if evidence:
                directory = Path(evidence) / "service_ui"
                directory.mkdir(parents=True, exist_ok=True)
                # Synthetic test fixtures only; no sessions or business DB content.
                html = page.content.decode().replace("<body", '<body data-evidence="synthetic-test-snapshot"', 1)
                (directory / f"{name}.html").write_text(html, encoding="utf-8")
                css = directory / "static" / "css"
                css.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(settings.BASE_DIR / "static/css/style.css", css / "style.css")

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
