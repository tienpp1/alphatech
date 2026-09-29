from django.test import TestCase, override_settings
from apps.accounts.management.commands.seed_demo import seed_demo_identities
from apps.accounts.models import User
from apps.accounts.services import has_workspace_permission
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(DEBUG=True)
class WorkspaceRoleAcceptanceMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_demo_identities()

    def test_seeded_retail_role_matrix(self):
        workspace = Workspace.objects.get(code="abc-retail")
        expected = {
            "retail.view_product": (True, True, True, True),
            "retail.create_order": (True, True, True, False),
            "retail.manage_product": (True, True, False, False),
            "approvals.view_approval": (True, True, False, False),
            "approvals.manage_approval": (True, True, False, False),
            "ai.chat": (True, True, True, False),
            "accounts.manage_user": (True, False, False, False),
            "forecasting.manage_forecast": (True, True, False, False),
        }
        for index, username in enumerate(("admin", "manager", "employee", "viewer")):
            user = User.objects.get(username=username)
            for permission, allowed in expected.items():
                with self.subTest(user=username, permission=permission):
                    self.assertEqual(has_workspace_permission(user, workspace, permission), allowed[index])

    def test_seeded_service_memberships_are_not_retail_roles(self):
        workspace = Workspace.objects.get(code="xyz-service")
        for username, role in (("manager", "EMPLOYEE"), ("employee", "EMPLOYEE"), ("viewer", "VIEWER")):
            user = User.objects.get(username=username)
            self.assertEqual(WorkspaceMembership.objects.get(user=user, workspace=workspace).role.name, role)
            self.assertTrue(has_workspace_permission(user, workspace, "service.view_request"))
            self.assertFalse(has_workspace_permission(user, workspace, "service.manage_request"))
            self.assertFalse(has_workspace_permission(user, workspace, "service.manage_task"))
            self.assertFalse(has_workspace_permission(user, workspace, "service.assign_request"))
            self.assertFalse(has_workspace_permission(user, workspace, "service.view_analytics"))
            is_employee = role == "EMPLOYEE"
            self.assertEqual(has_workspace_permission(user, workspace, "service.create_request"), is_employee)
            self.assertEqual(has_workspace_permission(user, workspace, "service.view_task"), is_employee)
            self.assertEqual(has_workspace_permission(user, workspace, "service.view_schedule"), is_employee)

    def test_public_and_inactive_membership_denied(self):
        workspace = Workspace.objects.get(code="abc-retail")
        customer = User.objects.create_user(username="public", email="public@example.com")
        self.assertFalse(has_workspace_permission(customer, workspace, "retail.view_product"))
        user = User.objects.get(username="employee")
        WorkspaceMembership.objects.filter(user=user, workspace=workspace).update(is_active=False)
        self.assertFalse(has_workspace_permission(user, workspace, "retail.view_product"))
