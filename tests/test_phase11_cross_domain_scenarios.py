"""
Phase 11 Cross-Domain End-to-End Integration Scenarios.
Verifies multi-phase operational pipelines spanning:
- Scenario A: Retail Pipeline (CSV Ingestion -> Mapping -> Canonical Orders -> Analytics -> GIS -> Forecast -> Recommendations -> AI Grounding -> Audit)
- Scenario B: Service Pipeline (External Tickets -> Mapping -> ServiceRequest -> SLA -> Technician -> GIS Proximity -> Forecast -> Recommendation -> Approval -> Dispatch -> Audit)
- Scenario C: RAG Pipeline (SOP Ingestion -> Parsing -> Chunking -> Embedding -> Retrieval -> Grounded Answer with Citations & Fallback)
- Scenario D: AI Mutation Governance Chain (Natural Language Command -> Intent Routing -> PENDING Approval -> Separation of Duties -> Manager Approval -> Atomic Execution -> Replay Protection -> Complete Audit Chain)
"""

import io
import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.audit.models import AuditLog
from apps.retail.models import Customer, Category, Product, Branch, Order, OrderItem, OrderStatus
from apps.service_ops.models import (
    Service, Employee, SLA, ServiceRequest, Task,
    ServiceRequestStatus, TaskStatus, ServiceCategory
)
from apps.integration.models import DataSource, ImportJob, RawImportRecord, SourceType, EntityType, ImportStatus
from apps.integration.services import execute_import_job
from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    apply_mapping_to_domain,
)
from apps.gis.selectors import get_retail_branches_geojson, get_nearby_technicians_for_ticket
from apps.forecasting.selectors import get_historical_timeseries
from apps.recommendations.models import Recommendation, RecommendationStatus
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentFileType,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
    answer_grounded_query,
)
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.approvals.registry import ToolRegistry


