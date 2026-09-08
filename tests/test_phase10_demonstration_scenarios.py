"""
Automated Demonstration Test Suite for Phase 10 (Scenarios A through G).
Verifies end-to-end:
AI -> Recommendation -> Evidence -> Tool Selection -> Mutation Intent -> ApprovalRequest -> Manager Approval -> Atomic Execution -> Audit Trail.
"""

from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.accounts.models import User, Role, Permission
from apps.retail.models import Category, Product, Order, OrderStatus, Customer as RetailCustomer
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Employee,
    Task,
    TaskStatus,
)
from apps.recommendations.models import Recommendation, RecommendationType, RecommendationStatus, RecommendationPriority
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.executor import execute_tool, process_approval_decision, ToolPermissionDenied, ToolValidationError
from apps.approvals.registry import ToolRegistry
from apps.knowledge.services import answer_grounded_query
from apps.audit.models import AuditLog


class Phase10DemonstrationScenarioTests(TestCase):
    """
    Tests covering the exact 7 Demonstration Scenarios specified in Phase 10 Directive:
    Scenario A: Retail Flagged Branch (Why is branch flagged? -> recommendation + evidence)
    Scenario B: Service Technician Candidate (Who should handle this ticket? -> candidate scoring + evidence)
    Scenario C: Mutation via AI Assistant (Assign technician -> PENDING ApprovalRequest)
    Scenario D: Approval Execution by Manager B (Approval -> Atomic DB Mutation + Audit)
    Scenario E: Rejection by Manager B (Rejection -> No Mutation)
    Scenario F: Unauthorized Approval (Employee user -> 403 / ToolPermissionDenied)
    Scenario G: Cross-Workspace Access (Access to other workspace resource -> Rejected)
    """

    def setUp(self):
        # 1. Create Dual Workspaces
        self.workspace_retail = Workspace.objects.create(
            name="Demo Retail Workspace",
            code="demo-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.workspace_service = Workspace.objects.create(
            name="Demo Service Workspace",
            code="demo-service",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 2. Permissions
        p_ai_chat, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "ai"})
        p_rec_view, _ = Permission.objects.get_or_create(codename="recommendations.view_recommendation", defaults={"name": "View Rec", "module": "recommendations"})
        p_app_view, _ = Permission.objects.get_or_create(codename="approvals.view_approval", defaults={"name": "View App", "module": "approvals"})
        p_app_manage, _ = Permission.objects.get_or_create(codename="approvals.manage_approval", defaults={"name": "Manage App", "module": "approvals"})
        p_retail_view, _ = Permission.objects.get_or_create(codename="retail.view_order", defaults={"name": "View Order", "module": "retail"})
        p_retail_manage, _ = Permission.objects.get_or_create(codename="retail.manage_order", defaults={"name": "Manage Order", "module": "retail"})
        p_service_view, _ = Permission.objects.get_or_create(codename="service.view_request", defaults={"name": "View Request", "module": "service_ops"})
        p_service_manage, _ = Permission.objects.get_or_create(codename="service.manage_request", defaults={"name": "Manage Request", "module": "service_ops"})
        p_service_emp_view, _ = Permission.objects.get_or_create(codename="service.view_employee", defaults={"name": "View Employee", "module": "service_ops"})

        # Roles
        self.role_manager = Role.objects.create(name="DEMO_MANAGER")
        self.role_manager.permissions.set([
            p_ai_chat, p_rec_view, p_app_view, p_app_manage,
            p_retail_view, p_retail_manage,
            p_service_view, p_service_manage, p_service_emp_view,
        ])

        self.role_employee = Role.objects.create(name="DEMO_EMPLOYEE")
        self.role_employee.permissions.set([p_ai_chat, p_service_view, p_retail_view])

        # Users
        self.manager_a = User.objects.create_user(
            username="manager_a", email="mgr_a@example.com", password="Password123!"
        )
        self.manager_b = User.objects.create_user(
            username="manager_b", email="mgr_b@example.com", password="Password123!"
        )
        self.employee_user = User.objects.create_user(
            username="emp_user", email="emp@example.com", password="Password123!"
        )
        self.other_workspace_user = User.objects.create_user(
            username="other_user", email="other@example.com", password="Password123!"
        )

        # Memberships
        WorkspaceMembership.objects.create(workspace=self.workspace_service, user=self.manager_a, role=self.role_manager)
        WorkspaceMembership.objects.create(workspace=self.workspace_service, user=self.manager_b, role=self.role_manager)
        WorkspaceMembership.objects.create(workspace=self.workspace_service, user=self.employee_user, role=self.role_employee)

        WorkspaceMembership.objects.create(workspace=self.workspace_retail, user=self.manager_a, role=self.role_manager)
        WorkspaceMembership.objects.create(workspace=self.workspace_retail, user=self.manager_b, role=self.role_manager)

        # Other workspace user only belongs to retail
        WorkspaceMembership.objects.create(workspace=self.workspace_retail, user=self.other_workspace_user, role=self.role_employee)

        # 3. Setup Service Ops Entities
        self.customer_svc = RetailCustomer.objects.create(
            workspace=self.workspace_service,
            code="CUST-SVC-01",
            name="Bitexco Tower Client",
            location=Point(105.8542, 21.0285, srid=4326),
        )
        self.service_net = Service.objects.create(
            workspace=self.workspace_service,
            code="SRV-NET-01",
            name="Dịch vụ Mạng Doanh nghiệp",
            category=ServiceCategory.MAINTENANCE,
            base_fee=Decimal("1500000.00"),
        )

        past_time = timezone.now() - datetime.timedelta(hours=14)
        self.ticket = ServiceRequest.objects.create(
            workspace=self.workspace_service,
            customer=self.customer_svc,
            service=self.service_net,
            request_number="SR-SCENARIO-01",
            title="Sự cố máy chủ mạng nội bộ",
            description="Mất kết nối mạng toàn bộ văn phòng",
            priority=ServiceRequestPriority.HIGH,
            status=ServiceRequestStatus.OPEN,
            latitude=Decimal("21.0285"),
            longitude=Decimal("105.8542"),
            location=Point(105.8542, 21.0285, srid=4326),
        )
        ServiceRequest.objects.filter(id=self.ticket.id).update(created_at=past_time)
        self.ticket.refresh_from_db()

        # Technician 1: Close (1 km away) with 1 task
        self.tech_1 = Employee.objects.create(
            workspace=self.workspace_service,
            user=self.manager_a,
            code="TECH-001",
            full_name="Nguyễn Văn A",
            email="tech1@example.com",
            is_active=True,
            is_available=True,
            latitude=Decimal("21.0300"),
            longitude=Decimal("105.8550"),
            current_location=Point(105.8550, 21.0300, srid=4326),
            skills=["NETWORK", "SERVER"],
            hourly_labor_rate=Decimal("150000.00"),
        )
        Task.objects.create(
            service_request=self.ticket,
            title="Nhiệm vụ trước",
            assigned_to=self.tech_1,
            status=TaskStatus.IN_PROGRESS,
        )

        # Technician 2: Farther (15 km away) with 3 tasks
        self.tech_2 = Employee.objects.create(
            workspace=self.workspace_service,
            code="TECH-002",
            full_name="Trần Văn B",
            email="tech2@example.com",
            is_active=True,
            is_available=True,
            latitude=Decimal("21.1500"),
            longitude=Decimal("105.9000"),
            current_location=Point(105.9000, 21.1500, srid=4326),
            skills=["NETWORK"],
            hourly_labor_rate=Decimal("120000.00"),
        )
        for i in range(3):
            Task.objects.create(
                service_request=self.ticket,
                title=f"Task bận {i}",
                assigned_to=self.tech_2,
                status=TaskStatus.IN_PROGRESS,
            )

        # 4. Setup Retail Entities: Low order volume & revenue
        self.customer_retail = RetailCustomer.objects.create(
            workspace=self.workspace_retail,
            code="CUST-RET-01",
            name="Khách Hàng Mẫu",
        )
        self.category = Category.objects.create(
            workspace=self.workspace_retail,
            name="Thiết bị",
            code="CAT-DEV",
        )
        self.product = Product.objects.create(
            workspace=self.workspace_retail,
            category=self.category,
            name="Router Cisco",
            sku="CISCO-01",
            unit_price=Decimal("2500000.00"),
            cost_price=Decimal("1800000.00"),
        )
        Order.objects.create(
            workspace=self.workspace_retail,
            customer=self.customer_retail,
            order_number="ORD-001",
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("5000000.00"),
        )

    # -------------------------------------------------------------------------
    # SCENARIO A: Retail Flagged Branch Recommendation
    # -------------------------------------------------------------------------
    def test_scenario_a_retail_flagged_branch(self):
        """
        Scenario A: User asks 'Why is branch A being flagged?'
        Expected: Explainable recommendation with what, why, evidence, and priority.
        """
        recs = evaluate_retail_recommendations(self.workspace_retail)
        self.assertGreaterEqual(len(recs), 1)

        res = answer_grounded_query(
            workspace=self.workspace_retail,
            user=self.manager_a,
            message="Tại sao chi nhánh bị cảnh báo flagged?",
        )

        answer = res["answer"]
        self.assertIn("Đề xuất khuyến nghị", answer)
        self.assertIn("Lý do cảnh báo", answer)
        self.assertIn("Bằng chứng dữ liệu (Evidence)", answer)
        tools_invoked = [t["tool"] for t in res["tools_used"]]
        self.assertIn("get_recommendations", tools_invoked)

    # -------------------------------------------------------------------------
    # SCENARIO B: Service Proximity Candidate Scoring
    # -------------------------------------------------------------------------
    def test_scenario_b_service_technician_candidate(self):
        """
        Scenario B: User asks 'Who should handle this ticket?'
        Expected: Deterministic ranked candidates with GIS proximity and subscore evidence.
        """
        res = answer_grounded_query(
            workspace=self.workspace_service,
            user=self.manager_a,
            message=f"Ai nên xử lý ticket #{self.ticket.id}?",
        )

        answer = res["answer"]
        self.assertIn("Đề xuất phân công kỹ thuật viên", answer)
        self.assertIn(self.tech_1.full_name, answer)
        self.assertIn("Điểm đánh giá", answer)
        self.assertIn("Khoảng cách địa lý", answer)
        self.assertIn("Bằng chứng", answer)

    # -------------------------------------------------------------------------
    # SCENARIO C: Mutation via AI Assistant
    # -------------------------------------------------------------------------
    def test_scenario_c_ai_mutation_creates_pending_approval(self):
        """
        Scenario C: User asks 'Phân công kỹ thuật viên 1 cho ticket 1'
        Expected: ZERO direct DB mutation. Creates a PENDING ApprovalRequest.
        """
        res = answer_grounded_query(
            workspace=self.workspace_service,
            user=self.manager_a,
            message=f"Phân công kỹ thuật viên {self.tech_1.id} cho ticket #{self.ticket.id}",
        )

        self.assertEqual(res.get("mutation_status"), "APPROVAL_REQUIRED")
        approval_id = res.get("approval_request_id")
        self.assertIsNotNone(approval_id)

        # Verify DB state: Ticket is NOT yet assigned to technician (Zero direct AI mutation!)
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.assigned_employee)

        # Verify ApprovalRequest in DB
        app_req = ApprovalRequest.objects.get(id=approval_id)
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)
        self.assertEqual(app_req.proposed_action, "dispatch_technician")
        self.assertEqual(app_req.requester, self.manager_a)
        self.assertEqual(app_req.parameters["ticket_id"], self.ticket.id)
        self.assertEqual(app_req.parameters["employee_id"], self.tech_1.id)

    # -------------------------------------------------------------------------
    # SCENARIO D: Approval Execution by Manager B
    # -------------------------------------------------------------------------
    def test_scenario_d_approval_execution_by_manager_b(self):
        """
        Scenario D: Manager B approves the mutation request created in Scenario C.
        Expected: Atomic execution, ServiceRequest updated, Task assigned, audit logged, replay prevented.
        """
        # 1. Create pending request by Manager A
        res = execute_tool(
            name="dispatch_technician",
            workspace=self.workspace_service,
            user=self.manager_a,
            parameters={"ticket_id": self.ticket.id, "employee_id": self.tech_1.id},
            idempotency_key="IK-DEMO-SCENARIO-D",
        )
        app_req = ApprovalRequest.objects.get(id=res["approval_request_id"])

        # 2. Manager B approves
        approval_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_b,
            decision="APPROVED",
            decision_reason="Đồng ý phê duyệt điều động khẩn cấp.",
        )

        self.assertEqual(approval_result["status"], "EXECUTED")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.EXECUTED)
        self.assertEqual(app_req.reviewer, self.manager_b)

        # 3. Verify Database Mutation actually occurred
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_employee, self.tech_1)
        self.assertEqual(self.ticket.status, ServiceRequestStatus.IN_PROGRESS)

        # 4. Verify Task created/updated
        task = Task.objects.filter(service_request=self.ticket, assigned_to=self.tech_1).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

        # 5. Verify Audit Log recorded
        audit = AuditLog.objects.filter(
            action="MUTATION_EXECUTED",
            entity_type="ApprovalRequest",
            entity_id=str(app_req.id),
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_user, self.manager_b)

        # 6. Verify Replay Protection: Re-executing returns cached result without repeating mutation
        replay_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_b,
            decision="APPROVED",
        )
        self.assertTrue(replay_result.get("idempotent_replay"))
        self.assertEqual(replay_result["status"], "EXECUTED")

    # -------------------------------------------------------------------------
    # SCENARIO E: Rejection by Manager B
    # -------------------------------------------------------------------------
    def test_scenario_e_rejection_prevents_mutation(self):
        """
        Scenario E: Manager B rejects the request.
        Expected: Status is REJECTED, no database mutation occurs.
        """
        # Create second ticket
        ticket_2 = ServiceRequest.objects.create(
            workspace=self.workspace_service,
            customer=self.customer_svc,
            service=self.service_net,
            request_number="SR-SCENARIO-02",
            title="Yêu cầu kiểm tra định kỳ",
            description="Kiểm tra định kỳ thiết bị mạng",
            priority=ServiceRequestPriority.LOW,
            status=ServiceRequestStatus.OPEN,
        )

        res = execute_tool(
            name="dispatch_technician",
            workspace=self.workspace_service,
            user=self.manager_a,
            parameters={"ticket_id": ticket_2.id, "employee_id": self.tech_2.id},
            idempotency_key="IK-DEMO-SCENARIO-E",
        )
        app_req = ApprovalRequest.objects.get(id=res["approval_request_id"])

        # Manager B rejects
        rej_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_b,
            decision="REJECTED",
            decision_reason="Kỹ thuật viên hiện đang quá tải 3 công việc.",
        )

        self.assertEqual(rej_result["status"], "REJECTED")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.REJECTED)

        # Verify NO mutation occurred on ticket_2
        ticket_2.refresh_from_db()
        self.assertIsNone(ticket_2.assigned_employee)
        self.assertEqual(ticket_2.status, ServiceRequestStatus.OPEN)

    # -------------------------------------------------------------------------
    # SCENARIO F: Unauthorized User Approval Denied
    # -------------------------------------------------------------------------
    def test_scenario_f_unauthorized_approval_denied(self):
        """
        Scenario F: Employee user attempts to approve a request.
        Expected: 403 / ToolPermissionDenied.
        """
        res = execute_tool(
            name="dispatch_technician",
            workspace=self.workspace_service,
            user=self.manager_a,
            parameters={"ticket_id": self.ticket.id, "employee_id": self.tech_1.id},
            idempotency_key="IK-DEMO-SCENARIO-F",
        )
        app_req = ApprovalRequest.objects.get(id=res["approval_request_id"])

        # Employee lacks approvals.manage_approval
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(
                approval_request=app_req,
                reviewer=self.employee_user,
                decision="APPROVED",
            )

        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)

    # -------------------------------------------------------------------------
    # SCENARIO G: Cross-Workspace Access Rejection
    # -------------------------------------------------------------------------
    def test_scenario_g_cross_workspace_rejection(self):
        """
        Scenario G: User attempts to execute tool or approval for another workspace resource.
        Expected: ToolValidationError or ToolPermissionDenied.
        """
        # User in retail workspace attempts to dispatch a ticket in service workspace
        with self.assertRaises((ToolValidationError, ToolPermissionDenied)):
            execute_tool(
                name="dispatch_technician",
                workspace=self.workspace_retail,  # Cross-workspace: retail workspace has no service tickets
                user=self.other_workspace_user,
                parameters={"ticket_id": self.ticket.id, "employee_id": self.tech_1.id},
            )
