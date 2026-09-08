"""
Unit & Integration Tests for Ingestion Security, Tenancy Isolation, RBAC, and Audit Logging.
"""

from django.test import TestCase, Client
from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.integration.models import DataSource, ImportJob, RawImportRecord, SourceType
from apps.integration.services import create_data_source, execute_import_job
from apps.audit.models import AuditLog


class IntegrationSecurityAndRBACTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Permissions
        self.perm_view = Permission.objects.create(codename="integration.view_datasource", name="View DS", module="integration")
        self.perm_manage = Permission.objects.create(codename="integration.manage_datasource", name="Manage DS", module="integration")
        self.perm_import = Permission.objects.create(codename="integration.execute_import", name="Execute Import", module="integration")

        # Roles
        self.admin_role = Role.objects.create(name="ADMIN", description="Admin")
        self.manager_role = Role.objects.create(name="MANAGER", description="Manager")
        self.viewer_role = Role.objects.create(name="VIEWER", description="Viewer")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage, self.perm_import)
        self.manager_role.permissions.add(self.perm_view, self.perm_manage, self.perm_import)
        self.viewer_role.permissions.add(self.perm_view)

        # Workspaces
        self.ws_a = Workspace.objects.create(name="Workspace Alpha", code="ws-alpha", workspace_type=WorkspaceType.RETAIL)
        self.ws_b = Workspace.objects.create(name="Workspace Beta", code="ws-beta", workspace_type=WorkspaceType.SERVICE)

        # Users
        self.user_admin = User.objects.create_user(username="admin_user", email="admin_user@example.com", password="Pass123!Admin")
        self.user_manager = User.objects.create_user(username="manager_user", email="manager_user@example.com", password="Pass123!Manager")
        self.user_viewer = User.objects.create_user(username="viewer_user", email="viewer_user@example.com", password="Pass123!Viewer")
        self.user_outsider = User.objects.create_user(username="outsider_user", email="outsider_user@example.com", password="Pass123!Outsider")

        # Memberships in WS Alpha
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.user_admin, role=self.admin_role, is_default=True)
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.user_manager, role=self.manager_role, is_default=True)
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.user_viewer, role=self.viewer_role, is_default=True)

        # Membership in WS Beta for outsider
        WorkspaceMembership.objects.create(workspace=self.ws_b, user=self.user_outsider, role=self.admin_role, is_default=True)

    def test_workspace_isolation_data_sources(self):
        # Create datasource in WS Alpha
        ds_a = DataSource.objects.create(
            workspace=self.ws_a,
            name="Alpha Source",
            source_type=SourceType.CSV,
            created_by=self.user_admin,
        )

        # Create datasource in WS Beta
        ds_b = DataSource.objects.create(
            workspace=self.ws_b,
            name="Beta Source",
            source_type=SourceType.MOCK_API,
            created_by=self.user_outsider,
        )

        # User in WS Alpha queries data sources
        self.client.force_login(self.user_admin)
        res = self.client.get("/api/v1/integration/data-sources/", HTTP_X_WORKSPACE_ID=str(self.ws_a.id))
        self.assertEqual(res.status_code, 200)
        source_names = [d["name"] for d in res.json()["data"]]
        self.assertIn("Alpha Source", source_names)
        self.assertNotIn("Beta Source", source_names)

        # User in WS Alpha cannot GET WS Beta's datasource
        res_cross = self.client.get(f"/api/v1/integration/data-sources/{ds_b.id}/", HTTP_X_WORKSPACE_ID=str(self.ws_a.id))
        self.assertEqual(res_cross.status_code, 404)

    def test_rbac_viewer_cannot_create_data_source(self):
        self.client.force_login(self.user_viewer)
        res = self.client.post(
            "/api/v1/integration/data-sources/",
            {"name": "Viewer Hack Source", "source_type": "CSV"},
            HTTP_X_WORKSPACE_ID=str(self.ws_a.id),
        )
        self.assertEqual(res.status_code, 403)
        self.assertFalse(DataSource.objects.filter(name="Viewer Hack Source").exists())

    def test_rbac_manager_can_create_data_source(self):
        import json
        self.client.force_login(self.user_manager)
        payload = json.dumps({"name": "Manager POS CSV", "source_type": "CSV", "connection_config": {"delimiter": ","}})
        res = self.client.post(
            "/api/v1/integration/data-sources/",
            payload,
            content_type="application/json",
            HTTP_X_WORKSPACE_ID=str(self.ws_a.id),
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["data"]["name"], "Manager POS CSV")

    def test_unauthenticated_api_rejection(self):
        res = self.client.get("/api/v1/integration/data-sources/")
        self.assertEqual(res.status_code, 401)

    def test_audit_log_created_on_data_source_and_import(self):
        # Create datasource
        ds = create_data_source(
            workspace=self.ws_a,
            user=self.user_admin,
            name="Audited Source",
            source_type=SourceType.MOCK_API,
            connection_config={"url": "/api/v1/mock-external/retail/orders/"},
        )

        create_log = AuditLog.objects.filter(entity_type="DataSource", entity_id=str(ds.id), action="CREATE").first()
        self.assertIsNotNone(create_log)
        self.assertEqual(create_log.actor_user, self.user_admin)

        # Execute import
        job = execute_import_job(workspace=self.ws_a, user=self.user_admin, data_source=ds)

        import_log = AuditLog.objects.filter(entity_type="ImportJob", entity_id=str(job.id), action="IMPORT_COMPLETED").first()
        self.assertIsNotNone(import_log)
        self.assertEqual(import_log.actor_user, self.user_admin)

    def test_ui_views_authenticated(self):
        self.client.force_login(self.user_admin)

        # 1. Dashboard
        res = self.client.get("/integration/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Data Integration")

        # 2. Sources
        res = self.client.get("/integration/sources/")
        self.assertEqual(res.status_code, 200)

        # 3. Import Wizard
        res = self.client.get("/integration/import/")
        self.assertEqual(res.status_code, 200)

        # 4. Jobs
        res = self.client.get("/integration/jobs/")
        self.assertEqual(res.status_code, 200)
