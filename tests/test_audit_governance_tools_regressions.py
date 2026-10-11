"""Acceptance regressions for the 11 October audit; only isolated test data."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolPermissionDenied, ToolValidationError, handle_schedule_task
from apps.audit.models import AuditLog
from apps.knowledge.services import detect_and_handle_mutation_request
from apps.knowledge.tools import (
    get_category_profit_margins,
    get_customer_order_history,
    get_branch_sales_analytics,
    get_inter_branch_transfer_recommendations,
    get_sales_summary,
    get_sales_trend_analytics,
    get_service_ticket_summary,
    get_stockout_risk_summary,
    get_spatial_ticket_clusters,
    get_technician_safety_compliance,
    get_technician_skills_summary,
    get_top_selling_products,
)
from apps.retail.models import Branch, Category, Customer, Order, OrderItem, Product, StockBalance
from apps.service_ops.models import Employee, LaborEntry, Service, ServiceRequest, ServiceRequestStatus, Task
from apps.workspaces.models import Workspace, WorkspaceMembership


class AuditGovernanceToolsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ws = Workspace.objects.create(code="audit-governance", name="Audit", workspace_type="RETAIL")
        cls.other_ws = Workspace.objects.create(code="audit-foreign", name="Other", workspace_type="SERVICE")
        cls.admin = User.objects.create_superuser(username="audit-root", email="audit-root@example.com")
        cls.manager = User.objects.create_user(username="audit-manager", email="audit-manager@example.com")
        role = Role.objects.create(name="AUDIT_TOOLS_MANAGER")
        for code in ("retail.view_product", "service.view_employee", "retail.view_order", "service.view_request"):
            perm, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split(".")[0]})
            role.permissions.add(perm)
        WorkspaceMembership.objects.create(user=cls.manager, workspace=cls.ws, role=role, is_active=True)
        cls.customer = Customer.objects.create(workspace=cls.ws, code="KNOWN", name="Known customer")
        cls.category = Category.objects.create(workspace=cls.ws, code="KEYBOARDS", name="Keyboards")
        cls.product = Product.objects.create(workspace=cls.ws, category=cls.category, sku="KEY1", name="Keyboard", unit_price=100, cost_price=40)
        cls.branch = Branch.objects.create(workspace=cls.ws, code="MAIN", name="Main", address="A")
        cls.service = Service.objects.create(workspace=cls.ws, code="REPAIR", name="Repair")

    def order(self, code, status="PENDING", total=100, reserved=False):
        return Order.objects.create(
            workspace=self.ws, customer=self.customer, branch=self.branch,
            order_number=code, order_date=timezone.localdate(), order_timestamp=timezone.now(),
            status=status, total_amount=total, fulfillment_stock_reserved=reserved,
        )

    def propose(self, order, new_status):
        proposal = execute_tool("update_order_status", self.ws, self.admin, {"order_id": order.pk, "new_status": new_status})
        return ApprovalRequest.objects.get(pk=proposal["approval_request_id"])

    def ticket(self, code, location=None, workspace=None, customer=None, service=None, **kwargs):
        return ServiceRequest.objects.create(
            workspace=workspace or self.ws, customer=customer or self.customer, service=service or self.service,
            request_number=code, title=code, description="Audit test", location=location, **kwargs,
        )

    def test_stockout_tool_preserves_unassessed_demand_and_per_product_freshness(self):
        products = [{"product_id": self.product.pk, "demand_assessment": {"status": "STALE_HISTORY", "period_end": "2025-01-01"}, "inventory_assessment": {"verified_record": False}}]
        dashboard = {
            "branch_name": "Main", "out_of_stock_count": 0, "high_risk_count": 0,
            "medium_risk_count": 0, "low_risk_count": 1, "total_products_tracked": 1,
            "unassessed_demand_count": 1, "inventory_unverified_count": 1,
            "verified_out_of_stock_count": 0, "products_at_risk": products,
        }
        with patch("apps.retail.stockout_services.get_stockout_risk_dashboard_data", return_value=dashboard):
            result = get_stockout_risk_summary(self.ws, self.manager)
        self.assertEqual(result["unassessed_demand_count"], 1)
        self.assertEqual(result["inventory_unverified_count"], 1)
        self.assertEqual(result["verified_out_of_stock_count"], 0)
        self.assertEqual(result["products_at_risk"][0]["demand_assessment"], products[0]["demand_assessment"])
        self.assertEqual(result["products_at_risk"][0]["inventory_assessment"], products[0]["inventory_assessment"])

    def test_schedule_task_requires_ticket_before_pending_approval(self):
        self.ticket("DO-NOT-GUESS")
        for ticket_id in (None, "1", True, 0, -1):
            with self.subTest(ticket_id=ticket_id), self.assertRaises(ToolValidationError):
                parameters = {"title": "Explicit ticket required"}
                if ticket_id is not None:
                    parameters["ticket_id"] = ticket_id
                execute_tool("schedule_task", self.ws, self.admin, parameters)
        self.assertFalse(ApprovalRequest.objects.filter(proposed_action="schedule_task").exists())
        self.assertFalse(Task.objects.exists())

    def test_schedule_task_direct_handler_never_uses_first_ticket(self):
        self.ticket("DO-NOT-GUESS")
        with self.assertRaises(ToolValidationError):
            handle_schedule_task(self.ws, self.admin, {"title": "Missing ticket"})
        self.assertFalse(Task.objects.exists())

    def test_schedule_task_rejects_foreign_ticket_before_approval(self):
        foreign_customer = Customer.objects.create(workspace=self.other_ws, code="SCHED-C", name="Foreign customer")
        foreign_service = Service.objects.create(workspace=self.other_ws, code="SCHED-S", name="Foreign service")
        ticket = self.ticket("FOREIGN-TASK", workspace=self.other_ws, customer=foreign_customer, service=foreign_service)
        with self.assertRaises(ToolValidationError):
            execute_tool("schedule_task", self.ws, self.admin, {"title": "Foreign ticket", "ticket_id": ticket.pk})
        self.assertFalse(ApprovalRequest.objects.filter(proposed_action="schedule_task").exists())
        self.assertFalse(Task.objects.exists())

    def test_schedule_task_approval_binds_only_explicit_ticket(self):
        first_ticket = self.ticket("FIRST-UNRELATED")
        chosen_ticket = self.ticket("CHOSEN-TASK")
        proposal = execute_tool("schedule_task", self.ws, self.admin, {"title": "Approved explicit task", "ticket_id": chosen_ticket.pk})
        self.assertFalse(Task.objects.exists())
        approval = ApprovalRequest.objects.get(pk=proposal["approval_request_id"])
        result = process_approval_decision(approval, self.admin, "APPROVED")
        self.assertEqual(result["status"], "EXECUTED")
        task = Task.objects.get()
        self.assertEqual(task.service_request_id, chosen_ticket.pk)
        self.assertEqual(task.title, "Approved explicit task")
        self.assertFalse(Task.objects.filter(service_request=first_ticket).exists())

    def test_dispatch_parser_does_not_match_employee_code_prefix(self):
        ticket = self.ticket("PREFIX-TICKET")
        Employee.objects.create(workspace=self.ws, code="E1", full_name="Recorded technician")
        result = detect_and_handle_mutation_request(f"Phân công ticket #{ticket.pk} cho E10", self.ws, self.admin)
        self.assertIsNone(result)
        self.assertFalse(ApprovalRequest.objects.exists())
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_employee_id)

    def test_dispatch_parser_accepts_whole_employee_code_without_direct_mutation(self):
        ticket = self.ticket("EXACT-TECH")
        employee = Employee.objects.create(workspace=self.ws, code="E1", full_name="Recorded technician")
        result = detect_and_handle_mutation_request(f"Phân công ticket #{ticket.pk} cho E1", self.ws, self.admin)
        approval = ApprovalRequest.objects.get(pk=result["approval_request_id"])
        self.assertEqual(approval.parameters, {"ticket_id": ticket.pk, "employee_id": employee.pk})
        self.assertEqual(approval.status, "PENDING")
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_employee_id)
        self.assertFalse(Task.objects.exists())

    def test_mutation_parser_rejects_partial_integer_ids(self):
        order = self.order("PARTIAL-ID")
        ticket = self.ticket("PARTIAL-TICKET")
        employee = Employee.objects.create(workspace=self.ws, code="EXACT", full_name="Recorded technician")
        for suffix in ("abc", ".5", "_other"):
            queries = [
                f"Cập nhật đơn hàng #{order.pk}{suffix} sang confirmed",
                f"Điều chỉnh giá sản phẩm #{self.product.pk}{suffix} thành 1000",
                f"Phân công ticket #{ticket.pk}{suffix} cho nhân viên #{employee.pk}",
                f"Phân công ticket #{ticket.pk} cho nhân viên #{employee.pk}{suffix}",
                f"Lập lịch 'Explicit task' cho ticket #{ticket.pk}{suffix}",
            ]
            for query in queries:
                with self.subTest(query=query), self.assertRaises(ValueError):
                    detect_and_handle_mutation_request(query, self.ws, self.admin)
        self.assertFalse(ApprovalRequest.objects.exists())
        self.assertFalse(Task.objects.exists())

    def test_order_status_parser_uses_explicit_destination_not_first_status(self):
        order = self.order("DESTINATION")
        result = detect_and_handle_mutation_request(f"Cập nhật đơn hàng #{order.pk} từ pending sang confirmed", self.ws, self.admin)
        approval = ApprovalRequest.objects.get(pk=result["approval_request_id"])
        self.assertEqual(approval.parameters, {"order_id": order.pk, "new_status": "CONFIRMED"})
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")
        process_approval_decision(approval, self.admin, "APPROVED")
        order.refresh_from_db()
        self.assertEqual(order.status, "CONFIRMED")

    def test_order_status_parser_rejects_ambiguous_multiple_statuses(self):
        order = self.order("AMBIGUOUS-STATUS")
        for phrase in ("pending confirmed", "sang pending hoặc confirmed", "sang pending rồi sang confirmed"):
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                detect_and_handle_mutation_request(f"Cập nhật đơn hàng #{order.pk} {phrase}", self.ws, self.admin)
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_order_status_parser_does_not_match_embedded_status_words(self):
        order = self.order("STATUS-TOKEN")
        for phrase in ("topending", "unconfirmed", "completedness"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(detect_and_handle_mutation_request(f"Update order #{order.pk} {phrase}", self.ws, self.admin))
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_margin_category_filter_is_exact_not_a_prefix_or_workspace_total(self):
        second_category = Category.objects.create(workspace=self.ws, code="KEYBOARDS-PLUS", name="Keyboards Plus")
        second_product = Product.objects.create(workspace=self.ws, category=second_category, sku="EXTRA", name="Extra product", unit_price=200, cost_price=30)
        order = self.order("CATEGORY-SCOPE", "COMPLETED", total=300)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=100)
        OrderItem.objects.create(order=order, product=second_product, quantity=1, unit_price=200)
        for selector in ("KEYBOARDS", "keyboards", str(self.category.pk)):
            with self.subTest(selector=selector):
                result = get_category_profit_margins(self.ws, self.admin, category=selector)
                self.assertEqual(result["total_revenue_raw"], 100)
                self.assertEqual([row["category_id"] for row in result["categories"]], [self.category.pk])
                self.assertEqual(result["category_match_status"], "EXACT_MATCH")
                self.assertIsNone(result["order_to_items_delta_raw"])

    def test_margin_unknown_or_foreign_category_never_falls_back_to_all(self):
        Category.objects.create(workspace=self.other_ws, code="FOREIGN-MARGIN", name="Foreign margin")
        OrderItem.objects.create(order=self.order("LOCAL-MARGIN", "COMPLETED"), product=self.product, quantity=1, unit_price=100)
        for selector in ("DOES-NOT-EXIST", "FOREIGN-MARGIN", "KEY"):
            with self.subTest(selector=selector):
                result = get_category_profit_margins(self.ws, self.admin, category=selector)
                self.assertEqual(result["categories"], [])
                self.assertEqual(result["total_revenue_raw"], 0)
                self.assertEqual(result["category_match_status"], "NOT_FOUND")

    def test_margin_ambiguous_category_name_never_selects_first(self):
        Category.objects.create(workspace=self.ws, code="DUPLICATE-NAME", name="Keyboards")
        OrderItem.objects.create(order=self.order("AMBIGUOUS-MARGIN", "COMPLETED"), product=self.product, quantity=1, unit_price=100)
        result = get_category_profit_margins(self.ws, self.admin, category="Keyboards")
        self.assertEqual(result["categories"], [])
        self.assertEqual(result["total_revenue_raw"], 0)
        self.assertEqual(result["category_match_status"], "AMBIGUOUS")

    def test_approval_cannot_skip_confirmation(self):
        order = self.order("SKIP")
        request = self.propose(order, "COMPLETED")
        with self.assertRaises(ToolValidationError):
            process_approval_decision(request, self.admin, "APPROVED")
        order.refresh_from_db()
        request.refresh_from_db()
        self.assertEqual(order.status, "PENDING")
        self.assertEqual(request.status, "PENDING")
        self.assertTrue(AuditLog.objects.filter(action="MUTATION_FAILED", entity_id=str(request.pk)).exists())

    def test_approval_cannot_cancel_terminal_completed_order(self):
        order = self.order("TERMINAL", status="COMPLETED")
        with self.assertRaises(ToolValidationError):
            process_approval_decision(self.propose(order, "CANCELLED"), self.admin, "APPROVED")
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")

    def test_approval_cancel_releases_reservation_once_and_has_domain_audit(self):
        order = self.order("RESERVED", reserved=True)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=100)
        stock = StockBalance.objects.create(workspace=self.ws, branch=self.branch, product=self.product, quantity_on_hand=9)
        request = self.propose(order, "CANCELLED")
        process_approval_decision(request, self.admin, "APPROVED")
        process_approval_decision(request, self.admin, "APPROVED")
        stock.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 10)
        self.assertIsNotNone(order.fulfillment_stock_released_at)
        self.assertEqual(AuditLog.objects.filter(action="ORDER_CANCELLED", entity_id=str(order.pk)).count(), 1)

    def test_missing_inventory_rolls_back_cancellation(self):
        order = self.order("NO-BALANCE", reserved=True)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=100)
        with self.assertRaises(ToolValidationError):
            process_approval_decision(self.propose(order, "CANCELLED"), self.admin, "APPROVED")
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")
        self.assertIsNone(order.fulfillment_stock_released_at)

    def test_empty_spatial_data_never_invents_hotspot(self):
        result = get_spatial_ticket_clusters(self.ws, self.admin)
        self.assertEqual(result["clusters"], [])
        self.assertIsNone(result["hotspot_region"])
        self.assertEqual(result["located_ticket_count"], 0)

    def test_spatial_counts_derive_from_real_locations_and_preserve_workspace(self):
        self.ticket("T1", Point(106.7000, 10.7700, srid=4326))
        self.ticket("T2", Point(106.7000, 10.7700, srid=4326))
        self.ticket("T3", Point(106.8100, 10.8200, srid=4326))
        self.ticket("UNLOCATED")
        foreign_customer = Customer.objects.create(workspace=self.other_ws, code="F", name="Foreign")
        foreign_service = Service.objects.create(workspace=self.other_ws, code="F", name="Foreign")
        self.ticket("FOREIGN", Point(106.7000, 10.7700, srid=4326), self.other_ws, foreign_customer, foreign_service)
        result = get_spatial_ticket_clusters(self.ws, self.admin)
        self.assertEqual(result["total_active_tickets"], 4)
        self.assertEqual(result["located_ticket_count"], 3)
        self.assertEqual(result["unlocated_ticket_count"], 1)
        self.assertEqual(sorted(c["ticket_count"] for c in result["clusters"]), [1, 2])
        self.assertEqual(sum(c["ticket_count"] for c in result["clusters"]), 3)
        self.assertEqual(result["method"], "WEB_MERCATOR_GRID_1000M")

    def test_unlocated_and_cancelled_tickets_are_not_fabricated_regions(self):
        self.ticket("UNLOCATED")
        self.ticket("CANCELLED", Point(106.7, 10.77, srid=4326), status="CANCELLED")
        result = get_spatial_ticket_clusters(self.ws, self.admin)
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["unlocated_ticket_count"], 1)

    def test_explicit_missing_customer_never_falls_back(self):
        result = get_customer_order_history(self.ws, self.admin, customer_name="NONEXISTENT PERSON")
        self.assertFalse(result["customer_found"])
        self.assertNotIn("customer_name", result)

    def test_customer_lookup_without_selector_asks_instead_of_disclosing_first(self):
        result = get_customer_order_history(self.ws, self.admin)
        self.assertFalse(result["customer_found"])
        self.assertEqual(result["error_code"], "CUSTOMER_REQUIRED")

    def test_ambiguous_partial_customer_name_never_selects_arbitrary_customer(self):
        Customer.objects.create(workspace=self.ws, code="SECOND", name="Known customer two")
        result = get_customer_order_history(self.ws, self.admin, customer_name="customer")
        self.assertFalse(result["customer_found"])
        self.assertEqual(result["error_code"], "CUSTOMER_AMBIGUOUS")

    def test_numeric_foreign_customer_id_cannot_fall_back_to_name(self):
        foreign = Customer.objects.create(workspace=self.other_ws, code="OTHER", name="Other")
        Customer.objects.create(workspace=self.ws, code=str(foreign.pk), name="Collision")
        result = get_customer_order_history(self.ws, self.admin, customer_id=foreign.pk)
        self.assertFalse(result["customer_found"])

    def test_history_aggregates_all_completed_orders_before_limiting_details(self):
        for index in range(12):
            OrderItem.objects.create(order=self.order(f"DONE-{index}", "COMPLETED"), product=self.product, quantity=1, unit_price=100)
        cancelled_product = Product.objects.create(workspace=self.ws, category=self.category, sku="NEVER-BOUGHT", name="Cancelled only", unit_price=900)
        OrderItem.objects.create(order=self.order("CANCELLED", "CANCELLED", total=900), product=cancelled_product, quantity=1, unit_price=900)
        self.order("NOT-BOUGHT", "PENDING", total=600)
        result = get_customer_order_history(self.ws, self.admin, customer_code=self.customer.code)
        self.assertEqual(result["order_count"], 14)
        self.assertEqual(result["completed_order_count"], 12)
        self.assertEqual(result["total_spent_raw"], 1200)
        self.assertEqual(len(result["orders"]), 10)
        self.assertNotIn("Cancelled only", result["purchased_products_summary"])

    def test_sales_revenue_excludes_cancelled_and_unfulfilled_orders(self):
        self.order("DONE", "COMPLETED", 200)
        self.order("WAIT", "CONFIRMED", 700)
        self.order("CANCEL", "CANCELLED", 900)
        result = get_sales_summary(self.ws, self.admin)
        self.assertEqual(result["total_revenue_raw"], 200)
        self.assertEqual(result["order_pipeline_total_raw"], 900)
        self.assertEqual(result["revenue_statuses"], ["COMPLETED"])

    def test_sales_analytics_share_completed_basis_and_equal_period_lengths(self):
        OrderItem.objects.create(order=self.order("DONE", "COMPLETED", 100), product=self.product, quantity=1, unit_price=100)
        OrderItem.objects.create(order=self.order("WAIT", "PENDING", 900), product=self.product, quantity=9, unit_price=100)
        ranking = get_top_selling_products(self.ws, self.admin)
        branch = get_branch_sales_analytics(self.ws, self.admin)
        trend = get_sales_trend_analytics(self.ws, self.admin, period_days=1)
        self.assertEqual(ranking["rankings"][0]["quantity_sold"], 1)
        self.assertEqual(branch["branches"][0]["revenue"], 100)
        self.assertEqual(trend["current_revenue"], 100)
        self.assertEqual(trend["current_units"], 1)
        today = timezone.localdate().isoformat()
        self.assertEqual(trend["current_period"], f"{today} đến {today}")

    def test_margin_categories_are_exact_and_use_discounted_item_subtotals(self):
        second = Category.objects.create(workspace=self.ws, code="MONITORS", name="Monitors")
        monitor = Product.objects.create(workspace=self.ws, category=second, sku="MON1", name="Monitor", unit_price=200, cost_price=80)
        order = self.order("CATEGORY-DONE", "COMPLETED", total=240)
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=100, discount=10)
        OrderItem.objects.create(order=order, product=monitor, quantity=1, unit_price=200, discount=50)
        OrderItem.objects.create(order=self.order("WAIT"), product=monitor, quantity=1, unit_price=200)
        result = get_category_profit_margins(self.ws, self.admin)
        categories = {row["category_key"]: row for row in result["categories"]}
        self.assertEqual(set(categories), {"KEYBOARDS", "MONITORS"})
        self.assertEqual(categories["KEYBOARDS"]["revenue_raw"], 90)
        self.assertEqual(categories["MONITORS"]["revenue_raw"], 150)
        self.assertEqual(result["completed_order_total_raw"], 240)
        self.assertFalse(result["historical_cogs_verified"])
        self.assertEqual(categories["KEYBOARDS"]["status"], "CURRENT_COST_ESTIMATE")
        self.assertIsNone(categories["KEYBOARDS"]["target_margin_pct"])

    def test_margin_missing_cost_is_unknown_not_eighty_percent_assumption(self):
        self.product.cost_price = 0
        self.product.save(update_fields=["cost_price"])
        OrderItem.objects.create(order=self.order("UNKNOWN", "COMPLETED"), product=self.product, quantity=1, unit_price=100)
        result = get_category_profit_margins(self.ws, self.admin)
        self.assertIsNone(result["overall_gross_margin_pct"])
        self.assertEqual(result["missing_cost_item_count"], 1)
        self.assertEqual(result["categories"][0]["status"], "INSUFFICIENT_COST_DATA")
        self.assertIsNone(result["categories"][0]["estimated_cost_raw"])

    def test_canonical_permissions_work_both_registry_and_handler(self):
        for tool in ("get_inter_branch_transfer_recommendations", "get_technician_safety_compliance"):
            with self.subTest(tool=tool):
                self.assertEqual(execute_tool(tool, self.ws, self.manager, {})["status"], "EXECUTED")
        outsider = User.objects.create_user(username="no-grants", email="no-grants@example.com")
        with self.assertRaises(ToolPermissionDenied):
            execute_tool("get_technician_safety_compliance", self.ws, outsider, {})

    def test_transfer_unknown_stock_is_not_zero_and_costs_are_not_inferred(self):
        second = Branch.objects.create(workspace=self.ws, code="SECOND", name="Bình Thạnh", address="B")
        StockBalance.objects.create(workspace=self.ws, branch=self.branch, product=self.product, quantity_on_hand=20)
        result = get_inter_branch_transfer_recommendations(self.ws, self.manager)
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["missing_balance_count"], 1)
        StockBalance.objects.create(workspace=self.ws, branch=second, product=self.product, quantity_on_hand=1)
        result = get_inter_branch_transfer_recommendations(self.ws, self.manager)
        self.assertEqual(len(result["recommendations"]), 1)
        self.assertIsNone(result["recommendations"][0]["estimated_transport_cost_vnd"])
        self.assertIsNone(result["recommendations"][0]["delivery_sla_hours"])
        self.assertFalse(result["transport_policy_verified"])

    def test_nearby_technician_tool_does_not_use_a_default_city_for_missing_coordinates(self):
        ticket = self.ticket("NO-COORDS")
        result = execute_tool("query_nearby_technicians", self.ws, self.manager, {"ticket_id": ticket.pk})["result"]
        self.assertIsNone(result["origin_coordinates"])
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["data_quality"], "NO_TICKET_LOCATION")

    def test_nearby_technician_tool_preserves_real_availability_and_unknown_skill_match(self):
        ticket = self.ticket("LOCATED", Point(106.7, 10.77, srid=4326))
        Employee.objects.create(workspace=self.ws, code="BUSY", full_name="Busy tech", current_location=Point(106.7, 10.77, srid=4326), is_available=False)
        Employee.objects.create(workspace=self.ws, code="AVAILABLE", full_name="Available tech", current_location=Point(106.7, 10.77, srid=4326), is_available=True)
        result = execute_tool("query_nearby_technicians", self.ws, self.manager, {"ticket_id": ticket.pk})["result"]
        rows = {row["code"]: row for row in result["candidates"]}
        self.assertEqual(rows["BUSY"]["total_score"], 0)
        self.assertFalse(rows["BUSY"]["is_available"])
        self.assertIsNone(rows["AVAILABLE"]["subscores"]["skill_score"])
        self.assertFalse(rows["AVAILABLE"]["skill_match_verified"])

    def test_safety_never_infers_certificates_or_overtime_from_name_and_tasks(self):
        technician = Employee.objects.create(workspace=self.ws, code="TECH", full_name="Vũ Hoàng Nam", skills=[])
        Task.objects.create(service_request=self.ticket("TASK"), assigned_to=technician, title="Task")
        result = get_technician_safety_compliance(self.ws, self.admin)
        row = result["technicians_compliance"][0]
        self.assertEqual(row["certifications"], [])
        self.assertIsNone(row["estimated_monthly_overtime_hours"])
        self.assertIsNone(row["night_shift_allowance_eligible"])
        self.assertIsNone(row["ot_compliant"])
        self.assertIsNone(row["iso_27001_nda_required"])
        self.assertEqual(row["status"], "NOT_VERIFIED")

    def test_technician_skill_matching_never_infers_skills_from_a_name(self):
        Employee.objects.create(workspace=self.ws, code="NAME-ONLY", full_name="CCNA expert", skills=[])
        result = get_technician_skills_summary(self.ws, self.manager, skill="CCNA")
        self.assertEqual(result["matching_count"], 0)

    def test_safety_reports_real_labor_entries_but_not_legal_compliance(self):
        technician = Employee.objects.create(workspace=self.ws, code="TECH", full_name="Tech", skills=["An toàn điện"], current_workload_score=0)
        task = Task.objects.create(service_request=self.ticket("LABOR"), assigned_to=technician, title="Task")
        LaborEntry.objects.create(task=task, employee=technician, started_at=timezone.now(), ended_at=timezone.now(), duration_minutes=120, hourly_rate_snapshot=100, labor_cost=200)
        result = get_technician_safety_compliance(self.ws, self.admin)
        row = result["technicians_compliance"][0]
        self.assertEqual(row["recorded_monthly_labor_hours"], 2)
        self.assertEqual(row["recorded_skills"], ["An toàn điện"])
        self.assertFalse(row["certifications_verified"])
        self.assertEqual(row["workload_score"], 0)

    def test_ticket_status_distribution_is_scoped_complete_and_respects_exclude_closed(self):
        statuses = ["OPEN", "OPEN", "ASSIGNED", "IN_PROGRESS", "CLOSED", "CANCELLED"]
        for index, status in enumerate(statuses):
            self.ticket(f"STATUS-{index}", status=status)
        foreign_customer = Customer.objects.create(workspace=self.other_ws, code="STATUS-C", name="Foreign customer")
        foreign_service = Service.objects.create(workspace=self.other_ws, code="STATUS-S", name="Foreign service")
        self.ticket("FOREIGN-STATUS", workspace=self.other_ws, customer=foreign_customer, service=foreign_service, status="OPEN")
        result = get_service_ticket_summary(self.ws, self.manager)
        self.assertEqual(result["status_distribution"], {
            "OPEN": 2, "ASSIGNED": 1, "IN_PROGRESS": 1, "RESOLVED": 0, "CLOSED": 1, "CANCELLED": 1,
        })
        self.assertEqual(sum(result["status_distribution"].values()), result["total_tickets"])
        self.assertEqual(result["total_tickets"], 6)
        filtered = get_service_ticket_summary(self.ws, self.manager, exclude_closed=True)
        self.assertEqual(filtered["total_tickets"], 4)
        self.assertEqual(filtered["status_distribution"], {
            "OPEN": 2, "ASSIGNED": 1, "IN_PROGRESS": 1, "RESOLVED": 0, "CLOSED": 0, "CANCELLED": 0,
        })
        self.assertEqual(sum(filtered["status_distribution"].values()), filtered["total_tickets"])
        empty_workspace = Workspace.objects.create(code="status-empty", name="Empty", workspace_type="SERVICE")
        empty = get_service_ticket_summary(empty_workspace, self.admin)
        self.assertEqual(empty["status_distribution"], {status: 0 for status in ServiceRequestStatus.values})
        self.assertEqual(empty["total_tickets"], 0)
