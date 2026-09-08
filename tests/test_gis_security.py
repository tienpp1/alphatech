"""
tests.test_gis_security - Workspace Tenancy Isolation, RBAC & Customer Spatial PII Protection Tests.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.retail.models import Branch, Customer, CustomerSegment


class GISSecurityAndIsolationTests(TestCase):
    def setUp(self):
        # Workspace A (Retail)
        self.workspace_a = Workspace.objects.create(
            name="Workspace Alpha",
            code="workspace-alpha",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Workspace B (Retail - Isolated)
        self.workspace_b = Workspace.objects.create(
            name="Workspace Beta",
            code="workspace-beta",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Permissions
        self.perm_view_gis, _ = Permission.objects.get_or_create(
            codename="gis.view_spatial_layers",
            defaults={"name": "View GIS", "module": "gis"},
        )
        self.perm_view_pii, _ = Permission.objects.get_or_create(
            codename="gis.view_customer_locations",
            defaults={"name": "View Customer PII", "module": "gis"},
        )

        # Roles
        self.role_manager, _ = Role.objects.get_or_create(name="MANAGER_TEST")
        self.role_manager.permissions.set([self.perm_view_gis, self.perm_view_pii])

        self.role_viewer, _ = Role.objects.get_or_create(name="VIEWER_TEST")
        self.role_viewer.permissions.set([self.perm_view_gis])

        # Users
        self.manager_user = User.objects.create_user(
            username="gis_manager",
            email="manager@alpha.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.manager_user,
            workspace=self.workspace_a,
            role=self.role_manager,
            is_default=True,
        )

        self.viewer_user = User.objects.create_user(
            username="gis_viewer",
            email="viewer@alpha.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.viewer_user,
            workspace=self.workspace_a,
            role=self.role_viewer,
            is_default=True,
        )

        # Entities in Workspace A
        self.branch_a = Branch.objects.create(
            workspace=self.workspace_a,
            code="BR-A1",
            name="Branch Alpha 1",
            region="District 1",
            location=Point(106.7000, 10.7700, srid=4326),
        )
        self.cust_a = Customer.objects.create(
            workspace=self.workspace_a,
            code="CUST-A1",
            name="Alice Sensitive",
            phone="0912345678",
            email="alice@sensitivedata.com",
            address="123 Private Street, D1",
            customer_segment=CustomerSegment.VIP,
            location=Point(106.7010, 10.7710, srid=4326),
        )

        # Entities in Workspace B (Cross-workspace)
        self.branch_b = Branch.objects.create(
            workspace=self.workspace_b,
            code="BR-B1",
            name="Branch Beta 1",
            region="District 7",
            location=Point(106.7200, 10.7300, srid=4326),
        )
        self.cust_b = Customer.objects.create(
            workspace=self.workspace_b,
            code="CUST-B1",
            name="Bob Secret",
            location=Point(106.7210, 10.7310, srid=4326),
        )

        self.client = APIClient()

    def test_workspace_isolation_in_gis_endpoints(self):
        """Verifies spatial endpoints strictly filter by active workspace_id."""
        self.client.force_authenticate(user=self.manager_user)

        # Requesting Workspace A
        resp = self.client.get("/api/v1/gis/retail/branches/", HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        codes_a = [f["properties"]["code"] for f in resp.json()["data"]["features"]]
        self.assertIn("BR-A1", codes_a)
        self.assertNotIn("BR-B1", codes_a)

        # User is not a member of Workspace B - accessing Workspace B must be rejected
        resp_b = self.client.get("/api/v1/gis/retail/branches/", HTTP_X_WORKSPACE_ID=str(self.workspace_b.id))
        self.assertEqual(resp_b.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gis_access_rejected(self):
        """Verifies unauthenticated access to GIS APIs is rejected with 401."""
        resp = self.client.get("/api/v1/gis/retail/branches/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_pii_privacy_masking_for_viewer_vs_manager(self):
        """
        Verifies that viewers receive masked customer names & addresses,
        while managers with 'gis.view_customer_locations' receive full unmasked PII.
        """
        # 1. Viewer test (Masked PII)
        self.client.force_authenticate(user=self.viewer_user)
        resp_viewer = self.client.get("/api/v1/gis/retail/customers/", HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(resp_viewer.status_code, status.HTTP_200_OK)
        data_viewer = resp_viewer.json()["data"]
        feat_viewer = data_viewer["features"][0]
        self.assertEqual(feat_viewer["properties"]["name"], "Customer CUST-A1")  # Masked
        self.assertEqual(feat_viewer["properties"]["address"], "Restricted (Address Protected)")  # Masked
        self.assertNotIn("phone", feat_viewer["properties"])
        self.assertNotIn("email", feat_viewer["properties"])
        self.assertTrue(data_viewer["metadata"]["pii_masked"])

        # 2. Manager test (Unmasked PII)
        self.client.force_authenticate(user=self.manager_user)
        resp_manager = self.client.get("/api/v1/gis/retail/customers/", HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(resp_manager.status_code, status.HTTP_200_OK)
        data_manager = resp_manager.json()["data"]
        feat_manager = data_manager["features"][0]
        self.assertEqual(feat_manager["properties"]["name"], "Alice Sensitive")  # Unmasked
        self.assertEqual(feat_manager["properties"]["phone"], "0912345678")
        self.assertEqual(feat_manager["properties"]["email"], "alice@sensitivedata.com")
        self.assertEqual(feat_manager["properties"]["address"], "123 Private Street, D1")
        self.assertFalse(data_manager["metadata"]["pii_masked"])
