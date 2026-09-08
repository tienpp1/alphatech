"""
Test suite for Approval Requests & Idempotency Workflow (Phase 10).
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.approvals.models import ApprovalRequest, ApprovalStatus, RiskLevel
from apps.approvals.executor import process_approval_decision, execute_tool
from apps.approvals.registry import ToolPermissionDenied, ToolValidationError


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Approval WS Test",
            code="approval-test",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.user_requester = User.objects.create_user(
            username="app_requester",
            email="req@example.com",
            password="Password123!",
        )
        self.user_manager = User.objects.create_user(
            username="app_manager",
            email="mgr@example.com",
            password="Password123!",
        )

        self.perm_manage, _ = Permission.objects.get_or_create(
            codename="approvals.manage_approval",
            defaults={"name": "Manage Approvals", "module": "approvals"}
        )
        self.role_mgr = Role.objects.create(name="AppManager")
        self.role_mgr.permissions.add(self.perm_manage)

        WorkspaceMembership.objects.create(
            user=self.user_manager,
            workspace=self.workspace,
            role=self.role_mgr,
        )

        self.client = APIClient()

    def test_approval_request_lifecycle_approved(self):
        """Verify pending request -> approval -> execution."""
        app_req = ApprovalRequest.objects.create(
            workspace=self.workspace,
            requester=self.user_requester,
            proposed_action="create_promotion_request",
            parameters={"promotion_name": "Test Sale 2026", "discount_pct": 15},
            reason="Test mutation",
            risk_level=RiskLevel.MEDIUM,
            status=ApprovalStatus.PENDING,
            idempotency_key="IK-TEST-001",
        )

        # Manager approves
        res = process_approval_decision(
            approval_request=app_req,
            reviewer=self.user_manager,
            decision="APPROVED",
            decision_reason="Looks good"
        )
        self.assertEqual(res["status"], "EXECUTED")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.EXECUTED)
        self.assertIsNotNone(app_req.execution_result)
        self.assertEqual(app_req.execution_result["status"], "SUCCESS")

    def test_approval_request_lifecycle_rejected(self):
        """Verify pending request -> rejection."""
        app_req = ApprovalRequest.objects.create(
            workspace=self.workspace,
            requester=self.user_requester,
            proposed_action="create_promotion_request",
            parameters={"promotion_name": "Test Sale Bad", "discount_pct": 50},
            reason="Test bad mutation",
            status=ApprovalStatus.PENDING,
            idempotency_key="IK-TEST-002",
        )

        res = process_approval_decision(
            approval_request=app_req,
            reviewer=self.user_manager,
            decision="REJECTED",
            decision_reason="Discount too high"
        )
        self.assertEqual(res["status"], "REJECTED")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.REJECTED)

    def test_idempotency_replay_protection(self):
        """Verify an already EXECUTED approval request cannot be re-executed twice."""
        app_req = ApprovalRequest.objects.create(
            workspace=self.workspace,
            requester=self.user_requester,
            proposed_action="create_promotion_request",
            parameters={"promotion_name": "Test Replay", "discount_pct": 10},
            status=ApprovalStatus.PENDING,
            idempotency_key="IK-REPLAY-999",
        )

        # First execution
        res1 = process_approval_decision(app_req, self.user_manager, "APPROVED")
        self.assertEqual(res1["status"], "EXECUTED")

        # Second execution attempt returns cached result without repeating mutation
        res2 = process_approval_decision(app_req, self.user_manager, "APPROVED")
        self.assertEqual(res2["status"], "EXECUTED")
        self.assertTrue(res2.get("idempotent_replay", False))

    def test_requester_cannot_self_approve(self):
        """Verify requester cannot self-approve own request (separation of duties)."""
        app_req = ApprovalRequest.objects.create(
            workspace=self.workspace,
            requester=self.user_manager,  # Manager is requester
            proposed_action="create_promotion_request",
            parameters={"promotion_name": "Self Approve Test"},
            status=ApprovalStatus.PENDING,
            idempotency_key="IK-SELF-001",
        )

        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(app_req, self.user_manager, "APPROVED")
