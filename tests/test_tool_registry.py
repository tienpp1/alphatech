"""
Test suite for Controlled Tool Registry & Execution Security (Phase 10).
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.approvals.registry import ToolRegistry, ToolPermissionDenied, ToolValidationError
from apps.approvals.executor import execute_tool
from apps.approvals.models import ApprovalRequest, ApprovalStatus


class ToolRegistryTests(TestCase):
    def setUp(self):
        self.workspace_retail = Workspace.objects.create(
            name="Retail Registry Test",
            code="retail-reg",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.user_admin = User.objects.create_superuser(
            username="reg_admin",
            email="admin@example.com",
            password="AdminPassword123!",
        )
        self.user_unauthorized = User.objects.create_user(
            username="unauth_user",
            email="unauth@example.com",
            password="UserPass123!",
        )

        self.client = APIClient()

    def test_tool_registry_lists_all_tools(self):
        """Verify registry lists all registered READ and MUTATION tools."""
        tools = ToolRegistry.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("get_sales_summary", names)
        self.assertIn("dispatch_technician", names)
        self.assertIn("update_order_status", names)

    def test_execute_read_tool_immediate(self):
        """Verify READ tools execute immediately for authorized user."""
        res = execute_tool(
            name="get_sales_summary",
            workspace=self.workspace_retail,
            user=self.user_admin,
            parameters={}
        )
        self.assertEqual(res["status"], "EXECUTED")
        self.assertEqual(res["classification"], "READ")
        self.assertIn("total_revenue", res["result"])

    def test_execute_mutation_tool_redirects_to_approval(self):
        """Verify MUTATION tools submit a PENDING ApprovalRequest."""
        res = execute_tool(
            name="create_promotion_request",
            workspace=self.workspace_retail,
            user=self.user_admin,
            parameters={"promotion_name": "Summer Special", "discount_pct": 20},
            idempotency_key="IK-PROMO-123"
        )
        self.assertEqual(res["status"], "APPROVAL_REQUIRED")
        self.assertEqual(res["classification"], "MUTATION")
        self.assertIn("approval_request_id", res)

        app_req = ApprovalRequest.objects.get(id=res["approval_request_id"])
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)
        self.assertEqual(app_req.proposed_action, "create_promotion_request")

    def test_unregistered_tool_rejected(self):
        """Verify unknown tool execution raises ToolValidationError."""
        with self.assertRaises(ToolValidationError):
            execute_tool(
                name="non_existent_tool",
                workspace=self.workspace_retail,
                user=self.user_admin,
                parameters={}
            )

    def test_unauthorized_tool_execution_denied(self):
        """Verify user without permission is denied tool execution."""
        with self.assertRaises(ToolPermissionDenied):
            execute_tool(
                name="create_promotion_request",
                workspace=self.workspace_retail,
                user=self.user_unauthorized,
                parameters={"promotion_name": "Hack Sale"}
            )
