"""
End-to-end integration tests for Phase 10 (Recommendations, Approvals, Tool Registry & AI Integration).
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.recommendations.models import Recommendation, RecommendationType, RecommendationStatus
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.audit.models import AuditLog


class Phase10IntegrationTests(TestCase):
    def setUp(self):
        self.workspace_retail = Workspace.objects.create(
            name="Retail Integration WS",
            code="retail-int",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.user_admin = User.objects.create_superuser(
            username="int_admin",
            email="admin_int@example.com",
            password="AdminPassword123!",
        )

        self.client = APIClient()

    def test_full_recommendation_and_approval_flow(self):
        """End-to-end test: Evaluate recommendations -> Accept -> Execute mutation via approval -> Audit log."""
        # 1. Trigger recommendation evaluation via API
        self.client.force_authenticate(user=self.user_admin)
        eval_res = self.client.post("/api/v1/recommendations/evaluate/")
        self.assertEqual(eval_res.status_code, status.HTTP_200_OK)
        self.assertTrue(eval_res.data["success"])

        # 2. Query recommendations list
        list_res = self.client.get("/api/v1/recommendations/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        recs = list_res.data["data"]
        self.assertTrue(len(recs) > 0)
        rec_id = recs[0]["id"]

        # 3. Accept recommendation
        accept_res = self.client.post(
            f"/api/v1/recommendations/{rec_id}/accept/",
            {"decision_reason": "Accepted during integration test"},
            format="json"
        )
        self.assertEqual(accept_res.status_code, status.HTTP_200_OK)
        self.assertEqual(accept_res.data["data"]["status"], "ACCEPTED")

        # 4. Trigger mutation tool (e.g. create_promotion_request) -> generates PENDING ApprovalRequest
        tool_res = self.client.post(
            "/api/v1/tools/create_promotion_request/execute/",
            {"parameters": {"promotion_name": "Integration Sale", "discount_pct": 20}, "idempotency_key": "IK-INT-001"},
            format="json"
        )
        self.assertEqual(tool_res.status_code, status.HTTP_200_OK)
        self.assertEqual(tool_res.data["data"]["status"], "APPROVAL_REQUIRED")
        approval_id = tool_res.data["data"]["approval_request_id"]

        # 5. Manager approves mutation request
        decision_res = self.client.post(
            f"/api/v1/approvals/{approval_id}/decision/",
            {"decision": "APPROVED", "decision_reason": "Manager approved integration test"},
            format="json"
        )
        self.assertEqual(decision_res.status_code, status.HTTP_200_OK)
        self.assertEqual(decision_res.data["data"]["status"], "EXECUTED")

        # 6. Verify audit logs recorded for recommendation acceptance and mutation execution
        audit_records = AuditLog.objects.filter(workspace=self.workspace_retail)
        actions = [a.action for a in audit_records]
        self.assertIn("RECOMMENDATION_ACCEPTED", actions)
        self.assertIn("MUTATION_EXECUTED", actions)
