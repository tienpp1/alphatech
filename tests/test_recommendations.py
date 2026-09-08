"""
Test suite for Business Recommendations Engine (Phase 10).
"""

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationPriority
from apps.recommendations.scoring import calculate_technician_score
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.retail.models import Customer
from apps.service_ops.models import Employee, Service, ServiceCategory, ServiceRequest


class RecommendationEngineTests(TestCase):
    def setUp(self):
        self.workspace_retail = Workspace.objects.create(
            name="Retail WS Test",
            code="retail-test",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.workspace_service = Workspace.objects.create(
            name="Service WS Test",
            code="service-test",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.user_manager = User.objects.create_user(
            username="rec_manager",
            email="rec_mgr@example.com",
            password="Password123!",
        )
        self.user_employee = User.objects.create_user(
            username="rec_employee",
            email="rec_emp@example.com",
            password="Password123!",
        )

        self.perm_manage, _ = Permission.objects.get_or_create(
            codename="recommendations.manage_recommendation",
            defaults={"name": "Manage Recommendations", "module": "recommendations"}
        )
        self.perm_assign, _ = Permission.objects.get_or_create(
            codename="service.assign_request",
            defaults={"name": "Assign Service Requests", "module": "service"},
        )
        self.role_manager = Role.objects.create(name="RecManager")
        self.role_manager.permissions.add(self.perm_manage, self.perm_assign)

        WorkspaceMembership.objects.create(
            user=self.user_manager,
            workspace=self.workspace_retail,
            role=self.role_manager,
        )

        self.service = Service.objects.create(
            workspace=self.workspace_service,
            code="REC-SVC-001",
            name="Recommendation test service",
            category=ServiceCategory.DATABASE_CONSULTING,
            base_fee=Decimal("0.00"),
        )
        self.customer = Customer.objects.create(
            workspace=self.workspace_service,
            code="REC-CUST-001",
            name="Recommendation test customer",
        )
        self.employee = Employee.objects.create(
            workspace=self.workspace_service,
            code="REC-EMP-001",
            full_name="Recommendation technician",
            email="rec-tech@example.com",
        )
        self.ticket = ServiceRequest.objects.create(
            workspace=self.workspace_service,
            customer=self.customer,
            service=self.service,
            request_number="REC-TICKET-001",
            title="Recommendation test ticket",
            description="Ticket used to validate action contracts.",
        )
        WorkspaceMembership.objects.create(
            user=self.user_manager,
            workspace=self.workspace_service,
            role=self.role_manager,
        )

        self.client = APIClient()

    def test_technician_candidate_scoring_formula(self):
        """Verify candidate scoring formula calculation and subscores."""
        score_res = calculate_technician_score(distance_km=5.0, active_tasks=1, has_matching_skill=True)
        # S_dist = max(0, 100 - 5*10) = 50
        # S_workload = max(0, 100 - 1*20) = 80
        # S_skill = 100
        # Total = 0.4*50 + 0.4*80 + 0.2*100 = 20 + 32 + 20 = 72.0
        self.assertEqual(score_res["score"], 72.0)
        self.assertEqual(score_res["subscores"]["distance_score"], 50.0)
        self.assertEqual(score_res["subscores"]["workload_score"], 80.0)
        self.assertEqual(score_res["subscores"]["skill_score"], 100.0)

    def test_retail_rule_evaluation(self):
        """Verify retail rules evaluate and generate recommendations."""
        recs = evaluate_retail_recommendations(self.workspace_retail)
        self.assertTrue(len(recs) > 0)
        rec = recs[0]
        self.assertEqual(rec.workspace, self.workspace_retail)
        self.assertIn("what", rec.explanation)
        self.assertIn("why", rec.explanation)
        self.assertIn("evidence", rec.explanation)

    def test_service_rule_evaluation(self):
        """Verify service rules evaluate and generate recommendations."""
        recs = evaluate_service_recommendations(self.workspace_service)
        # Empty service workspace creates no recs by default
        self.assertEqual(len(recs), 0)

    def test_recommendation_accept_api(self):
        """Verify accepting a recommendation updates status to ACCEPTED."""
        rec = Recommendation.objects.create(
            workspace=self.workspace_retail,
            recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
            title="Declining Revenue Test",
            explanation={"what": "Promote", "why": "Low sales"},
            status=RecommendationStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user_manager)
        response = self.client.post(
            f"/api/v1/recommendations/{rec.id}/accept/",
            {"decision_reason": "Approved from test"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.ACCEPTED)

    def test_recommendation_reject_api(self):
        """Verify rejecting a recommendation updates status to REJECTED."""
        rec = Recommendation.objects.create(
            workspace=self.workspace_retail,
            recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
            title="Low Volume Test",
            explanation={"what": "Review"},
            status=RecommendationStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user_manager)
        response = self.client.post(
            f"/api/v1/recommendations/{rec.id}/reject/",
            {"decision_reason": "Not needed now"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.REJECTED)

    def test_actionable_recommendation_acceptance_creates_one_approval(self):
        rec = Recommendation.objects.create(
            workspace=self.workspace_service,
            recommendation_type=RecommendationType.SERVICE_NEARBY_TECHNICIAN,
            title="Dispatch candidate",
            explanation={"what": "Dispatch", "why": "Nearest qualified technician"},
            proposed_action="dispatch_technician",
            proposed_parameters={"ticket_id": self.ticket.id, "employee_id": self.employee.id},
        )

        self.client.force_authenticate(user=self.user_manager)
        headers = {"HTTP_X_WORKSPACE_ID": str(self.workspace_service.id)}
        response = self.client.post(
            f"/api/v1/recommendations/{rec.id}/accept/",
            {"decision_reason": "Proceed through controlled approval"},
            format="json",
            **headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.ACCEPTED)
        self.assertIsNotNone(rec.approval_request_id)
        approval = ApprovalRequest.objects.get(pk=rec.approval_request_id)
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        self.assertEqual(approval.proposed_action, "dispatch_technician")
        self.assertEqual(approval.parameters, {"ticket_id": self.ticket.id, "employee_id": self.employee.id})

        replay = self.client.post(
            f"/api/v1/recommendations/{rec.id}/accept/",
            {"decision_reason": "Repeated click"},
            format="json",
            **headers,
        )
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertEqual(ApprovalRequest.objects.filter(idempotency_key=f"RECOMMENDATION-{rec.id}").count(), 1)

    def test_recommendation_workspace_isolation(self):
        """Verify users cannot see or accept recommendations from another workspace."""
        rec_retail = Recommendation.objects.create(
            workspace=self.workspace_retail,
            recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
            title="Retail Rec",
        )

        self.client.force_authenticate(user=self.user_employee)
        # Employee not in workspace retail
        response = self.client.get("/api/v1/recommendations/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
