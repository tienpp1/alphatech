"""Focused regressions for the production internal authorization baseline."""

from django.test import Client, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


class AuthorizationConvergenceRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(
            name="Authorization Workspace",
            code="authorization-workspace",
            workspace_type=WorkspaceType.RETAIL,
        )
        view_codes = (
            "retail.view_product",
            "integration.view_datasource",
            "mapping.view_mapping",
            "knowledge.view_knowledge",
            "forecasting.view_forecast",
            "recommendations.view_recommendation",
            "approvals.view_approval",
        )
        cls.permissions = {
            code: Permission.objects.create(codename=code, name=code, module=code.split(".")[0])
            for code in view_codes
        }
        for code in (
            "integration.manage_datasource",
            "integration.execute_import",
            "mapping.manage_mapping",
            "mapping.apply_mapping",
            "knowledge.manage_knowledge",
            "forecasting.manage_forecast",
            "recommendations.manage_recommendation",
            "approvals.manage_approval",
        ):
            cls.permissions[code] = Permission.objects.create(
                codename=code, name=code, module=code.split(".")[0]
            )

        cls.viewer_role = Role.objects.create(name="CONVERGENCE_VIEWER")
        cls.viewer_role.permissions.set(
            [permission for code, permission in cls.permissions.items() if ".view_" in code]
        )
        cls.no_permission_role = Role.objects.create(name="CONVERGENCE_NO_PERMISSIONS")

        cls.viewer = User.objects.create_user(
            username="convergence_viewer", email="convergence_viewer@example.com", password="Password123!"
        )
        cls.no_permission_user = User.objects.create_user(
            username="convergence_none", email="convergence_none@example.com", password="Password123!"
        )
        cls.public_customer = User.objects.create_user(
            username="convergence_customer", email="convergence_customer@example.com", password="Password123!"
        )
        WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.viewer, role=cls.viewer_role, is_default=True
        )
        WorkspaceMembership.objects.create(
            workspace=cls.workspace,
            user=cls.no_permission_user,
            role=cls.no_permission_role,
            is_default=True,
        )

    def _browser(self, user):
        client = Client()
        client.force_login(user)
        session = client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()
        return client

    def test_viewer_can_read_internal_pages_but_mutation_controls_are_hidden(self):
        client = self._browser(self.viewer)

        sources = client.get("/integration/sources/")
        self.assertEqual(sources.status_code, 200)
        self.assertNotContains(sources, "new-source-modal")

        mapping = client.get("/mapping/")
        self.assertEqual(mapping.status_code, 200)
        self.assertNotContains(mapping, "/mapping/profiles/new/")

        knowledge = client.get("/knowledge/")
        self.assertEqual(knowledge.status_code, 200)
        self.assertNotContains(knowledge, 'name="action" value="create_kb"')
        self.assertNotContains(knowledge, 'name="action" value="upload_doc"')

        self.assertEqual(client.get("/forecasting/").status_code, 200)
        self.assertEqual(client.get("/recommendations/").status_code, 200)
        self.assertEqual(client.get("/approvals/").status_code, 200)
        self.assertEqual(client.get("/retail/products/").status_code, 200)

    def test_catalog_and_knowledge_read_do_not_grant_analytics_or_chat(self):
        client = self._browser(self.viewer)
        for path in ("/retail/", "/noibo/retail/", "/ai/", "/noibo/ai/"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 403)

        service_ws = Workspace.objects.create(code="service-catalog-only", name="Service", workspace_type=WorkspaceType.SERVICE)
        permission = Permission.objects.create(codename="service.view_service", name="Service catalog", module="service")
        self.viewer_role.permissions.add(permission)
        WorkspaceMembership.objects.create(workspace=service_ws, user=self.viewer, role=self.viewer_role)
        for path in ("/services/", "/noibo/services/"):
            self.assertEqual(client.get(path, HTTP_X_WORKSPACE_ID=str(service_ws.pk)).status_code, 403)

    def test_member_without_capability_is_denied_before_read_or_mutation(self):
        api = APIClient()
        api.force_authenticate(self.no_permission_user)
        headers = {"HTTP_X_WORKSPACE_ID": str(self.workspace.id)}

        self.assertEqual(api.get("/api/v1/recommendations/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/approvals/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/integration/data-sources/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/mapping/profiles/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/retail/products/", **headers).status_code, 403)

    def test_public_customer_cannot_use_legacy_header_for_internal_apis(self):
        api = APIClient()
        api.force_authenticate(self.public_customer)
        headers = {"HTTP_X_WORKSPACE": self.workspace.code}

        self.assertEqual(api.get("/api/v1/recommendations/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/approvals/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/knowledge/bases/", **headers).status_code, 403)
        self.assertEqual(api.get("/api/v1/forecasting/models/", **headers).status_code, 403)
