"""
Comprehensive Automated Benchmark Test Suite: Vietnamese AI Business Intent Understanding.
Validates 77 realistic Vietnamese business queries covering all 26 requirement dimensions:
Retail, Service Ops, GIS, Forecasting, RAG, Hybrid, Ranking, Comparison, Trends, Follow-ups,
Ambiguity, Negation/Exclusion, and Controlled Mutations.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.knowledge.intent_router import (
    classify_business_intent,
    BusinessIntent,
    parse_date_range_from_text,
    extract_limit_and_ordering,
    extract_product_category,
    extract_comparison_entities,
    extract_negations_and_exclusions,
    resolve_follow_up_context,
)
from apps.knowledge.services import answer_grounded_query
from apps.retail.models import Category, Product, Branch, Customer, Order, OrderItem, OrderStatus, StockBalance
from apps.service_ops.models import Service, ServiceCategory, Employee, ServiceRequest, ServiceRequestStatus, ServiceRequestPriority, LaborEntry, Task, TaskStatus


class VietnameseBusinessIntentBenchmarkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Setup Dual Workspaces
        cls.ws_retail = Workspace.objects.create(
            code="retail-benchmark-ws",
            name="ABC Tech Benchmark Store",
            workspace_type=WorkspaceType.RETAIL,
        )
        cls.ws_service = Workspace.objects.create(
            code="service-benchmark-ws",
            name="XYZ IT Service Benchmark",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 2. Setup Superuser for Testing
        cls.user = User.objects.create_user(
            username="benchmark_admin",
            email="admin@benchmark.com",
            password="AdminPassword123!",
            is_superuser=True,
        )

        # 3. Setup Retail Catalog & Data
        cls.cat_laptop = Category.objects.create(workspace=cls.ws_retail, name="Laptop", code="laptop")
        cls.cat_phone = Category.objects.create(workspace=cls.ws_retail, name="Điện thoại", code="smartphone")
        cls.cat_mouse = Category.objects.create(workspace=cls.ws_retail, name="Chuột", code="mouse")
        cls.cat_comp = Category.objects.create(workspace=cls.ws_retail, name="Linh kiện", code="components")

        cls.prod_asus = Product.objects.create(
            workspace=cls.ws_retail, category=cls.cat_laptop, sku="ASUS-VIVO", name="Laptop ASUS VivoBook 14",
            unit_price=Decimal("15000000.00"), cost_price=Decimal("12000000.00"), is_active=True
        )
        cls.prod_lenovo = Product.objects.create(
            workspace=cls.ws_retail, category=cls.cat_laptop, sku="LENOVO-IDEA", name="Laptop Lenovo IdeaPad 3",
            unit_price=Decimal("14000000.00"), cost_price=Decimal("11000000.00"), is_active=True
        )
        cls.prod_mouse_logi = Product.objects.create(
            workspace=cls.ws_retail, category=cls.cat_mouse, sku="LOGI-GPRO", name="Chuột Logitech G Pro",
            unit_price=Decimal("2500000.00"), cost_price=Decimal("1800000.00"), is_active=True
        )

        cls.branch_q1 = Branch.objects.create(workspace=cls.ws_retail, code="BR-Q1", name="Chi nhánh Quận 1", is_active=True)
        cls.branch_q3 = Branch.objects.create(workspace=cls.ws_retail, code="BR-Q3", name="Chi nhánh Quận 3", is_active=True)

        cls.cust = Customer.objects.create(workspace=cls.ws_retail, code="CUST-01", name="Trần Văn Nam", phone="0911223344")

        # Create sample completed retail order
        today = timezone.now().date()
        cls.order1 = Order.objects.create(
            workspace=cls.ws_retail, order_number="ORD-BM-001", customer=cls.cust, branch=cls.branch_q1,
            order_date=today, order_timestamp=timezone.now(), status=OrderStatus.COMPLETED, total_amount=Decimal("30000000.00")
        )
        OrderItem.objects.create(order=cls.order1, product=cls.prod_asus, quantity=2, unit_price=Decimal("15000000.00"), subtotal=Decimal("30000000.00"))

        # Stock balances
        StockBalance.objects.create(workspace=cls.ws_retail, branch=cls.branch_q1, product=cls.prod_asus, quantity_on_hand=4)
        StockBalance.objects.create(workspace=cls.ws_retail, branch=cls.branch_q3, product=cls.prod_lenovo, quantity_on_hand=15)

        # 4. Setup Service Catalog & Service Requests
        cls.service_cust = Customer.objects.create(workspace=cls.ws_service, code="CUST-SVC-01", name="Công ty Công Nghệ VIP", phone="0988776655")
        cls.svc_install = Service.objects.create(
            workspace=cls.ws_service, code="INST-OS", name="Cài đặt hệ điều hành Server",
            category=ServiceCategory.INSTALLATION, standard_duration_minutes=90, base_fee=Decimal("350000.00"), is_active=True
        )
        cls.tech = Employee.objects.create(
            workspace=cls.ws_service, code="EMP-01", full_name="Nguyễn Văn Kỹ Thuật",
            hourly_labor_rate=Decimal("150000.00"), is_available=True, current_workload_score=45.0
        )
        cls.ticket = ServiceRequest.objects.create(
            workspace=cls.ws_service, request_number="SR-BM-100", title="Cài đặt server cho phòng kế toán",
            customer=cls.service_cust, service=cls.svc_install, assigned_employee=cls.tech, status=ServiceRequestStatus.IN_PROGRESS,
            priority=ServiceRequestPriority.HIGH, resolution_deadline_at=timezone.now() + timedelta(hours=2)
        )
        cls.task = Task.objects.create(
            service_request=cls.ticket, assigned_to=cls.tech, title="Triển khai Ubuntu Server",
            status=TaskStatus.IN_PROGRESS, priority=ServiceRequestPriority.HIGH
        )
        LaborEntry.objects.create(
            task=cls.task, employee=cls.tech,
            started_at=timezone.now() - timedelta(hours=3), ended_at=timezone.now() - timedelta(minutes=30),
            duration_minutes=150, hourly_rate_snapshot=Decimal("150000.00"), labor_cost=Decimal("375000.00")
        )


    def _route_retail(self, query: str, context=None):

        return classify_business_intent(query, self.ws_retail, conversation_context=context)

    def _route_service(self, query: str, context=None):
        return classify_business_intent(query, self.ws_service, conversation_context=context)

    # =========================================================================
    # 1. RETAIL PRODUCT & CATALOG CONTEXT (Q1 - Q5)
    # =========================================================================
    def test_q01_catalog_count_laptop(self):
        """Q1: 'Có bao nhiêu laptop đang kinh doanh?' -> CATALOG_COUNT, category='laptop'"""
        r = self._route_retail("Có bao nhiêu laptop đang kinh doanh?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertIn("get_product_catalog_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q02_catalog_list_phone(self):
        """Q2: 'Danh sách các mẫu điện thoại hiện có?' -> CATALOG_COUNT, category='smartphone'"""
        r = self._route_retail("Danh sách các mẫu điện thoại hiện có?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertIn("get_product_catalog_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "smartphone")

    def test_q03_catalog_components_total(self):
        """Q3: 'Tổng số mặt hàng linh kiện trong hệ thống?' -> CATALOG_COUNT, category='components'"""
        r = self._route_retail("Tổng số mặt hàng linh kiện trong hệ thống?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertEqual(r["parameters"]["category"], "components")

    def test_q04_catalog_networking_models(self):
        """Q4: 'Các model thiết bị mạng hiện có?' -> CATALOG_COUNT, category='networking'"""
        r = self._route_retail("Các model thiết bị mạng hiện có?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertEqual(r["parameters"]["category"], "networking")

    def test_q05_catalog_active_only_filter(self):
        """Q5: 'Bỏ qua sản phẩm ngừng kinh doanh, hiện có bao nhiêu bàn phím?' -> active_only=True"""
        r = self._route_retail("Bỏ qua sản phẩm ngừng kinh doanh, hiện có bao nhiêu bàn phím?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertEqual(r["parameters"]["category"], "keyboard")

    # =========================================================================
    # 2. RETAIL SALES & REVENUE RANKING (Q6 - Q11)
    # =========================================================================
    def test_q06_top_selling_laptop_this_month(self):
        """Q6: 'Laptop nào bán chạy nhất tháng này?' -> TOP_SELLING_PRODUCTS, limit=1, time='tháng này'"""
        r = self._route_retail("Laptop nào bán chạy nhất tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertEqual(r["parameters"]["metric"], "quantity_sold")
        self.assertEqual(r["parameters"]["limit"], 1)
        self.assertEqual(r["parameters"]["time_label"], "tháng này")

    def test_q07_top_3_revenue_models_this_year(self):
        """Q7: 'Top 3 mẫu máy có doanh thu cao nhất năm nay?' -> TOP_REVENUE_PRODUCTS, metric='revenue', limit=3"""
        r = self._route_retail("Top 3 mẫu máy có doanh thu cao nhất năm nay?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertEqual(r["parameters"]["metric"], "revenue")
        self.assertEqual(r["parameters"]["limit"], 3)
        self.assertEqual(r["parameters"]["time_label"], "năm nay")

    def test_q08_top_selling_past_7_days(self):
        """Q8: 'Sản phẩm nào bán được nhiều nhất trong 7 ngày qua?' -> TOP_SELLING_PRODUCTS, limit=1"""
        r = self._route_retail("Sản phẩm nào bán được nhiều nhất trong 7 ngày qua?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"]["limit"], 1)
        self.assertIn("7 ngày", r["parameters"]["time_label"])

    def test_q09_slowest_selling_mouse(self):
        """Q9: 'Mặt hàng chuột nào ế ẩm nhất?' -> sort_order='ASC', category='mouse'"""
        r = self._route_retail("Mặt hàng chuột nào ế ẩm nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"]["sort_order"], "ASC")
        self.assertEqual(r["parameters"]["category"], "mouse")

    def test_q10_top_5_revenue_this_quarter(self):
        """Q10: 'Top 5 sản phẩm mang lại doanh số cao nhất quý này?' -> TOP_REVENUE_PRODUCTS, limit=5"""
        r = self._route_retail("Top 5 sản phẩm mang lại doanh số cao nhất quý này?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)
        self.assertEqual(r["parameters"]["limit"], 5)
        self.assertEqual(r["parameters"]["time_label"], "quý này")

    def test_q11_laptop_dung_dau_luong_ban(self):
        """Q11: 'Laptop nào đứng đầu về lượng bán?' -> TOP_SELLING_PRODUCTS, limit=1"""
        r = self._route_retail("Laptop nào đứng đầu về lượng bán?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"]["limit"], 1)
        self.assertEqual(r["parameters"]["category"], "laptop")

    # =========================================================================
    # 3. RETAIL CUSTOMER ANALYTICS (Q12 - Q15)
    # =========================================================================
    def test_q12_top_customer_year(self):
        """Q12: 'Khách hàng nào mua nhiều nhất năm nay?' -> TOP_CUSTOMERS, limit=1"""
        r = self._route_retail("Khách hàng nào mua nhiều nhất năm nay?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertIn("get_top_customers", r["tools"])
        self.assertEqual(r["parameters"]["limit"], 1)

    def test_q13_top_3_vip_customers(self):
        """Q13: 'Top 3 khách VIP có doanh thu cao nhất?' -> TOP_CUSTOMERS, limit=3"""
        r = self._route_retail("Top 3 khách VIP có doanh thu cao nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertEqual(r["parameters"]["limit"], 3)

    def test_q14_customer_highest_spend_this_month(self):
        """Q14: 'Khách hàng nào chi tiêu nhiều nhất tháng này?' -> TOP_CUSTOMERS, time='tháng này'"""
        r = self._route_retail("Khách hàng nào chi tiêu nhiều nhất tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertEqual(r["parameters"]["time_label"], "tháng này")

    def test_q15_customer_count_segments(self):
        """Q15: 'Hiện có bao nhiêu khách hàng theo phân khúc?' -> CUSTOMER_SUMMARY"""
        r = self._route_retail("Hiện có bao nhiêu khách hàng theo phân khúc?")
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_SUMMARY)
        self.assertIn("get_customer_summary", r["tools"])

    # =========================================================================
    # 4. RETAIL BRANCH ANALYTICS & RANKINGS (Q16 - Q20)
    # =========================================================================
    def test_q16_branch_highest_revenue_this_month(self):
        """Q16: 'Chi nhánh nào có doanh thu cao nhất tháng này?' -> BRANCH_REVENUE, sort='DESC'"""
        r = self._route_retail("Chi nhánh nào có doanh thu cao nhất tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertIn("get_branch_sales_analytics", r["tools"])
        self.assertEqual(r["parameters"]["sort_order"], "DESC")
        self.assertEqual(r["parameters"]["time_label"], "tháng này")

    def test_q17_branch_lowest_revenue(self):
        """Q17: 'Cửa hàng nào có doanh thu thấp nhất?' -> BRANCH_REVENUE, sort='ASC'"""
        r = self._route_retail("Cửa hàng nào có doanh thu thấp nhất?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"]["sort_order"], "ASC")

    def test_q18_top_3_branches(self):
        """Q18: 'Top 3 chi nhánh bán chạy nhất quý này?' -> BRANCH_REVENUE"""
        r = self._route_retail("Top 3 chi nhánh bán chạy nhất quý này?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"]["time_label"], "quý này")

    def test_q19_branch_selling_most_laptops(self):
        """Q19: 'Chi nhánh nào bán được nhiều laptop nhất?' -> BRANCH_REVENUE, category='laptop'"""
        r = self._route_retail("Chi nhánh nào bán được nhiều laptop nhất?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q20_branch_lowest_sales_last_week(self):
        """Q20: 'Cơ sở nào doanh thu thấp nhất tuần trước?' -> BRANCH_REVENUE, sort='ASC', time='tuần trước'"""
        r = self._route_retail("Cơ sở nào doanh thu thấp nhất tuần trước?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"]["sort_order"], "ASC")
        self.assertEqual(r["parameters"]["time_label"], "tuần trước")

    # =========================================================================
    # 5. RETAIL TREND & PERIOD COMPARISON (Q21 - Q25)
    # =========================================================================
    def test_q21_sales_trend_laptop(self):
        """Q21: 'Doanh thu laptop đang tăng hay giảm?' -> SALES_TREND, tool='get_sales_trend_analytics'"""
        r = self._route_retail("Doanh thu laptop đang tăng hay giảm?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertIn("get_sales_trend_analytics", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q22_sales_trend_month_over_month(self):
        """Q22: 'Doanh thu tháng này so với tháng trước thế nào?' -> SALES_TREND"""
        r = self._route_retail("Doanh thu tháng này so với tháng trước thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertIn("get_sales_trend_analytics", r["tools"])

    def test_q23_sales_trend_fastest_growing(self):
        """Q23: 'Sản phẩm nào đang tăng doanh số mạnh nhất?' -> SALES_TREND"""
        r = self._route_retail("Sản phẩm nào đang tăng doanh số mạnh nhất?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)

    def test_q24_sales_trend_components_week(self):
        """Q24: 'Diễn biến xu hướng bán hàng linh kiện tuần này?' -> SALES_TREND, category='components'"""
        r = self._route_retail("Diễn biến xu hướng bán hàng linh kiện tuần này?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertEqual(r["parameters"]["category"], "components")

    def test_q25_sales_trend_growth_or_drop(self):
        """Q25: 'Doanh số đang tăng trưởng hay sụt giảm?' -> SALES_TREND"""
        r = self._route_retail("Doanh số đang tăng trưởng hay sụt giảm?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)

    # =========================================================================
    # 6. RETAIL ENTITY COMPARISON (Q26 - Q30)
    # =========================================================================
    def test_q26_compare_asus_vs_lenovo(self):
        """Q26: 'ASUS hay Lenovo bán tốt hơn?' -> COMPARISON, entities=['ASUS', 'LENOVO']"""
        r = self._route_retail("ASUS hay Lenovo bán tốt hơn?")
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertIn("compare_entities_analytics", r["tools"])
        self.assertEqual(r["parameters"]["entity_type"], "product")
        self.assertIn("ASUS", r["parameters"]["entities"])
        self.assertIn("LENOVO", r["parameters"]["entities"])

    def test_q27_compare_branches_q1_vs_q3(self):
        """Q27: 'Chi nhánh Quận 1 so với Chi nhánh Quận 3 thế nào?' -> COMPARISON, entity_type='branch'"""
        r = self._route_retail("Chi nhánh Quận 1 so với Chi nhánh Quận 3 thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertIn("compare_entities_analytics", r["tools"])
        self.assertEqual(r["parameters"]["entity_type"], "branch")

    def test_q28_compare_mouse_vs_keyboard(self):
        """Q28: 'Chuột và bàn phím cái nào bán chạy hơn?' -> COMPARISON"""
        r = self._route_retail("Chuột và bàn phím cái nào bán chạy hơn?")
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertIn("compare_entities_analytics", r["tools"])

    def test_q29_compare_vivobook_vs_ideapad_revenue(self):
        """Q29: 'Doanh thu VivoBook và IdeaPad cái nào cao hơn?' -> COMPARISON, metric='revenue'"""
        r = self._route_retail("Doanh thu VivoBook và IdeaPad cái nào cao hơn?")
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"]["metric"], "revenue")

    def test_q30_compare_stores_generic(self):
        """Q30: 'So sánh cửa hàng A và B về lượng đơn hàng' -> COMPARISON, entity_type='branch'"""
        r = self._route_retail("So sánh cửa hàng A và B về lượng đơn hàng")
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"]["entity_type"], "branch")

    # =========================================================================
    # 7. RETAIL STOCKOUT RISK & STOCK BALANCES (Q31 - Q36)
    # =========================================================================
    def test_q31_stockout_risk_7_days(self):
        """Q31: 'Sản phẩm nào có nguy cơ hết hàng trong 7 ngày tới?' -> STOCKOUT_RISK"""
        r = self._route_retail("Sản phẩm nào có nguy cơ hết hàng trong 7 ngày tới?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])

    def test_q32_stockout_risk_laptop(self):
        """Q32: 'Laptop nào sắp hết hàng?' -> STOCKOUT_RISK, category='laptop'"""
        r = self._route_retail("Laptop nào sắp hết hàng?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q33_stockout_reorder_recommendation(self):
        """Q33: 'Sản phẩm nào nên nhập sớm?' -> STOCKOUT_RISK"""
        r = self._route_retail("Sản phẩm nào nên nhập sớm?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)

    def test_q34_stock_balance_laptop(self):
        """Q34: 'Tồn kho laptop hiện tại thế nào?' -> STOCK_BALANCE, category='laptop'"""
        r = self._route_retail("Tồn kho laptop hiện tại thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertIn("get_stock_balance_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q35_stock_balance_branches(self):
        """Q35: 'Kiểm tra số lượng tồn kho của các chi nhánh' -> STOCK_BALANCE"""
        r = self._route_retail("Kiểm tra số lượng tồn kho của các chi nhánh")
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)

    def test_q36_stock_balance_least_in_stock(self):
        """Q36: 'Laptop nào còn ít hàng nhất trong kho?' -> STOCK_BALANCE, category='laptop'"""
        r = self._route_retail("Laptop nào còn ít hàng nhất trong kho?")
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertEqual(r["parameters"]["category"], "laptop")

    # =========================================================================
    # 8. SERVICE OPERATIONS TICKETS & SLA (Q37 - Q42)
    # =========================================================================
    def test_q37_service_tickets_open_count(self):
        """Q37: 'Có bao nhiêu ticket đang xử lý?' -> SERVICE_TICKETS_SUMMARY"""
        r = self._route_service("Có bao nhiêu ticket đang xử lý?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_TICKETS_SUMMARY)
        self.assertIn("get_service_ticket_summary", r["tools"])

    def test_q38_service_sla_at_risk(self):
        """Q38: 'Ticket nào sắp trễ SLA?' -> SERVICE_SLA_AT_RISK, filter='SLA_AT_RISK'"""
        r = self._route_service("Ticket nào sắp trễ SLA?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)
        self.assertEqual(r["parameters"]["filter"], "SLA_AT_RISK")

    def test_q39_service_sla_breached(self):
        """Q39: 'Ticket nào đã quá hạn SLA?' -> SERVICE_SLA_AT_RISK, filter='SLA_BREACHED'"""
        r = self._route_service("Ticket nào đã quá hạn SLA?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)
        self.assertEqual(r["parameters"]["filter"], "SLA_BREACHED")

    def test_q40_service_sla_within_1_hour(self):
        """Q40: 'Ticket nào còn 1 giờ nữa là vi phạm SLA?' -> SERVICE_SLA_AT_RISK"""
        r = self._route_service("Ticket nào còn 1 giờ nữa là vi phạm SLA?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)

    def test_q41_ticket_single_lookup(self):
        """Q41: 'Ticket 5 đang ở trạng thái gì?' -> TICKET_LOOKUP, ticket_id=5"""
        r = self._route_service("Ticket 5 đang ở trạng thái gì?")
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"]["ticket_id"], 5)

    def test_q42_ticket_lookup_assigned(self):
        """Q42: 'Phiếu yêu cầu #12 ai đang phụ trách?' -> TICKET_LOOKUP, ticket_id=12"""
        r = self._route_service("Phiếu yêu cầu #12 ai đang phụ trách?")
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"]["ticket_id"], 12)

    # =========================================================================
    # 9. TECHNICIAN WORKLOAD, GIS & RECOMMENDATION (Q43 - Q47)
    # =========================================================================
    def test_q43_technician_nearby_gis(self):
        """Q43: 'Kỹ thuật viên nào gần ticket 5 nhất?' -> TECHNICIAN_NEARBY_GIS, tool='query_nearby_technicians'"""
        r = self._route_service("Kỹ thuật viên nào gần ticket 5 nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)
        self.assertIn("query_nearby_technicians", r["tools"])
        self.assertEqual(r["parameters"]["ticket_id"], 5)

    def test_q44_technician_nearby_radius(self):
        """Q44: 'Ai ở gần khách hàng này nhất trong bán kính 10km?' -> TECHNICIAN_NEARBY_GIS"""
        r = self._route_service("Ai ở gần khách hàng này nhất trong bán kính 10km?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)
        self.assertIn("query_nearby_technicians", r["tools"])

    def test_q45_technician_overloaded(self):
        """Q45: 'Kỹ thuật viên nào đang quá tải?' -> TECHNICIAN_WORKLOAD, sort='DESC'"""
        r = self._route_service("Kỹ thuật viên nào đang quá tải?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_WORKLOAD)
        self.assertIn("get_technician_workload_summary", r["tools"])
        self.assertEqual(r["parameters"]["sort_order"], "DESC")

    def test_q46_technician_available_least_loaded(self):
        """Q46: 'Ai đang rảnh nhất để nhận việc?' -> TECHNICIAN_WORKLOAD, sort='ASC'"""
        r = self._route_service("Ai đang rảnh nhất để nhận việc?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_WORKLOAD)
        self.assertEqual(r["parameters"]["sort_order"], "ASC")

    def test_q47_technician_recommendation_best_fit(self):
        """Q47: 'Kỹ thuật viên nào phù hợp nhất để xử lý ticket 5?' -> TECHNICIAN_RECOMMENDATION"""
        r = self._route_service("Kỹ thuật viên nào phù hợp nhất để xử lý ticket 5?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_RECOMMENDATION)
        self.assertEqual(r["parameters"]["ticket_id"], 5)

    # =========================================================================
    # 10. SERVICE LABOR COST & HOURS (Q48 - Q51)
    # =========================================================================
    def test_q48_labor_cost_ticket(self):
        """Q48: 'Ticket này tốn bao nhiêu tiền công?' -> SERVICE_LABOR_COST, tool='get_service_labor_cost_summary'"""
        r = self._route_service("Ticket này tốn bao nhiêu tiền công?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)
        self.assertIn("get_service_labor_cost_summary", r["tools"])

    def test_q49_labor_hours_this_month(self):
        """Q49: 'Kỹ thuật viên đã làm bao nhiêu giờ công tháng này?' -> SERVICE_LABOR_COST"""
        r = self._route_service("Kỹ thuật viên đã làm bao nhiêu giờ công tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)
        self.assertEqual(r["parameters"]["time_label"], "tháng này")

    def test_q50_total_labor_cost_month(self):
        """Q50: 'Chi phí nhân công tháng này là bao nhiêu?' -> SERVICE_LABOR_COST"""
        r = self._route_service("Chi phí nhân công tháng này là bao nhiêu?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)

    def test_q51_labor_cost_past_30_days(self):
        """Q51: 'Tổng công kỹ thuật đã chi trả trong 30 ngày qua?' -> SERVICE_LABOR_COST"""
        r = self._route_service("Tổng công kỹ thuật đã chi trả trong 30 ngày qua?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)

    # =========================================================================
    # 11. SERVICE CATALOG QUERIES (Q52 - Q53)
    # =========================================================================
    def test_q52_service_catalog_pricing(self):
        """Q52: 'Bảng giá các gói dịch vụ IT hiện có?' -> SERVICE_CATALOG, tool='get_service_catalog_summary'"""
        r = self._route_service("Bảng giá các gói dịch vụ IT hiện có?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_CATALOG)
        self.assertIn("get_service_catalog_summary", r["tools"])

    def test_q53_service_catalog_maintenance(self):
        """Q53: 'Có những loại dịch vụ bảo trì nào?' -> SERVICE_CATALOG"""
        r = self._route_service("Có những loại dịch vụ bảo trì nào?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_CATALOG)

    # =========================================================================
    # 12. FORECASTING & TIME-SERIES PROJECTIONS (Q54 - Q57)
    # =========================================================================
    def test_q54_forecast_revenue_14_days(self):
        """Q54: 'Dự báo doanh thu 14 ngày tới?' -> FORECAST_METRICS, target='RETAIL_REVENUE'"""
        r = self._route_retail("Dự báo doanh thu 14 ngày tới?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"]["target_type"], "RETAIL_REVENUE")

    def test_q55_forecast_order_volume(self):
        """Q55: 'Số lượng đơn hàng dự kiến trong 14 ngày tới?' -> FORECAST_METRICS, target='RETAIL_ORDER_VOLUME'"""
        r = self._route_retail("Số lượng đơn hàng dự kiến trong 14 ngày tới?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"]["target_type"], "RETAIL_ORDER_VOLUME")

    def test_q56_forecast_service_tickets(self):
        """Q56: 'Tuần tới có khoảng bao nhiêu ticket sự cố?' -> FORECAST_METRICS, target='SERVICE_TICKET_VOLUME'"""
        r = self._route_service("Tuần tới có khoảng bao nhiêu ticket sự cố?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"]["target_type"], "SERVICE_TICKET_VOLUME")

    def test_q57_forecast_future_sales(self):
        """Q57: 'Ước tính doanh số thời gian tới thế nào?' -> FORECAST_METRICS"""
        r = self._route_retail("Ước tính doanh số thời gian tới thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)

    # =========================================================================
    # 13. POLICY / SOP DOCUMENT RAG (Q58 - Q60)
    # =========================================================================
    def test_q58_rag_warranty_policy(self):
        """Q58: 'Chính sách bảo hành laptop là gì?' -> DOCUMENT_RAG"""
        r = self._route_retail("Chính sách bảo hành laptop là gì?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)
        self.assertEqual(len(r["tools"]), 0)

    def test_q59_rag_return_policy(self):
        """Q59: 'Quy định đổi trả hàng trong bao nhiêu ngày?' -> DOCUMENT_RAG"""
        r = self._route_retail("Quy định đổi trả hàng trong bao nhiêu ngày?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    def test_q60_rag_server_maintenance_sop(self):
        """Q60: 'Quy trình xử lý sự cố server theo SOP?' -> DOCUMENT_RAG"""
        r = self._route_service("Quy trình xử lý sự cố server theo SOP?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    # =========================================================================
    # 14. HYBRID DATA + POLICY QUERIES (Q61 - Q63)
    # =========================================================================
    def test_q61_hybrid_top_selling_warranty(self):
        """Q61: 'Laptop bán chạy nhất có được bảo hành 24 tháng không?' -> TOP_SELLING_PRODUCTS + RAG execution"""
        r = self._route_retail("Laptop bán chạy nhất có được bảo hành 24 tháng không?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])

    def test_q62_hybrid_top_revenue_return_policy(self):
        """Q62: 'Sản phẩm doanh thu cao nhất áp dụng quy định đổi trả thế nào?' -> TOP_REVENUE_PRODUCTS"""
        r = self._route_retail("Sản phẩm doanh thu cao nhất áp dụng quy định đổi trả thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)

    def test_q63_hybrid_ticket_sla_sop(self):
        """Q63: 'Ticket 5 sắp trễ SLA thì quy trình xử lý theo SOP là gì?' -> TICKET_LOOKUP"""
        r = self._route_service("Ticket 5 sắp trễ SLA thì quy trình xử lý theo SOP là gì?")
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"]["ticket_id"], 5)

    # =========================================================================
    # 15. CONVERSATIONAL FOLLOW-UPS & CONTEXT RESOLUTION (Q64 - Q67)
    # =========================================================================
    def test_q64_follow_up_con_asus_thi_sao(self):
        """Q64: Turn 1: 'Laptop nào bán chạy nhất?' -> Turn 2: 'Còn ASUS thì sao?'"""
        context = [{"intent": BusinessIntent.TOP_SELLING_PRODUCTS, "parameters": {"category": "laptop", "metric": "quantity_sold"}}]
        r = self._route_retail("Còn ASUS thì sao?", context=context)
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q65_follow_up_thang_truoc_thi_the_nao(self):
        """Q65: Turn 1: 'Doanh thu tháng này?' -> Turn 2: 'Tháng trước thì thế nào?'"""
        context = [{"intent": BusinessIntent.SALES_SUMMARY, "parameters": {"category": "laptop"}}]
        r = self._route_retail("Tháng trước thì thế nào?", context=context)
        self.assertEqual(r["parameters"]["time_label"], "tháng trước")

    def test_q66_follow_up_cai_do_con_hang_khong(self):
        """Q66: Turn 1: 'Laptop ASUS VivoBook 14 bán chạy không?' -> Turn 2: 'Cái đó còn hàng không?'"""
        context = [{"intent": BusinessIntent.TOP_SELLING_PRODUCTS, "parameters": {"category": "laptop"}}]
        r = self._route_retail("Cái đó còn hàng không?", context=context)
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_q67_follow_up_vay_ai_xu_ly_duoc(self):
        """Q67: Turn 1: 'Ticket 5 bị sự cố gì?' -> Turn 2: 'Vậy ai xử lý được?'"""
        context = [{"intent": BusinessIntent.TICKET_LOOKUP, "parameters": {"ticket_id": 5}}]
        r = self._route_service("Vậy ai xử lý được?", context=context)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_RECOMMENDATION)
        self.assertEqual(r["parameters"]["ticket_id"], 5)

    # =========================================================================
    # 16. AMBIGUITY & CLARIFICATION QUESTIONS (Q68 - Q70)
    # =========================================================================
    def test_q68_ambiguous_laptop_tot_nhat(self):
        """Q68: 'Laptop nào tốt nhất?' -> AMBIGUOUS, clarification question returned"""
        r = self._route_retail("Laptop nào tốt nhất?")
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)
        self.assertIn("clarification_question", r)
        self.assertEqual(len(r["tools"]), 0)

    def test_q69_ambiguous_chi_nhanh_ok_nhat(self):
        """Q69: 'Chi nhánh nào ok nhất?' -> AMBIGUOUS"""
        r = self._route_retail("Chi nhánh nào ok nhất?")
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)

    def test_q70_ambiguous_san_pham_dinh_nhat(self):
        """Q70: 'Sản phẩm nào đỉnh nhất?' -> AMBIGUOUS"""
        r = self._route_retail("Sản phẩm nào đỉnh nhất?")
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)

    # =========================================================================
    # 17. NEGATION & EXCLUSION CONSTRAINTS (Q71 - Q73)
    # =========================================================================
    def test_q71_exclusion_khong_tinh_don_da_huy(self):
        """Q71: 'Không tính đơn đã hủy, doanh thu tháng này là bao nhiêu?' -> exclude_cancelled=True"""
        r = self._route_retail("Không tính đơn đã hủy, doanh thu tháng này là bao nhiêu?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)
        self.assertTrue(r["parameters"]["exclude_cancelled"])

    def test_q72_exclusion_bo_qua_san_pham_ngung_kinh_doanh(self):
        """Q72: 'Bỏ qua sản phẩm ngừng kinh doanh, laptop nào bán chạy nhất?' -> active_only=True"""
        r = self._route_retail("Bỏ qua sản phẩm ngừng kinh doanh, laptop nào bán chạy nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertTrue(r["parameters"]["active_only"])

    def test_q73_exclusion_khong_tinh_ticket_da_dong(self):
        """Q73: 'Không tính ticket đã đóng, có bao nhiêu phiếu sự cố?' -> exclude_closed=True"""
        r = self._route_service("Không tính ticket đã đóng, có bao nhiêu phiếu sự cố?")
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_TICKETS_SUMMARY)
        self.assertTrue(r["parameters"]["exclude_closed"])

    # =========================================================================
    # 18. CONTROLLED MUTATION ACTIONS (Q74 - Q77)
    # =========================================================================
    def test_q74_mutation_adjust_price(self):
        """Q74: 'Đổi giá sản phẩm 5 thành 15000000 VND.' -> MUTATION_ACTION"""
        r = self._route_retail("Đổi giá sản phẩm 5 thành 15000000 VND.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_q75_mutation_dispatch_technician(self):
        """Q75: 'Phân công kỹ thuật viên 2 cho ticket 10.' -> MUTATION_ACTION"""
        r = self._route_service("Phân công kỹ thuật viên 2 cho ticket 10.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_q76_mutation_update_order_status(self):
        """Q76: 'Cập nhật trạng thái đơn hàng 8 thành COMPLETED.' -> MUTATION_ACTION"""
        r = self._route_retail("Cập nhật trạng thái đơn hàng 8 thành COMPLETED.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_q77_mutation_schedule_task(self):
        """Q77: 'Lập lịch nhiệm vụ bảo trì cho kỹ thuật viên 3.' -> MUTATION_ACTION"""
        r = self._route_service("Lập lịch nhiệm vụ bảo trì cho kỹ thuật viên 3.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)
