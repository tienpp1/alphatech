"""
Enterprise Q&A Vietnamese Benchmark Test Suite (Q89 - Q100).

Validates end-to-end intent classification, tool registry execution, controlled approvals,
and grounded answer generation for 12 complex enterprise scenarios:
1. Category Gross Profit Margins & COGS
2. Price & Margin Analysis for Accessories
3. Customer Churn Risk (Inactivity > 45 days)
4. Enterprise Customer Churn with SLA Impact
5. Inter-branch Inventory Transfer (Surplus -> Deficit)
6. Multi-Branch Inventory Balancing & Transport Cost
7. Technician Overtime Safety & Workload Limits
8. Safety Certification & Night Shift Compliance
9. Policy & SOP Document RAG Retrieval
10. What-If Cost & Margin Simulation
11. Controlled Mutation: Inter-branch Stock Transfer Approval
12. Controlled Mutation: Markdown / Price Adjustment Approval
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Branch, Category, Customer, Order, OrderItem, Product, StockBalance
from apps.service_ops.models import Employee, ServiceRequest, Task, TaskStatus, Service, ServiceCategory
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolRegistry
from apps.knowledge.intent_router import BusinessIntent, classify_business_intent
from apps.knowledge.tools import (
    get_category_profit_margins,
    get_customer_churn_risk_summary,
    get_inter_branch_transfer_recommendations,
    get_technician_safety_compliance,
)
from apps.knowledge.services import ask_ai_assistant, detect_and_handle_mutation_request


class EnterpriseQnABenchmarkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Setup Workspaces
        cls.workspace = Workspace.objects.create(
            name="MegaTech Enterprise",
            code="MEGATECH",
            workspace_type="RETAIL",
        )
        cls.user = User.objects.create_user(
            username="analyst_corp",
            email="analyst@megatech.vn",
            password="AnalystPassword123!",
            is_active=True,
        )
        cls.admin_role = Role.objects.filter(name="WORKSPACE_ADMIN").first() or Role.objects.create(name="WORKSPACE_ADMIN")
        perms = []
        for codename, module in [
            ("ai.chat", "ai"), ("retail.view_order", "retail"),
            ("retail.view_customer", "retail"), ("retail.view_stock", "retail"),
            ("service.view_technician", "service_ops"), ("service.view_request", "service_ops"),
            ("retail.manage_product", "retail"), ("retail.manage_stock", "retail"),
        ]:
            perm, _ = Permission.objects.get_or_create(codename=codename, defaults={"name": codename, "module": module})
            perms.append(perm)
        cls.admin_role.permissions.add(*perms)
        WorkspaceMembership.objects.create(
            user=cls.user,
            workspace=cls.workspace,
            role=cls.admin_role,
            is_active=True,
            is_default=True,
        )

        # 2. Setup Branches
        cls.branch_q1 = Branch.objects.create(
            workspace=cls.workspace,
            name="Chi nhánh Quận 1",
            code="CN-Q1",
            address="12 Lê Duẩn, Q1, TP.HCM",
            is_active=True,
        )
        cls.branch_bt = Branch.objects.create(
            workspace=cls.workspace,
            name="Chi nhánh Bình Thạnh",
            code="CN-BT",
            address="45 Điện Biên Phủ, Bình Thạnh, TP.HCM",
            is_active=True,
        )

        # 3. Setup Categories & Products
        cls.cat_laptop = Category.objects.create(
            workspace=cls.workspace,
            name="Laptop",
            code="CAT-LAPTOP",
        )
        cls.cat_accessory = Category.objects.create(
            workspace=cls.workspace,
            name="Linh kiện",
            code="CAT-ACC",
        )

        cls.prod_laptop = Product.objects.create(
            workspace=cls.workspace,
            category=cls.cat_laptop,
            sku="NB-DELL-XPS15",
            name="Dell XPS 15",
            unit_price=Decimal("35000000.00"),
            cost_price=Decimal("26000000.00"),
            is_active=True,
        )
        cls.prod_ram = Product.objects.create(
            workspace=cls.workspace,
            category=cls.cat_accessory,
            sku="RAM-DDR5-16G",
            name="RAM DDR5 16GB",
            unit_price=Decimal("1500000.00"),
            cost_price=Decimal("1250000.00"),
            is_active=True,
        )

        # 4. Stock Balances (Imbalance: BT has surplus, Q1 has deficit)
        StockBalance.objects.create(
            workspace=cls.workspace,
            branch=cls.branch_bt,
            product=cls.prod_laptop,
            quantity_on_hand=15,
        )
        StockBalance.objects.create(
            workspace=cls.workspace,
            branch=cls.branch_q1,
            product=cls.prod_laptop,
            quantity_on_hand=2,
        )

        # 5. Customers & Orders
        cls.customer_vip = Customer.objects.create(
            workspace=cls.workspace,
            code="CUST-VIP-01",
            name="Tập đoàn FSI Global",
            phone="0901234567",
            customer_segment="VIP",
        )
        cls.customer_retail = Customer.objects.create(
            workspace=cls.workspace,
            code="CUST-RET-02",
            name="Nguyễn Văn A",
            phone="0912345678",
            customer_segment="STANDARD",
        )

        cls.order_recent = Order.objects.create(
            workspace=cls.workspace,
            branch=cls.branch_q1,
            customer=cls.customer_retail,
            order_number="ORD-2026-001",
            total_amount=Decimal("35000000.00"),
            status="COMPLETED",
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
        )
        OrderItem.objects.create(
            order=cls.order_recent,
            product=cls.prod_laptop,
            quantity=1,
            unit_price=Decimal("35000000.00"),
            subtotal=Decimal("35000000.00"),
        )

        # 6. Service Ops: Technicians & Tasks
        cls.tech1 = Employee.objects.create(
            workspace=cls.workspace,
            code="EMP-TECH-01",
            full_name="Trần Văn Kỹ Thuật",
            email="tech1@megatech.vn",
            phone="0988776655",
            skills=["Hardware", "Network", "An toàn điện"],
            is_available=True,
            hourly_labor_rate=Decimal("150000.00"),
        )
        cls.tech2 = Employee.objects.create(
            workspace=cls.workspace,
            code="EMP-TECH-02",
            full_name="Lê Hoàng Bảo Trì",
            email="tech2@megatech.vn",
            phone="0977665544",
            skills=["System", "Software"],
            is_available=False,
            hourly_labor_rate=Decimal("180000.00"),
        )

        # Create service request & active tasks using canonical required relations
        cls.service_catalog = Service.objects.create(
            workspace=cls.workspace, code="SRV-QNA-001", name="Hỗ trợ vận hành",
            category=ServiceCategory.DATABASE_CONSULTING, base_fee=Decimal("0.00"), is_active=True,
        )
        cls.service_customer = Customer.objects.create(
            workspace=cls.workspace, code="CUST-QNA-SVC", name="Khách hàng dịch vụ",
        )
        cls.service_req = ServiceRequest.objects.create(
            workspace=cls.workspace,
            customer=cls.service_customer,
            service=cls.service_catalog,
            request_number="SR-2026-001",
            title="Bảo trì hạ tầng trung tâm dữ liệu",
            status="IN_PROGRESS",
            priority="HIGH",
        )

        Task.objects.create(
            service_request=cls.service_req,
            assigned_to=cls.tech1,
            title="Bảo trì UPS trung tâm dữ liệu",
            status=TaskStatus.IN_PROGRESS,
            priority="HIGH",
        )
        for i in range(3):
            Task.objects.create(
                service_request=cls.service_req,
                assigned_to=cls.tech2,
                title=f"Xử lý sự cố máy chủ #{i+1}",
                status=TaskStatus.IN_PROGRESS,
                priority="HIGH",
            )

    # -------------------------------------------------------------------------
    # Intent Classification Benchmarks (Q89 - Q100)
    # -------------------------------------------------------------------------
    def test_q89_profit_margin_laptop_vs_accessories(self):
        r = classify_business_intent("Biên lợi nhuận gộp danh mục laptop so với linh kiện thế nào?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.PROFIT_MARGIN_ANALYSIS)
        self.assertIn("get_category_profit_margins", r["tools"])

    def test_q90_cost_and_margin_for_accessories(self):
        r = classify_business_intent("Giá vốn và tỷ suất lợi nhuận linh kiện quý này đạt bao nhiêu?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.PROFIT_MARGIN_ANALYSIS)
        self.assertIn("get_category_profit_margins", r["tools"])

    def test_q91_customer_churn_risk_vip(self):
        r = classify_business_intent("Khách hàng VIP nào có nguy cơ rời bỏ hoặc không mua hàng trên 45 ngày?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_CHURN_RISK)
        self.assertIn("get_customer_churn_risk_summary", r["tools"])

    def test_q92_enterprise_churn_risk_with_sla(self):
        r = classify_business_intent("Có khách hàng doanh nghiệp nào sắp churn do sự cố ticket trễ hạn không?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_CHURN_RISK)
        self.assertIn("get_customer_churn_risk_summary", r["tools"])

    def test_q93_inter_branch_transfer_inquiry(self):
        r = classify_business_intent("Chi nhánh Bình Thạnh đang dư laptop, có nên điều chuyển tồn kho sang Quận 1 không?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.INTER_BRANCH_TRANSFER)
        self.assertIn("get_inter_branch_transfer_recommendations", r["tools"])

    def test_q94_inter_branch_balancing_optimization(self):
        r = classify_business_intent("Đề xuất điều chuyển tồn kho giữa các chi nhánh để tối ưu chi phí vận chuyển", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.INTER_BRANCH_TRANSFER)
        self.assertIn("get_inter_branch_transfer_recommendations", r["tools"])

    def test_q95_technician_overtime_compliance(self):
        r = classify_business_intent("Kỹ thuật viên nào đang làm thêm giờ vượt quá tiêu chuẩn trong tháng?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_COMPLIANCE)
        self.assertIn("get_technician_safety_compliance", r["tools"])

    def test_q96_safety_cert_and_night_allowance(self):
        r = classify_business_intent("Kiểm tra chứng chỉ an toàn lao động và phụ cấp ca đêm của kỹ thuật viên", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_COMPLIANCE)
        self.assertIn("get_technician_safety_compliance", r["tools"])

    def test_q97_policy_sop_rag(self):
        r = classify_business_intent("Chính sách quy định đổi trả và quy trình bảo hành áp dụng ra sao?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    def test_q98_what_if_simulation_cost_increase(self):
        r = classify_business_intent("Nếu giá vốn tăng 10% thì biên lợi nhuận thay đổi ra sao?", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)

    def test_q99_controlled_mutation_stock_transfer(self):
        r = classify_business_intent("Tạo đề xuất điều chuyển 2 laptop từ Bình Thạnh sang Quận 1", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_q100_controlled_mutation_price_markdown(self):
        r = classify_business_intent("Hạ giá 5% xả kho cho lô linh kiện tồn kho chậm luân chuyển", self.workspace)
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    # -------------------------------------------------------------------------
    # Tool Execution & Data Validation
    # -------------------------------------------------------------------------
    def test_tool_category_profit_margins_execution(self):
        res = get_category_profit_margins(self.workspace, self.user)
        self.assertIn("categories", res)
        self.assertIn("overall_gross_margin_pct", res)
        self.assertTrue(len(res["categories"]) >= 1)
        self.assertIn("total_revenue_formatted", res)

    def test_tool_customer_churn_risk_execution(self):
        res = get_customer_churn_risk_summary(self.workspace, self.user, inactivity_days=45)
        self.assertIn("at_risk_customers", res)
        self.assertIn("at_risk_count", res)
        self.assertIn("total_revenue_at_risk_formatted", res)

    def test_tool_inter_branch_transfer_execution(self):
        res = get_inter_branch_transfer_recommendations(self.workspace, self.user)
        self.assertIn("opportunities", res)
        self.assertTrue(len(res["opportunities"]) >= 1)
        opp = res["opportunities"][0]
        self.assertEqual(opp["source_branch"], "Chi nhánh Bình Thạnh")
        self.assertEqual(opp["destination_branch"], "Chi nhánh Quận 1")
        self.assertTrue(opp["recommended_transfer_quantity"] > 0)

    def test_tool_technician_safety_compliance_execution(self):
        res = get_technician_safety_compliance(self.workspace, self.user)
        self.assertIn("technicians_compliance", res)
        self.assertIn("total_technicians", res)
        self.assertEqual(res["total_technicians"], 2)
        tech_data = {t["name"]: t for t in res["technicians_compliance"]}
        self.assertIn("Trần Văn Kỹ Thuật", tech_data)
        self.assertIn("An toàn điện", tech_data["Trần Văn Kỹ Thuật"]["safety_certifications"])

    # -------------------------------------------------------------------------
    # Controlled Mutations: Zero Direct DB Write & Approval Request Creation
    # -------------------------------------------------------------------------
    def test_mutation_stock_transfer_creates_approval_request(self):
        initial_approvals = ApprovalRequest.objects.for_workspace(self.workspace).count()
        res = detect_and_handle_mutation_request(
            workspace=self.workspace,
            user=self.user,
            query="Lập đề xuất điều chuyển 2 laptop từ Bình Thạnh sang Quận 1",
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "APPROVAL_REQUIRED")
        self.assertEqual(res["tool_name"], "create_stock_transfer")
        self.assertEqual(ApprovalRequest.objects.for_workspace(self.workspace).count(), initial_approvals + 1)

    def test_mutation_price_markdown_creates_approval_request(self):
        initial_approvals = ApprovalRequest.objects.for_workspace(self.workspace).count()
        res = detect_and_handle_mutation_request(
            workspace=self.workspace,
            user=self.user,
            query="Đề xuất hạ giá 5% xả kho cho laptop để kích cầu",
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "APPROVAL_REQUIRED")
        self.assertEqual(res["tool_name"], "adjust_product_price")
        self.assertEqual(ApprovalRequest.objects.for_workspace(self.workspace).count(), initial_approvals + 1)

    # -------------------------------------------------------------------------
    # End-to-End Grounded Answer Generation
    # -------------------------------------------------------------------------
    def test_e2e_ask_ai_profit_margins(self):
        resp = ask_ai_assistant(
            workspace=self.workspace,
            user=self.user,
            query="Biên lợi nhuận gộp danh mục laptop hiện tại ra sao?",
        )
        self.assertIn("answer", resp)
        self.assertIn("Biên lợi nhuận", resp["answer"])
        self.assertIn("Laptop", resp["answer"])

    def test_e2e_ask_ai_inter_branch_transfer(self):
        resp = ask_ai_assistant(
            workspace=self.workspace,
            user=self.user,
            query="Đề xuất điều chuyển tồn kho giữa các chi nhánh",
        )
        self.assertIn("answer", resp)
        self.assertIn("Chi nhánh Bình Thạnh", resp["answer"])
        self.assertIn("Chi nhánh Quận 1", resp["answer"])
