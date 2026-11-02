"""Actual mapping persistence and internal GIS permission/scope regressions."""
from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User
from apps.audit.models import AuditLog
from apps.integration.models import DataSource, ImportJob, RawImportRecord
from apps.mapping.services import add_mapping_rule, apply_mapping_to_domain, create_mapping_profile, generate_mapping_preview
from apps.retail.models import Branch, Customer
from apps.service_ops.models import Employee, Service, ServiceRequest, Task
from apps.workspaces.models import Workspace, WorkspaceMembership


class DefenseMappingGISRegressionTests(TestCase):
    def setUp(self):
        self.retail = Workspace.objects.create(name="Retail", code="def-retail", workspace_type="RETAIL")
        self.service = Workspace.objects.create(name="Service", code="def-service", workspace_type="SERVICE")
        self.role = Role.objects.create(name="MANAGER")
        for code in ("gis.view_spatial_layers", "mapping.view_mapping", "mapping.apply_mapping"):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split('.')[0]})
            self.role.permissions.add(permission)
        self.user = User.objects.create_user(username="defmanager", email="defmanager@example.test", is_staff=True)
        WorkspaceMembership.objects.create(workspace=self.retail, user=self.user, role=self.role, is_default=True)
        WorkspaceMembership.objects.create(workspace=self.service, user=self.user, role=self.role)
        self.customer = Customer.objects.create(workspace=self.retail, code="PRIVATE", name="Private Name", address="Private Address", phone="0901234567", email="private@example.test", location=Point(106.7, 10.7))
        Branch.objects.create(workspace=self.retail, code="BR", name="Retail Branch", location=Point(106.7, 10.7))
        customer = Customer.objects.create(workspace=self.service, code="SVC-C", name="Service Customer")
        service = Service.objects.create(workspace=self.service, code="SVC", name="Installation")
        self.ticket = ServiceRequest.objects.create(workspace=self.service, customer=customer, service=service, request_number="SVC-TICKET", title="Service ticket", location=Point(106.7, 10.7))
        self.employee = Employee.objects.create(workspace=self.service, code="TECH", full_name="Technician", current_location=Point(106.7, 10.7))
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def task_batch(self, *, invalid=False):
        source = DataSource.objects.create(workspace=self.service, name="Tasks", source_type="CSV")
        profile = create_mapping_profile(self.service, self.user, "Task mapping", "Task", source)
        for field in ("request_number", "title", "assigned_employee_code"):
            add_mapping_rule(profile, self.user, field, field)
        job = ImportJob.objects.create(workspace=self.service, data_source=source, total_rows=1)
        RawImportRecord.objects.create(workspace=self.service, import_job=job, row_number=1,
            raw_data={"request_number": "SVC-TICKET", "title": "Mapped task", "assigned_employee_code": "TECH"},
            is_valid=not invalid, validation_errors=["invalid source"] if invalid else [])
        return profile, job

    def test_valid_task_preview_applies_with_real_assignment(self):
        profile, job = self.task_batch()
        preview = generate_mapping_preview(self.service, profile, import_job=job)
        self.assertTrue(preview["is_valid"])
        result = apply_mapping_to_domain(self.service, self.user, profile, job, strict=True)
        self.assertEqual(result["status"], "COMPLETED", result)
        task = Task.objects.get(service_request=self.ticket, title="Mapped task")
        self.assertEqual(task.assigned_to, self.employee)
        self.assertTrue(AuditLog.objects.filter(workspace=self.service, action="MAPPING_APPLIED").exists())

    def test_invalid_task_strict_batch_keeps_domain_unchanged(self):
        profile, job = self.task_batch(invalid=True)
        result = apply_mapping_to_domain(self.service, self.user, profile, job, strict=True)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["inserted_count"], 0)
        self.assertFalse(Task.objects.filter(service_request=self.ticket).exists())

    def test_partial_task_batch_api_retains_rejection_row_details(self):
        profile, job = self.task_batch()
        RawImportRecord.objects.create(workspace=self.service, import_job=job, row_number=2,
            raw_data={"title": "Rejected task"}, is_valid=False, validation_errors=["invalid source"])
        response = self.api.post("/api/v1/mapping/apply/", {
            "profile_id": str(profile.pk), "import_job_id": str(job.pk), "strict": False,
        }, format="json", HTTP_X_WORKSPACE_ID=str(self.service.pk))
        self.assertEqual(response.status_code, 200)
        result = response.json()["data"]
        self.assertEqual((result["status"], result["inserted_count"], result["failed_count"]), ("PARTIAL", 1, 1))
        self.assertEqual(result["errors"][0]["row"], 2)
        self.assertEqual(result["errors"][0]["errors"][0]["code"], "INVALID_STAGED_RECORD")
        self.assertEqual(Task.objects.get(service_request=self.ticket).assigned_to, self.employee)

    def test_zero_persisted_task_batch_retains_rejection_row_details(self):
        profile, job = self.task_batch(invalid=True)
        result = apply_mapping_to_domain(self.service, self.user, profile, job, strict=False)
        self.assertEqual((result["status"], result["inserted_count"], result["failed_count"]), ("PARTIAL", 0, 1))
        self.assertEqual(result["errors"][0]["row"], 1)
        self.assertEqual(result["errors"][0]["errors"][0]["code"], "INVALID_STAGED_RECORD")
        self.assertFalse(Task.objects.filter(service_request=self.ticket).exists())

    def test_staff_without_workspace_pii_grant_remains_masked(self):
        response = self.api.get("/api/v1/gis/retail/customers/", HTTP_X_WORKSPACE_ID=str(self.retail.pk))
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["metadata"]["pii_masked"])
        properties = data["features"][0]["properties"]
        self.assertEqual(properties["name"], "Customer PRIVATE")
        self.assertEqual(properties["address"], "Restricted (Address Protected)")
        self.assertNotIn("phone", properties)
        self.assertNotIn("email", properties)

    def test_explicit_pii_grants_and_superuser_remain_supported(self):
        for code in ("gis.view_customer_locations", "retail.manage_customer"):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split('.')[0]})
            self.role.permissions.add(permission)
            response = self.api.get("/api/v1/gis/retail/customers/", HTTP_X_WORKSPACE_ID=str(self.retail.pk))
            self.assertFalse(response.json()["data"]["metadata"]["pii_masked"])
            self.assertEqual(response.json()["data"]["features"][0]["properties"]["phone"], "0901234567")
            self.role.permissions.remove(permission)
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        response = self.api.get("/api/v1/gis/retail/customers/", HTTP_X_WORKSPACE_ID=str(self.retail.pk))
        self.assertFalse(response.json()["data"]["metadata"]["pii_masked"])

    def test_opposite_domain_page_and_explicit_layer_context(self):
        client = Client()
        client.force_login(self.user)
        for active, target, page, endpoint, expected in (
            (self.retail, self.service, "/noibo/services/gis/", "/api/v1/gis/service/tickets/", "SVC-TICKET"),
            (self.service, self.retail, "/noibo/retail/gis/", "/api/v1/gis/retail/branches/", "Retail Branch"),
        ):
            session = client.session
            session["active_workspace_id"] = str(active.pk)
            session.save()
            response = client.get(page)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["active_workspace"], target)
            response = client.get(endpoint, HTTP_X_WORKSPACE_ID=str(target.pk))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected)
        foreign = Workspace.objects.create(name="Foreign", code="def-foreign", workspace_type="SERVICE")
        self.assertEqual(client.get("/api/v1/gis/service/tickets/", HTTP_X_WORKSPACE_ID=str(foreign.pk)).status_code, 403)