class Phase11CrossDomainScenarioTests(TestCase):
    """
    Complete cross-domain end-to-end integration scenarios for Phase 11.
    """

    def setUp(self):
        # 1. Workspaces
        self.retail_ws = Workspace.objects.create(
            name="Retail Corp Test",
            code="WS_RETAIL_11",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )
        self.service_ws = Workspace.objects.create(
            name="Service Tech Test",
            code="WS_SERVICE_11",
            workspace_type=WorkspaceType.SERVICE,
            is_active=True,
        )

        # 2. Permissions
        self.perm_view_order, _ = Permission.objects.get_or_create(codename="retail.view_order", defaults={"name": "View Orders", "module": "retail"})
        self.perm_change_order, _ = Permission.objects.get_or_create(codename="retail.change_order", defaults={"name": "Change Orders", "module": "retail"})
        self.perm_change_prod, _ = Permission.objects.get_or_create(codename="retail.change_product", defaults={"name": "Change Products", "module": "retail"})
        self.perm_manage_prod, _ = Permission.objects.get_or_create(codename="retail.manage_product", defaults={"name": "Manage Products", "module": "retail"})

        self.perm_view_service, _ = Permission.objects.get_or_create(codename="service_ops.view_servicerequest", defaults={"name": "View Requests", "module": "service_ops"})
        self.perm_change_service, _ = Permission.objects.get_or_create(codename="service_ops.change_servicerequest", defaults={"name": "Change Requests", "module": "service_ops"})
        self.perm_view_emp, _ = Permission.objects.get_or_create(codename="service_ops.view_employee", defaults={"name": "View Employees", "module": "service_ops"})

        self.perm_view_rec, _ = Permission.objects.get_or_create(codename="recommendations.view_recommendation", defaults={"name": "View Recommendations", "module": "recommendations"})
        self.perm_manage_rec, _ = Permission.objects.get_or_create(codename="recommendations.manage_recommendation", defaults={"name": "Manage Recommendations", "module": "recommendations"})
        self.perm_manage_app, _ = Permission.objects.get_or_create(codename="approvals.manage_approval", defaults={"name": "Manage Approvals", "module": "approvals"})

        self.perm_view_doc, _ = Permission.objects.get_or_create(codename="knowledge.view_document", defaults={"name": "View Documents", "module": "knowledge"})
        self.perm_chat_k, _ = Permission.objects.get_or_create(codename="knowledge.chat", defaults={"name": "Knowledge Chat", "module": "knowledge"})
        self.perm_chat_ai, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "knowledge"})

        # Role: Manager
        self.manager_role = Role.objects.create(name="MANAGER", description="Workspace Manager")
        self.manager_role.permissions.set([
            self.perm_view_order, self.perm_change_order, self.perm_change_prod, self.perm_manage_prod,
            self.perm_view_service, self.perm_change_service, self.perm_view_emp,
            self.perm_view_rec, self.perm_manage_rec, self.perm_manage_app,
            self.perm_view_doc, self.perm_chat_k, self.perm_chat_ai,
        ])

        # Role: Employee
        self.employee_role = Role.objects.create(name="EMPLOYEE", description="Workspace Employee")
        self.employee_role.permissions.set([
            self.perm_view_order, self.perm_view_service, self.perm_view_emp,
            self.perm_view_doc, self.perm_chat_k, self.perm_chat_ai,
            self.perm_change_service, self.perm_change_prod, self.perm_manage_prod,
        ])

        # Users
        self.manager_user = User.objects.create_user(
            username="manager11", email="manager11@example.com", password="password123", is_active=True
        )
        self.employee_user = User.objects.create_user(
            username="employee11", email="employee11@example.com", password="password123", is_active=True
        )

        WorkspaceMembership.objects.create(
            user=self.manager_user, workspace=self.retail_ws, role=self.manager_role, is_active=True, is_default=True
        )
        WorkspaceMembership.objects.create(
            user=self.manager_user, workspace=self.service_ws, role=self.manager_role, is_active=True, is_default=False
        )
        WorkspaceMembership.objects.create(
            user=self.employee_user, workspace=self.retail_ws, role=self.employee_role, is_active=True, is_default=True
        )
        WorkspaceMembership.objects.create(
            user=self.employee_user, workspace=self.service_ws, role=self.employee_role, is_active=True, is_default=False
        )

    # =========================================================================
    # SCENARIO A: RETAIL PIPELINE
    # CSV -> Integration -> Mapping -> Domain Orders -> Analytics -> GIS -> Forecast -> Recommendation -> AI Grounding -> Audit
    # =========================================================================
    def test_scenario_a_retail_pipeline(self):
        """
        Scenario A: End-to-end Retail Pipeline verifying complete cross-phase propagation.
        """
        # Step 1: Create Retail Category, Customer, Branch, and Product in Workspace
        category = Category.objects.create(workspace=self.retail_ws, code="CAT_HW", name="Phần cứng máy tính")
        customer = Customer.objects.create(
            workspace=self.retail_ws,
            code="CUST-CANON-01",
            name="Nguyễn Văn An",
            is_active=True,
        )
        branch = Branch.objects.create(
            workspace=self.retail_ws,
            code="BR_HN_01",
            name="Chi nhánh Hà Nội 1",
            location=Point(105.8542, 21.0285, srid=4326),
            is_active=True,
        )
        product = Product.objects.create(
            workspace=self.retail_ws,
            sku="PROD_LAPTOP_01",
            name="Laptop Enterprise X1",
            category=category,
            unit_price=Decimal("25000000"),
            is_active=True,
        )

        # Step 2: Ingest External Orders CSV via Data Integration
        data_source = DataSource.objects.create(
            workspace=self.retail_ws,
            name="External POS Sales CSV",
            source_type=SourceType.CSV,
            is_active=True,
            created_by=self.manager_user,
        )

        csv_content = (
            "so_hd,ma_kh,ngay,tien\n"
            "ORD-P11-001,CUST-CANON-01,2026-08-20,50000000\n"
            "ORD-P11-002,CUST-CANON-01,2026-08-21,25000000\n"
        ).encode("utf-8")

        import_job = execute_import_job(
            workspace=self.retail_ws,
            user=self.manager_user,
            data_source=data_source,
            file_obj=io.BytesIO(csv_content),
            entity_type=EntityType.RETAIL_ORDERS,
        )
        self.assertEqual(import_job.status, ImportStatus.COMPLETED)
        self.assertEqual(import_job.total_rows, 2)

        # Step 3: Map Raw Records to Domain Model via Data Mapping Engine
        profile = create_mapping_profile(
            workspace=self.retail_ws,
            user=self.manager_user,
            name="POS to Order Mapping Profile",
            target_entity="Order",
            data_source=data_source,
        )
        add_mapping_rule(profile, self.manager_user, "so_hd", "order_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.manager_user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.manager_user, "ngay", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"})
        add_mapping_rule(profile, self.manager_user, "tien", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"})

        # Apply mapping to domain
        applied_results = apply_mapping_to_domain(
            workspace=self.retail_ws,
            user=self.manager_user,
            profile=profile,
            import_job=import_job,
            strict=True,
        )
        self.assertEqual(applied_results["status"], "COMPLETED")
        self.assertEqual(applied_results["inserted_count"], 2)

        # Verify Canonical Orders persisted with branch assignment
        orders = Order.objects.for_workspace(self.retail_ws).order_by("order_number")
        self.assertEqual(orders.count(), 2)
        for ord_obj in orders:
            ord_obj.branch = branch
            ord_obj.status = OrderStatus.COMPLETED
            ord_obj.save(update_fields=["branch", "status"])
        self.assertEqual(orders[0].total_amount, Decimal("50000000"))

        # Step 4: Verify GIS Branch Analytics reflects network
        branch_geojson = get_retail_branches_geojson(workspace=self.retail_ws)
        self.assertEqual(branch_geojson["type"], "FeatureCollection")
        self.assertTrue(len(branch_geojson["features"]) >= 1)

        # Step 5: Verify Forecasting Time Series selector pulls orders
        ts_df = get_historical_timeseries(
            workspace=self.retail_ws,
            target_type="RETAIL_REVENUE",
        )
        self.assertFalse(ts_df.empty)
        self.assertTrue(ts_df["target"].sum() >= 75000000)

        # Step 6: Trigger Operational Recommendations
        recs = evaluate_retail_recommendations(workspace=self.retail_ws)
        self.assertTrue(len(recs) >= 1)
        pending_rec = Recommendation.objects.for_workspace(self.retail_ws).first()
        self.assertIsNotNone(pending_rec)
        self.assertIn("what", pending_rec.explanation)
        self.assertIn("why", pending_rec.explanation)
        self.assertIn("evidence", pending_rec.explanation)

        # Step 7: Grounded AI Query reads retail telemetry & recommendations
        answer_result = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.manager_user,
            message="Tổng hợp doanh thu bán hàng và các đề xuất vận hành hiện tại",
        )
        self.assertIn("answer", answer_result)
        self.assertTrue(len(answer_result["answer"]) > 10)

        # Step 8: Verify Complete Audit Trail Recorded
        audit_actions = AuditLog.objects.filter(workspace=self.retail_ws).values_list("action", flat=True)
        self.assertIn("IMPORT_COMPLETED", audit_actions)
        self.assertIn("MAPPING_APPLIED", audit_actions)
        self.assertIn("AI_TOOL_INVOKED", audit_actions)

    # =========================================================================
    # SCENARIO B: SERVICE PIPELINE
    # External Tickets -> Mapping -> Service Ticket -> SLA -> Technician -> GIS Proximity -> Recommendation -> Approval -> Dispatch -> Audit
    # =========================================================================
    def test_scenario_b_service_pipeline(self):
        """
        Scenario B: End-to-end Service Operations Pipeline from ticket ingestion to controlled dispatch.
        """
        # Step 1: Setup Service Catalog, SLA, and Technicians
        service = Service.objects.create(
            workspace=self.service_ws,
            code="SRV_INSTALL",
            name="Cài đặt hệ thống Server",
            category=ServiceCategory.INSTALLATION,
            base_fee=Decimal("5000000"),
            standard_duration_minutes=240,
            is_active=True,
        )
        sla = SLA.objects.create(
            workspace=self.service_ws,
            name="Khẩn cấp 4h",
            response_time_hours=1,
            resolution_time_hours=4,
            is_active=True,
        )
        tech_alpha = Employee.objects.create(
            workspace=self.service_ws,
            code="TECH_P11_01",
            full_name="Lê Kỹ Thuật",
            current_location=Point(105.8550, 21.0300, srid=4326),  # ~0.2 km from ticket
            hourly_labor_rate=Decimal("150000"),
            skills=["INSTALLATION", "MAINTENANCE"],
            is_active=True,
        )
        customer = Customer.objects.create(
            workspace=self.service_ws,
            code="CUST_SVC_01",
            name="Công ty Công nghệ Á Châu",
            is_active=True,
        )

        # Step 2: Ingest External Service Ticket via Integration
        data_source = DataSource.objects.create(
            workspace=self.service_ws,
            name="External Helpdesk Tickets",
            source_type=SourceType.CSV,
            is_active=True,
            created_by=self.manager_user,
        )
        csv_tickets = (
            "ticket_no,client_id,service_id,issue_title\n"
            "REQ-P11-901,CUST_SVC_01,SRV_INSTALL,Sự cố máy chủ DC01 sập nguồn\n"
        ).encode("utf-8")

        import_job = execute_import_job(
            workspace=self.service_ws,
            user=self.manager_user,
            data_source=data_source,
            file_obj=io.BytesIO(csv_tickets),
            entity_type=EntityType.SERVICE_REQUESTS,
        )
        self.assertEqual(import_job.status, ImportStatus.COMPLETED)
        self.assertEqual(import_job.total_rows, 1)

        # Step 3: Apply Mapping to Domain ServiceRequest
        profile = create_mapping_profile(
            workspace=self.service_ws,
            user=self.manager_user,
            name="Ticket Map Profile",
            target_entity="ServiceRequest",
            data_source=data_source,
        )
        add_mapping_rule(profile, self.manager_user, "ticket_no", "request_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.manager_user, "client_id", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.manager_user, "service_id", "service_code", RuleType.FIELD_MAPPING)
        add_mapping_rule(profile, self.manager_user, "issue_title", "title", RuleType.FIELD_MAPPING)

        res = apply_mapping_to_domain(
            workspace=self.service_ws,
            user=self.manager_user,
            profile=profile,
            import_job=import_job,
            strict=True,
        )
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["inserted_count"], 1)

        ticket = ServiceRequest.objects.for_workspace(self.service_ws).filter(request_number="REQ-P11-901").first()
        self.assertIsNotNone(ticket)
        # Enrich ticket with spatial coordinate and SLA
        ticket.location = Point(105.8542, 21.0285, srid=4326)
        ticket.sla = sla
        ticket.priority = "HIGH"
        ticket.save(update_fields=["location", "sla", "priority"])

        # Step 4: GIS Spatial Proximity & Ranking
        nearby_data = get_nearby_technicians_for_ticket(
            ticket=ticket,
            radius_km=25.0,
        )
        self.assertTrue(len(nearby_data["candidates"]) >= 1)
        top_candidate = nearby_data["candidates"][0]
        self.assertEqual(top_candidate["employee_id"], tech_alpha.id)

        # Step 5: Trigger Recommendations
        recs = evaluate_service_recommendations(workspace=self.service_ws)
        self.assertTrue(len(recs) >= 1)

        # Step 6: Controlled AI Mutation Dispatch Request
        exec_response = execute_tool(
            name="dispatch_technician",
            workspace=self.service_ws,
            user=self.employee_user,
            parameters={
                "ticket_id": ticket.id,
                "employee_id": tech_alpha.id,
            },
        )
        self.assertEqual(exec_response["status"], "APPROVAL_REQUIRED")
        approval_id = exec_response["approval_request_id"]

        # Verify Ticket is UNCHANGED (Zero Direct DB Mutation)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_employee)
        self.assertEqual(ticket.status, ServiceRequestStatus.OPEN)

        # Step 7: Authorized Manager Decision (Execution)
        app_req = ApprovalRequest.objects.get(id=approval_id)
        decision_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_user,
            decision="APPROVED",
            decision_reason="Phê duyệt điều động kỹ thuật viên khẩn cấp xử lý sự cố DC01.",
        )
        self.assertEqual(decision_result["status"], "EXECUTED")

        # Verify Database Mutation Applied Atomically
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_employee, tech_alpha)
        self.assertEqual(ticket.status, ServiceRequestStatus.IN_PROGRESS)

        # Step 8: Replay Protection Check
        replay_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_user,
            decision="APPROVED",
        )
        self.assertTrue(replay_result.get("idempotent_replay"))

        # Step 9: Verify Audit Trail
        audit_events = AuditLog.objects.filter(workspace=self.service_ws).values_list("action", flat=True)
        self.assertIn("APPROVAL_CREATED", audit_events)
        self.assertIn("MUTATION_EXECUTED", audit_events)

    # =========================================================================
    # SCENARIO C: GROUNDED RAG PIPELINE
    # Upload SOP -> Parse -> Chunk -> Embed -> Retrieve -> Grounded Answer -> Citations & Fallback
    # =========================================================================
    def test_scenario_c_grounded_rag_pipeline(self):
        """
        Scenario C: Verifies Document parsing, semantic chunking, vector embedding,
        grounded question answering with verifiable citations, and exact no-context fallback.
        """
        # Step 1: Ingest Company SOP Document
        sop_content = (
            "# Quy trình Xử lý Sự cố Hạ tầng Trung tâm Dữ liệu\n\n"
            "Khi nhiệt độ phòng máy chủ vượt quá 32 độ C, kỹ thuật viên trực ban phải lập tức "
            "bật hệ thống làm mát dự phòng CRAC-02 và gửi thông báo khẩn cấp cho Quản lý trong vòng 15 phút.\n\n"
            "Mọi trường hợp quá nhiệt phải được ghi vào Nhật ký Vận hành với mã sự cố TCK-DC-TEMP."
        )

        kb = create_knowledge_base(
            workspace=self.service_ws,
            user=self.manager_user,
            name="SOP Trung tâm Dữ liệu",
        )
        sop_file = SimpleUploadedFile(
            "sop_temp.md",
            sop_content.encode("utf-8"),
            content_type="text/markdown",
        )
        doc = upload_and_ingest_document(
            workspace=self.service_ws,
            user=self.manager_user,
            knowledge_base=kb,
            file_obj=sop_file,
            title="SOP-DC-01 Quy trình xử lý nhiệt độ phòng Server",
            file_type="MD",
        )
        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertTrue(doc.chunks.count() >= 1)

        # Step 2: Grounded Query with verified context -> Expect citation
        grounded_res = answer_grounded_query(
            workspace=self.service_ws,
            user=self.manager_user,
            message="Khi nhiệt độ phòng server vượt quá 32 độ thì kỹ thuật viên phải làm gì?",
        )
        self.assertIn("answer", grounded_res)
        # Should mention cooling or CRAC-02
        self.assertTrue(
            any(kw in grounded_res["answer"] for kw in ["làm mát", "CRAC-02", "32 độ", "dự phòng", "nhiệt độ"]),
            f"Expected SOP facts in answer: {grounded_res['answer']}"
        )
        self.assertTrue(len(grounded_res["sources"]) >= 1)
        self.assertEqual(grounded_res["sources"][0]["document_title"], doc.title)

        # Step 3: Invariant Test: Unrelated / Out-of-Domain query -> Exact Fallback
        fallback_res = answer_grounded_query(
            workspace=self.service_ws,
            user=self.manager_user,
            message="Chính sách hỗ trợ mua nhà cho nhân viên năm 2030 là gì?",
        )
        self.assertEqual(
            fallback_res["answer"],
            "Không tìm thấy thông tin đủ tin cậy trong tài liệu của doanh nghiệp."
        )

    # =========================================================================
    # SCENARIO D: AI MUTATION GOVERNANCE CHAIN
    # Natural language command -> AI intent -> PENDING Approval -> Separation of Duties -> Manager Approval -> Atomic Execution -> Complete Audit Chain
    # =========================================================================
    def test_scenario_d_ai_mutation_governance_chain(self):
        """
        Scenario D: Complete Human-in-the-Loop AI mutation lifecycle with separation of duties.
        """
        # Step 1: Setup target product
        category = Category.objects.create(workspace=self.retail_ws, code="CAT_DISC", name="Khuyến mãi")
        product = Product.objects.create(
            workspace=self.retail_ws,
            sku="PROD_DISC_01",
            name="Màn hình Gaming 27 inch",
            category=category,
            unit_price=Decimal("8000000"),
            is_active=True,
        )

        # Step 2: Employee prompts natural language price adjustment
        ai_response = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.employee_user,
            message=f"Điều chỉnh giá sản phẩm {product.id} thành 7500000",
        )
        self.assertIn("Yêu cầu Phê duyệt", ai_response["answer"])

        # Verify ApprovalRequest created in PENDING state
        app_req = ApprovalRequest.objects.filter(workspace=self.retail_ws, proposed_action="adjust_product_price").first()
        self.assertIsNotNone(app_req)
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)
        self.assertEqual(app_req.requester, self.employee_user)

        # Verify Product unit price UNCHANGED
        product.refresh_from_db()
        self.assertEqual(product.unit_price, Decimal("8000000"))

        # Step 3: Separation of Duties - Requester cannot approve own request
        with self.assertRaises(Exception):
            process_approval_decision(
                approval_request=app_req,
                reviewer=self.employee_user,
                decision="APPROVED",
            )

        # Step 4: Authorized Manager approves the request
        decision_result = process_approval_decision(
            approval_request=app_req,
            reviewer=self.manager_user,
            decision="APPROVED",
            decision_reason="Đồng ý giảm giá kích cầu dịp lễ.",
        )
        self.assertEqual(decision_result["status"], "EXECUTED")

        # Step 5: Verify Atomic Execution
        product.refresh_from_db()
        self.assertEqual(product.unit_price, Decimal("7500000"))

        # Step 6: Verify Complete Audit Log Sequence
        logs = AuditLog.objects.filter(workspace=self.retail_ws).values_list("action", flat=True)
        self.assertIn("AI_MUTATION_REQUESTED", logs)
        self.assertIn("APPROVAL_CREATED", logs)
        self.assertIn("MUTATION_EXECUTED", logs)
