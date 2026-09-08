"""
Security, Workspace Isolation & Audit Log Verification Tests for Data Mapping.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.audit.models import AuditLog
from apps.integration.models import DataSource, SourceType, ImportJob, RawImportRecord
from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    accept_ai_mapping_rule,
    reject_ai_mapping_rule,
)


class MappingSecurityTestCase(TestCase):
    def setUp(self):
        # Workspace A
        self.ws_a = Workspace.objects.create(name="Workspace A", code="ws-a", workspace_type=WorkspaceType.RETAIL)
        # Workspace B
        self.ws_b = Workspace.objects.create(name="Workspace B", code="ws-b", workspace_type=WorkspaceType.RETAIL)

        self.user_a = User.objects.create_user(username="user_a", email="usera@example.com")
        self.user_viewer = User.objects.create_user(username="viewer_user", email="viewer@example.com")

        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_viewer = Role.objects.create(name="VIEWER")

        # Give view permission to VIEWER
        perm_view, _ = Permission.objects.get_or_create(codename="mapping.view_mapping", defaults={"name": "View Mapping", "module": "mapping"})
        perm_manage, _ = Permission.objects.get_or_create(codename="mapping.manage_mapping", defaults={"name": "Manage Mapping", "module": "mapping"})
        perm_apply, _ = Permission.objects.get_or_create(codename="mapping.apply_mapping", defaults={"name": "Apply Mapping", "module": "mapping"})
        self.role_viewer.permissions.add(perm_view)
        self.role_admin.permissions.add(perm_view, perm_manage, perm_apply)

        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.user_a, role=self.role_admin, is_default=True)
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.user_viewer, role=self.role_viewer, is_default=True)

        self.profile_a = create_mapping_profile(self.ws_a, self.user_a, "Profile WS A", "Order")
        self.profile_b = create_mapping_profile(self.ws_b, self.user_a, "Profile WS B", "Order")

        self.client = APIClient()

    def test_workspace_isolation_cross_tenant_access_blocked(self):
        """Verifies a user in Workspace A cannot access or see profiles belonging to Workspace B."""
        self.client.force_authenticate(user=self.user_a)

        # GET detail of Profile B with Workspace A header -> 404 Not Found
        url = f"/api/v1/mapping/profiles/{self.profile_b.id}/"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.ws_a.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # List profiles with Workspace A header -> Profile B must not be in results
        list_url = "/api/v1/mapping/profiles/"
        resp_list = self.client.get(list_url, HTTP_X_WORKSPACE_ID=str(self.ws_a.id))
        self.assertEqual(resp_list.status_code, status.HTTP_200_OK)
        returned_ids = [p["id"] for p in resp_list.data["data"]]
        self.assertIn(str(self.profile_a.id), returned_ids)
        self.assertNotIn(str(self.profile_b.id), returned_ids)

    def test_rbac_viewer_cannot_create_or_apply_profiles(self):
        """Verifies VIEWER role cannot create or modify mapping profiles."""
        self.client.force_authenticate(user=self.user_viewer)

        create_url = "/api/v1/mapping/profiles/"
        resp = self.client.post(
            create_url,
            {"name": "Unauthorized Profile", "target_entity": "Order"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.ws_a.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_logging_lifecycle(self):
        """Verifies AuditLog records are written for profile creation, rule addition, and AI review."""
        AuditLog.objects.all().delete()

        profile = create_mapping_profile(self.ws_a, self.user_a, "Audited Profile", "Customer")
        self.assertTrue(AuditLog.objects.filter(action="MAPPING_PROFILE_CREATED", entity_id=str(profile.id)).exists())

        rule = add_mapping_rule(
            profile=profile,
            user=self.user_a,
            source_field="ma_kh",
            target_field="customer_id",
            ai_status=AIConfirmationStatus.PENDING,
        )
        self.assertTrue(AuditLog.objects.filter(action="MAPPING_RULE_ADDED", entity_id=str(rule.id)).exists())

        accept_ai_mapping_rule(rule, self.user_a)
        self.assertTrue(AuditLog.objects.filter(action="MAPPING_RULE_APPROVED", entity_id=str(rule.id)).exists())

        reject_ai_mapping_rule(rule, self.user_a)
        self.assertTrue(AuditLog.objects.filter(action="MAPPING_RULE_REJECTED", entity_id=str(rule.id)).exists())
