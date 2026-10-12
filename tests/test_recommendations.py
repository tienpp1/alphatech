"""
Test suite for Business Recommendations Engine (Phase 10).
"""

from decimal import Decimal
import datetime
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationPriority
from apps.recommendations.scoring import calculate_technician_score
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
from apps.recommendations.services import reject_recommendation
from apps.approvals.registry import ToolValidationError
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.registry import ToolRegistry
from apps.audit.models import AuditLog
from apps.retail.models import Customer
from apps.service_ops.models import Employee, Service, ServiceCategory, ServiceRequest, Task


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

    def test_service_unknown_deadlines_are_advisory_not_measured_sla_risk(self):
        self.ticket.priority = "HIGH"
        self.ticket.save(update_fields=["priority"])
        with patch("apps.gis.services.find_nearby_technicians") as nearby:
            rows = evaluate_service_recommendations(self.workspace_service)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].priority, "MEDIUM")
        self.assertEqual(rows[0].supporting_data["sla"]["overall_status"], "UNKNOWN")
        self.assertIn("không chứng minh vi phạm", rows[0].explanation["why"])
        self.assertNotIn("Đảm bảo tuân thủ", rows[0].explanation["expected_effect"])
        self.assertIsNotNone(rows[0].expires_at)
        nearby.assert_not_called()

    def test_high_priority_old_ticket_with_on_time_deadlines_is_not_sla_breach(self):
        now = timezone.now()
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(
            created_at=now - datetime.timedelta(hours=14), priority="HIGH",
            response_deadline_at=now + datetime.timedelta(days=2),
            resolution_deadline_at=now + datetime.timedelta(days=3),
        )
        self.assertEqual(evaluate_service_recommendations(self.workspace_service), [])

    def test_actual_breached_deadline_precedes_unknown_age_heuristic(self):
        now = timezone.now()
        self.ticket.priority = "HIGH"
        self.ticket.save(update_fields=["priority"])
        urgent = ServiceRequest.objects.create(
            workspace=self.workspace_service, customer=self.customer, service=self.service,
            request_number="ACTUAL-SLA", title="Deadline evidence", priority="MEDIUM",
            response_deadline_at=now - datetime.timedelta(minutes=5),
            resolution_deadline_at=now + datetime.timedelta(hours=20),
        )
        ServiceRequest.objects.filter(pk=urgent.pk).update(created_at=now - datetime.timedelta(hours=1))
        row = evaluate_service_recommendations(self.workspace_service)[0]
        self.assertEqual(row.supporting_data["ticket_id"], urgent.pk)
        self.assertEqual(row.supporting_data["sla"]["overall_status"], "BREACHED")
        self.assertEqual(row.priority, "CRITICAL")
        self.assertIsNotNone(row.explanation["evidence"]["response_deadline_at"])

    def test_service_candidates_use_recorded_availability_not_invented_skills(self):
        self.ticket.priority = "HIGH"
        self.ticket.location = Point(105.8542, 21.0285, srid=4326)
        self.ticket.save(update_fields=["priority", "location"])
        self.employee.current_location = self.ticket.location
        self.employee.is_available = False
        self.employee.skills = ["SERVER"]
        self.employee.save(update_fields=["current_location", "is_available", "skills"])
        available = Employee.objects.create(workspace=self.workspace_service, code="AVAILABLE",
                                            full_name="Available unknown skill", skills=[],
                                            current_location=Point(105.8552, 21.0285, srid=4326))
        rows = evaluate_service_recommendations(self.workspace_service)
        dispatch = next(row for row in rows if row.recommendation_type == RecommendationType.SERVICE_NEARBY_TECHNICIAN)
        top = dispatch.explanation["evidence"]["top_candidate"]
        self.assertEqual(top["technician_id"], available.pk)
        self.assertTrue(top["is_available"])
        self.assertFalse(top["skill_match_verified"])
        self.assertEqual(top["recorded_skills"], [])
        self.assertIsNone(top["score_breakdown"]["skill_score"])
        self.assertEqual(dispatch.explanation["evidence"]["ranked_candidates_count"], 1)
        self.assertIn("0.5", dispatch.explanation["evidence"]["scoring_formula"])
        self.assertEqual(dispatch.proposed_action, "dispatch_technician")
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_candidate_generation_is_not_blocked_by_existing_sla_advice(self):
        self.ticket.priority = "HIGH"
        self.ticket.save(update_fields=["priority"])
        first = evaluate_service_recommendations(self.workspace_service)
        self.assertEqual(len(first), 1)
        self.ticket.location = Point(105.8542, 21.0285, srid=4326)
        self.ticket.save(update_fields=["location"])
        self.employee.current_location = self.ticket.location
        self.employee.save(update_fields=["current_location"])
        later = evaluate_service_recommendations(self.workspace_service)
        self.assertEqual(len(later), 1)
        self.assertEqual(later[0].recommendation_type, RecommendationType.SERVICE_NEARBY_TECHNICIAN)
        self.assertEqual(evaluate_service_recommendations(self.workspace_service), [])

    def test_inactive_employee_is_not_reported_as_current_overload(self):
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])
        for number in range(3):
            Task.objects.create(service_request=self.ticket, assigned_to=self.employee,
                                title=f"Inactive task {number}", status="IN_PROGRESS")
        self.assertEqual(evaluate_service_recommendations(self.workspace_service), [])

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
        self.assertIsNone(rec.approval_request_id)
        self.assertFalse(ApprovalRequest.objects.exists())

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

    def test_reject_does_not_overwrite_accepted_controlled_approval(self):
        rec = Recommendation.objects.create(
            workspace=self.workspace_service, recommendation_type=RecommendationType.SERVICE_NEARBY_TECHNICIAN,
            title="Controlled dispatch", proposed_action="dispatch_technician",
            proposed_parameters={"ticket_id": self.ticket.pk, "employee_id": self.employee.pk},
        )
        self.client.force_authenticate(user=self.user_manager)
        headers = {"HTTP_X_WORKSPACE_ID": str(self.workspace_service.pk)}
        accepted = self.client.post(f"/api/v1/recommendations/{rec.pk}/accept/", {}, format="json", **headers)
        self.assertEqual(accepted.status_code, 200)
        rec.refresh_from_db()
        approval_id = rec.approval_request_id
        self.assertIsNotNone(approval_id)
        refused = self.client.post(f"/api/v1/recommendations/{rec.pk}/reject/", {}, format="json", **headers)
        self.assertEqual(refused.status_code, 400)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.ACCEPTED)
        self.assertEqual(rec.approval_request_id, approval_id)
        self.assertEqual(ApprovalRequest.objects.get(pk=approval_id).status, ApprovalStatus.PENDING)
        self.assertFalse(AuditLog.objects.filter(action="RECOMMENDATION_REJECTED", entity_id=str(rec.pk)).exists())

    def test_rejection_reloads_locked_state_and_is_idempotent(self):
        rec = Recommendation.objects.create(workspace=self.workspace_retail, title="Pending loaded snapshot",
                                            recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME)
        Recommendation.objects.filter(pk=rec.pk).update(status=RecommendationStatus.ACCEPTED)
        with self.assertRaises(ToolValidationError):
            reject_recommendation(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.ACCEPTED)
        Recommendation.objects.filter(pk=rec.pk).update(status=RecommendationStatus.PENDING)
        rejected = reject_recommendation(rec)
        self.assertEqual(rejected.status, RecommendationStatus.REJECTED)
        self.assertEqual(reject_recommendation(rec).status, RecommendationStatus.REJECTED)
        with self.assertRaises(ToolValidationError):
            from apps.recommendations.services import accept_recommendation
            accept_recommendation(rejected, self.user_manager)

    def test_expired_terminal_recommendation_cannot_be_rewritten_as_rejected(self):
        rec = Recommendation.objects.create(workspace=self.workspace_retail, title="Expired terminal",
                                            recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
                                            status=RecommendationStatus.EXPIRED)
        self.client.force_authenticate(user=self.user_manager)
        response = self.client.post(f"/api/v1/recommendations/{rec.pk}/reject/", {}, format="json",
                                    HTTP_X_WORKSPACE_ID=str(self.workspace_retail.pk))
        self.assertEqual(response.status_code, 400)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.EXPIRED)

    def test_reject_preserves_workspace_isolation(self):
        rec = Recommendation.objects.create(workspace=self.workspace_service, title="Other workspace",
                                            recommendation_type=RecommendationType.SERVICE_TICKET_SPIKE)
        self.client.force_authenticate(user=self.user_manager)
        response = self.client.post(f"/api/v1/recommendations/{rec.pk}/reject/", {}, format="json",
                                    HTTP_X_WORKSPACE_ID=str(self.workspace_retail.pk))
        self.assertEqual(response.status_code, 404)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.PENDING)

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

        # Acceptance is not execution; the real ticket stays unchanged.
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "OPEN")
        self.assertIsNone(self.ticket.assigned_employee_id)
        permission, _ = Permission.objects.get_or_create(
            codename="approvals.manage_approval", defaults={"name": "Review", "module": "approvals"})
        self.role_manager.permissions.add(permission)
        self_review = self.client.post(
            f"/api/v1/approvals/{approval.pk}/decision/", {"decision": "APPROVED"},
            format="json", **headers)
        self.assertEqual(self_review.status_code, 400)
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        reviewer = User.objects.create_user(username="independent-reviewer", password=None)
        WorkspaceMembership.objects.create(user=reviewer, workspace=self.workspace_service, role=self.role_manager)
        self.client.force_authenticate(user=reviewer)
        for _ in range(2):
            reviewed = self.client.post(
                f"/api/v1/approvals/{approval.pk}/decision/", {"decision": "APPROVED"},
                format="json", **headers)
            self.assertEqual(reviewed.status_code, 200)
        self.ticket.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.EXECUTED)
        self.assertEqual(self.ticket.status, "IN_PROGRESS")
        self.assertEqual(self.ticket.assigned_employee_id, self.employee.pk)
        event = AuditLog.objects.get(action="MUTATION_EXECUTED", entity_id=str(approval.pk))
        self.assertEqual(event.actor_user_id, reviewer.pk)
        self.assertEqual(event.workspace_id, self.workspace_service.pk)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.changes["result"]["ticket_id"], self.ticket.pk)

    def test_rule_generated_dispatch_reaches_independent_approval_audit_and_replay(self):
        """Local synthetic fixtures, real rules/PostGIS/API; not production UAT."""
        now = timezone.now()
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(
            created_at=now - datetime.timedelta(hours=2), priority="HIGH",
            location=Point(106.7000, 10.7750, srid=4326),
            response_deadline_at=now - datetime.timedelta(minutes=30),
            resolution_deadline_at=now + datetime.timedelta(hours=8),
        )
        self.employee.current_location = Point(106.7010, 10.7750, srid=4326)
        self.employee.is_active = True
        self.employee.is_available = True
        self.employee.skills = []
        self.employee.save(update_fields=["current_location", "is_active", "is_available", "skills"])
        self.assertFalse(Recommendation.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        self.assertFalse(Task.objects.filter(service_request=self.ticket).exists())

        # No mocked generator, manual Recommendation row or direct execute_tool.
        generated = evaluate_service_recommendations(self.workspace_service)
        candidates = [row for row in generated
                      if row.recommendation_type == RecommendationType.SERVICE_NEARBY_TECHNICIAN]
        self.assertEqual(len(candidates), 1)
        rec = candidates[0]
        parameters = {"ticket_id": self.ticket.pk, "employee_id": self.employee.pk}
        self.assertEqual(rec.workspace_id, self.workspace_service.pk)
        self.assertEqual(rec.status, RecommendationStatus.PENDING)
        self.assertEqual(rec.proposed_action, "dispatch_technician")
        self.assertEqual(rec.proposed_parameters, parameters)
        self.assertIsNone(rec.approval_request_id)
        self.assertGreater(rec.expires_at, now)
        self.assertIn(f"ticket:{self.ticket.pk}", rec.source_references)
        self.assertIn(f"employee:{self.employee.pk}", rec.source_references)
        top = rec.explanation["evidence"]["top_candidate"]
        self.assertEqual(top["technician_id"], self.employee.pk)
        self.assertGreater(top["distance_km"], 0)
        self.assertLess(top["distance_km"], 1)
        self.assertTrue(top["is_available"])
        self.assertFalse(top["skill_match_verified"])
        self.assertIsNone(top["score_breakdown"]["skill_score"])
        self.assertEqual(evaluate_service_recommendations(self.workspace_service), [])

        self.client.force_authenticate(user=self.user_manager)
        headers = {"HTTP_X_WORKSPACE_ID": str(self.workspace_service.pk)}
        # A real generated recommendation cannot be accepted from another scope.
        foreign = self.client.post(f"/api/v1/recommendations/{rec.pk}/accept/", {}, format="json",
                                   HTTP_X_WORKSPACE_ID=str(self.workspace_retail.pk))
        self.assertEqual(foreign.status_code, 404)
        self.assertFalse(ApprovalRequest.objects.exists())
        accepted = self.client.post(f"/api/v1/recommendations/{rec.pk}/accept/",
                                    {"decision_reason": "TEST — review generated dispatch"},
                                    format="json", **headers)
        self.assertEqual(accepted.status_code, 200)
        rec.refresh_from_db()
        self.assertEqual(rec.status, RecommendationStatus.ACCEPTED)
        approval = ApprovalRequest.objects.get(pk=rec.approval_request_id)
        self.assertEqual(approval.workspace_id, self.workspace_service.pk)
        self.assertEqual(approval.requester_id, self.user_manager.pk)
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        self.assertEqual(approval.proposed_action, rec.proposed_action)
        self.assertEqual(approval.parameters, parameters)
        self.assertEqual(approval.idempotency_key, f"RECOMMENDATION-{rec.pk}")
        self.assertIsNone(approval.executed_at)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "OPEN")
        self.assertIsNone(self.ticket.assigned_employee_id)
        self.assertFalse(Task.objects.filter(service_request=self.ticket).exists())
        accepted_again = self.client.post(f"/api/v1/recommendations/{rec.pk}/accept/", {}, format="json", **headers)
        self.assertEqual(accepted_again.status_code, 200)
        self.assertEqual(ApprovalRequest.objects.filter(workspace=self.workspace_service,
                                                        idempotency_key=approval.idempotency_key).count(), 1)

        permission, _ = Permission.objects.get_or_create(
            codename="approvals.manage_approval", defaults={"name": "Review", "module": "approvals"})
        self.role_manager.permissions.add(permission)
        self.assertFalse(self.user_manager.is_superuser)
        self_review = self.client.post(f"/api/v1/approvals/{approval.pk}/decision/",
                                        {"decision": "APPROVED"}, format="json", **headers)
        self.assertEqual(self_review.status_code, 400)
        approval.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        self.assertFalse(Task.objects.filter(service_request=self.ticket).exists())
        reviewer = User.objects.create_user(username="generated-rule-reviewer", password=None)
        WorkspaceMembership.objects.create(user=reviewer, workspace=self.workspace_service, role=self.role_manager)
        self.assertNotEqual(reviewer.pk, approval.requester_id)
        self.assertFalse(reviewer.is_superuser)
        self.client.force_authenticate(user=reviewer)
        reviewed = self.client.post(f"/api/v1/approvals/{approval.pk}/decision/",
                                    {"decision": "APPROVED", "decision_reason": "TEST — independent review"},
                                    format="json", **headers)
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data["data"]["status"], "EXECUTED")
        approval.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.EXECUTED)
        self.assertEqual(approval.reviewer_id, reviewer.pk)
        self.assertIsNotNone(approval.executed_at)
        self.assertEqual(self.ticket.status, "IN_PROGRESS")
        self.assertEqual(self.ticket.assigned_employee_id, self.employee.pk)
        task = Task.objects.get(service_request=self.ticket)
        self.assertEqual(task.assigned_to_id, self.employee.pk)
        self.assertEqual(task.status, "IN_PROGRESS")
        event = AuditLog.objects.get(workspace=self.workspace_service, action="MUTATION_EXECUTED",
                                     entity_type="ApprovalRequest", entity_id=str(approval.pk))
        self.assertEqual(event.actor_user_id, reviewer.pk)
        self.assertEqual(event.changes["proposed_action"], rec.proposed_action)
        self.assertEqual(event.changes["result"]["ticket_id"], self.ticket.pk)
        self.assertEqual(event.changes["result"]["assigned_employee_id"], self.employee.pk)
        self.assertEqual(event.changes["result"]["task_id"], task.pk)
        dispatched = AuditLog.objects.get(workspace=self.workspace_service, action="TECHNICIAN_DISPATCHED",
                                          entity_type="ServiceRequest", entity_id=str(self.ticket.pk))
        self.assertEqual(dispatched.actor_user_id, reviewer.pk)
        self.assertEqual(dispatched.changes["before"]["status"], "OPEN")
        self.assertEqual(dispatched.changes["after"]["status"], "IN_PROGRESS")
        executed_at = approval.executed_at
        replay = self.client.post(f"/api/v1/approvals/{approval.pk}/decision/",
                                  {"decision": "APPROVED"}, format="json", **headers)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["data"]["idempotent_replay"])
        approval.refresh_from_db()
        self.assertEqual(approval.executed_at, executed_at)
        self.assertEqual(list(Task.objects.filter(service_request=self.ticket).values_list("pk", flat=True)), [task.pk])
        self.assertEqual(AuditLog.objects.filter(workspace=self.workspace_service, action="MUTATION_EXECUTED",
                                                entity_id=str(approval.pk)).count(), 1)
        self.assertEqual(AuditLog.objects.filter(workspace=self.workspace_service, action="TECHNICIAN_DISPATCHED",
                                                entity_id=str(self.ticket.pk)).count(), 1)
        rec.refresh_from_db()
        self.assertEqual(rec.approval_request_id, approval.pk)

    def test_generated_retail_advice_does_not_enable_unimplemented_actions(self):
        recommendations = evaluate_retail_recommendations(self.workspace_retail)
        self.assertTrue(recommendations)
        self.assertTrue(all(not row.proposed_action for row in recommendations))
        # These unsupported transaction contracts must not silently become tools.
        for name in ("stock_reorder", "workload_balancing"):
            self.assertIsNone(ToolRegistry.get(name))

    def test_overload_rule_remains_advisory(self):
        for number in range(3):
            Task.objects.create(service_request=self.ticket, assigned_to=self.employee,
                                title=f"Task {number}", status="IN_PROGRESS")
        rows = evaluate_service_recommendations(self.workspace_service)
        overload = [r for r in rows if r.recommendation_type == RecommendationType.SERVICE_TECHNICIAN_OVERLOAD]
        self.assertEqual(len(overload), 1)
        self.assertEqual(overload[0].proposed_action, "")
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_stockout_rule_remains_advisory(self):
        from apps.recommendations.rules import evaluate_retail_stockout_recommendations
        # Controlled predictor output tests mapping, not forecasting accuracy.
        risk = dict(product_id=123, product_sku="TEST", product_name="Test", current_stock=0,
                    predicted_daily_demand=2, days_to_stockout=0, lead_time_days=3,
                    suggested_reorder_quantity=6, unit="cái", risk_level="OUT_OF_STOCK",
                    expected_stockout_date="2026-09-15", safety_buffer_days=0)
        with patch("apps.retail.stockout_services.get_stockout_risk_dashboard_data",
                   return_value={"products_at_risk": [risk]}):
            rows = evaluate_retail_stockout_recommendations(self.workspace_retail)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].proposed_action, "")
        self.assertFalse(ApprovalRequest.objects.exists())

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
