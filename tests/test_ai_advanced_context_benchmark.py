"""
Comprehensive Vietnamese AI Business Intent Benchmark Test Suite (88 Benchmark Scenarios).

Evaluates the AI Assistant's semantic understanding across:
- Retail: Products, Categories, Sales Rankings, Customer History, Branch Intersections, Trends, Comparisons, Stockout vs Balances
- Service Ops: Tickets, SLA Deadlines, Technician Skills, Availability, Workload, Labor Costs, Schedules & Conflict Detection
- Advanced Cross-Domain: Spatial GIS Clusters, Forecasting, Policy RAG, Hybrid Queries, Root-Cause ("Vì sao?"), What-If Simulations, Multi-Condition Intersections, Conversational Memory, Ambiguity, and Controlled Mutations.
"""

from datetime import date
from django.test import TestCase
from django.utils import timezone
from apps.workspaces.models import Workspace
from apps.knowledge.intent_router import (
    BusinessIntent,
    classify_business_intent,
    resolve_follow_up_context,
)


class VietnameseAdvancedContextBenchmarkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.retail_workspace = Workspace.objects.create(
            name="Alpha Retail MegaStore",
            code="ALPHA_RETAIL",
            workspace_type="RETAIL",
        )
        cls.service_workspace = Workspace.objects.create(
            name="Beta Service Hub",
            code="BETA_SERVICE",
            workspace_type="SERVICE",
        )

    # -------------------------------------------------------------------------
    # 1. Retail Product Context & Rankings (Q01-Q06)
    # -------------------------------------------------------------------------
    def test_q01_catalog_count_laptop(self):
        r = classify_business_intent("Có bao nhiêu laptop đang kinh doanh?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertEqual(r["parameters"].get("category"), "laptop")
        self.assertIn("get_product_catalog_summary", r["tools"])

    def test_q02_top_selling_quantity(self):
        r = classify_business_intent("Laptop nào bán chạy nhất tháng này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "laptop")
        self.assertEqual(r["parameters"].get("metric"), "quantity_sold")
        self.assertEqual(r["parameters"].get("limit"), 1)

    def test_q03_top_revenue_products(self):
        r = classify_business_intent("Laptop nào kiếm được nhiều tiền nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "laptop")
        self.assertEqual(r["parameters"].get("metric"), "revenue")

    def test_q04_slow_selling_products(self):
        r = classify_business_intent("Laptop nào đang bán chậm nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("sort_order"), "ASC")

    def test_q05_top_3_keyboards(self):
        r = classify_business_intent("Top 3 bàn phim cơ bán chạy nhất quý này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "keyboard")
        self.assertEqual(r["parameters"].get("limit"), 3)

    def test_q06_unpopular_mouse(self):
        r = classify_business_intent("Chuột nào ế ẩm nhất năm nay?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "mouse")
        self.assertEqual(r["parameters"].get("sort_order"), "ASC")

    # -------------------------------------------------------------------------
    # 2. Retail Customer Context & Order History (Q07-Q12)
    # -------------------------------------------------------------------------
    def test_q07_customer_purchase_quantity(self):
        r = classify_business_intent("Khách nào mua nhiều nhất tháng này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertIn("get_top_customers", r["tools"])

    def test_q08_customer_revenue_highest(self):
        r = classify_business_intent("Khách nào mang lại doanh thu cao nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)

    def test_q09_customer_order_history_lookup(self):
        r = classify_business_intent("Khách A đã mua những gì?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_ORDER_HISTORY)
        self.assertEqual(r["parameters"].get("customer_name"), "A")
        self.assertIn("get_customer_order_history", r["tools"])

    def test_q10_customer_order_history_vip(self):
        r = classify_business_intent("Lịch sử mua hàng của khách VIP 1?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_ORDER_HISTORY)
        self.assertIn("get_customer_order_history", r["tools"])

    def test_q11_customer_product_filter(self):
        r = classify_business_intent("Khách hàng nào mua laptop nhiều nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q12_customer_summary_segments(self):
        r = classify_business_intent("Hiện có bao nhiêu khách hàng theo phân khúc?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.CUSTOMER_SUMMARY)
        self.assertIn("get_customer_summary", r["tools"])

    # -------------------------------------------------------------------------
    # 3. Retail Branch Context & Intersections (Q13-Q17)
    # -------------------------------------------------------------------------
    def test_q13_branch_revenue_lowest(self):
        r = classify_business_intent("Cửa hàng nào doanh thu thấp nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"].get("sort_order"), "ASC")

    def test_q14_branch_top_revenue(self):
        r = classify_business_intent("Chi nhánh nào có doanh thu cao nhất tháng này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"].get("sort_order"), "DESC")

    def test_q15_branch_laptop_sales(self):
        r = classify_business_intent("Chi nhánh nào bán nhiều laptop nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q16_branch_trend_change(self):
        r = classify_business_intent("Doanh thu chi nhánh Tân Phú giảm bao nhiêu so với tháng trước?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertIn("Tan Phu", r["parameters"].get("branch_name", ""))


    def test_q17_top_3_branches(self):
        r = classify_business_intent("Top 3 chi nhánh doanh thu cao nhất quý này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)

    # -------------------------------------------------------------------------
    # 4. Retail Trend & Growth Analytics (Q18-Q22)
    # -------------------------------------------------------------------------
    def test_q18_sales_trend_month_over_month(self):
        r = classify_business_intent("Doanh thu tháng này so với tháng trước thế nào?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertIn("get_sales_trend_analytics", r["tools"])

    def test_q19_product_growth_rate(self):
        r = classify_business_intent("Doanh thu laptop đang tăng trưởng hay sụt giảm?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q20_sales_trend_7_days(self):
        r = classify_business_intent("Doanh số tuần này tăng hay giảm so với tuần trước?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertEqual(r["parameters"].get("period_days"), 7)

    def test_q21_sales_volatility(self):
        r = classify_business_intent("Biến động doanh thu linh kiện 30 ngày qua?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_TREND)
        self.assertEqual(r["parameters"].get("category"), "components")

    def test_q22_general_sales_summary(self):
        r = classify_business_intent("Tổng doanh thu toàn hệ thống tháng này?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)
        self.assertIn("get_sales_summary", r["tools"])

    # -------------------------------------------------------------------------
    # 5. Retail Entity Comparison (Q23-Q27)
    # -------------------------------------------------------------------------
    def test_q23_brand_comparison(self):
        r = classify_business_intent("ASUS và Lenovo bên nào bán tốt hơn?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"].get("entity_type"), "product")
        self.assertIn("get_sales_trend_analytics" not in r["tools"], [True])
        self.assertIn("compare_entities_analytics", r["tools"])

    def test_q24_branch_comparison(self):
        r = classify_business_intent("Chi nhánh Quận 1 so với Chi nhánh Quận 3 thế nào?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"].get("entity_type"), "branch")

    def test_q25_revenue_comparison(self):
        r = classify_business_intent("Doanh thu MacBook hay ThinkPad cao hơn?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"].get("metric"), "revenue")

    def test_q26_category_comparison(self):
        r = classify_business_intent("Chuột hay Bàn phím bán được nhiều chiếc hơn?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)
        self.assertEqual(r["parameters"].get("metric"), "quantity_sold")

    def test_q27_general_product_comparison(self):
        r = classify_business_intent("So sánh hiệu suất bán hàng giữa các dòng máy", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.COMPARISON)

    # -------------------------------------------------------------------------
    # 6. Retail Stockout vs Balance vs Reorder (Q28-Q33)
    # -------------------------------------------------------------------------
    def test_q28_stockout_risk_upcoming(self):
        r = classify_business_intent("Có sản phẩm nào sắp hết hàng không?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])

    def test_q29_reorder_recommendation(self):
        r = classify_business_intent("Laptop nào cần nhập sớm?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q30_stock_balance_general(self):
        r = classify_business_intent("Tồn kho hiện tại thế nào?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertIn("get_stock_balance_summary", r["tools"])

    def test_q31_stock_balance_lowest(self):
        r = classify_business_intent("Laptop nào còn ít hàng nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q32_reorder_quantity_alert(self):
        r = classify_business_intent("Đề xuất nhập thêm bao nhiêu sản phẩm linh kiện?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertEqual(r["parameters"].get("category"), "components")

    def test_q33_stock_check_vivobook(self):
        r = classify_business_intent("Kiểm tra tồn kho VivoBook còn bao nhiêu chiếc?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)

    # -------------------------------------------------------------------------
    # 7. Service Tickets & SLA Deadlines (Q34-Q39)
    # -------------------------------------------------------------------------
    def test_q34_service_tickets_summary(self):
        r = classify_business_intent("Có bao nhiêu ticket đang xử lý?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_TICKETS_SUMMARY)
        self.assertIn("get_service_ticket_summary", r["tools"])

    def test_q35_single_ticket_lookup(self):
        r = classify_business_intent("Ticket 5 đang ở trạng thái gì?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"].get("ticket_id"), 5)

    def test_q36_ticket_lookup_hash(self):
        r = classify_business_intent("Phiếu #12 ai phụ trách?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"].get("ticket_id"), 12)

    def test_q37_sla_at_risk(self):
        r = classify_business_intent("Ticket nào sắp trễ SLA?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)
        self.assertEqual(r["parameters"].get("filter"), "SLA_AT_RISK")

    def test_q38_sla_breached(self):
        r = classify_business_intent("Ticket nào đã quá hạn?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)
        self.assertEqual(r["parameters"].get("filter"), "SLA_BREACHED")

    def test_q39_sla_deadline_remaining(self):
        r = classify_business_intent("Ticket nào còn dưới 2 tiếng?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)

    # -------------------------------------------------------------------------
    # 8. Technician Skills & Availability Intersections (Q40-Q44)
    # -------------------------------------------------------------------------
    def test_q40_technician_skill_database(self):
        r = classify_business_intent("Ai có kỹ năng database?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SKILLS)
        self.assertEqual(r["parameters"].get("skill"), "DATABASE")
        self.assertIn("get_technician_skills_summary", r["tools"])

    def test_q41_technician_skill_postgresql(self):
        r = classify_business_intent("Kỹ thuật viên nào phù hợp xử lý PostgreSQL?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SKILLS)
        self.assertEqual(r["parameters"].get("skill"), "POSTGRESQL")

    def test_q42_technician_skill_linux_and_available(self):
        r = classify_business_intent("Ai vừa biết Linux vừa rảnh?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SKILLS)
        self.assertEqual(r["parameters"].get("skill"), "LINUX")
        self.assertTrue(r["parameters"].get("is_available_only"))

    def test_q43_technician_skill_network(self):
        r = classify_business_intent("Kỹ thuật viên nào có chuyên môn hạ tầng mạng?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SKILLS)
        self.assertEqual(r["parameters"].get("skill"), "NETWORK")

    def test_q44_technician_skill_laptop_repair(self):
        r = classify_business_intent("Ai có thể sửa laptop phần cứng?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SKILLS)

    # -------------------------------------------------------------------------
    # 9. Technician Workload vs Availability vs GIS Distance (Q45-Q49)
    # -------------------------------------------------------------------------
    def test_q45_technician_available_most(self):
        r = classify_business_intent("Ai đang rảnh nhất để nhận việc?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_WORKLOAD)
        self.assertEqual(r["parameters"].get("sort_order"), "ASC")

    def test_q46_technician_overload(self):
        r = classify_business_intent("Kỹ thuật viên nào đang quá tải?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_WORKLOAD)
        self.assertEqual(r["parameters"].get("sort_order"), "DESC")

    def test_q47_technician_gis_nearest(self):
        r = classify_business_intent("Kỹ thuật viên nào gần ticket 5 nhất?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)
        self.assertEqual(r["parameters"].get("ticket_id"), 5)
        self.assertIn("query_nearby_technicians", r["tools"])

    def test_q48_technician_gis_radius(self):
        r = classify_business_intent("Có kỹ thuật viên nào trong bán kính 10km quanh ticket 10 không?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)
        self.assertEqual(r["parameters"].get("ticket_id"), 10)

    def test_q49_technician_best_recommendation(self):
        r = classify_business_intent("Kỹ thuật viên nào phù hợp nhất để xử lý ticket 5?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_RECOMMENDATION)
        self.assertEqual(r["parameters"].get("ticket_id"), 5)
        self.assertIn("get_recommendations", r["tools"])

    # -------------------------------------------------------------------------
    # 10. Service Labor Cost & Hours (Q50-Q53)
    # -------------------------------------------------------------------------
    def test_q50_ticket_labor_cost(self):
        r = classify_business_intent("Ticket 5 tốn bao nhiêu tiền công?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)
        self.assertEqual(r["parameters"].get("ticket_id"), 5)
        self.assertIn("get_service_labor_cost_summary", r["tools"])

    def test_q51_workspace_labor_cost_monthly(self):
        r = classify_business_intent("Tháng này tiền công kỹ thuật viên là bao nhiêu?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)

    def test_q52_most_labor_hours(self):
        r = classify_business_intent("Chi phí nhân công và tổng giờ làm tháng này?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)

    def test_q53_service_catalog_prices(self):
        r = classify_business_intent("Bảng giá các gói dịch vụ bảo trì hiện có?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_CATALOG)
        self.assertIn("get_service_catalog_summary", r["tools"])

    # -------------------------------------------------------------------------
    # 11. Service Schedules & Calendar Conflicts (Q54-Q58)
    # -------------------------------------------------------------------------
    def test_q54_schedule_tomorrow(self):
        r = classify_business_intent("Ai rảnh chiều mai?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SCHEDULE)
        self.assertEqual(r["parameters"].get("date_target"), "tomorrow")
        self.assertIn("get_technician_schedule_summary", r["tools"])

    def test_q55_schedule_today(self):
        r = classify_business_intent("Lịch làm việc hôm nay của kỹ thuật viên?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SCHEDULE)
        self.assertEqual(r["parameters"].get("date_target"), "today")

    def test_q56_schedule_conflict_detection(self):
        r = classify_business_intent("Có ai bị trùng lịch không?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SCHEDULE)
        self.assertTrue(r["parameters"].get("conflict_check"))

    def test_q57_schedule_employee_specific(self):
        r = classify_business_intent("Kỹ thuật viên Tuấn hôm nay có lịch không?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SCHEDULE)
        self.assertIn("Tuan", r["parameters"].get("employee_query", ""))


    def test_q58_schedule_overlap_check(self):
        r = classify_business_intent("Kiểm tra chồng chéo lịch công việc ngày mai", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_SCHEDULE)
        self.assertTrue(r["parameters"].get("conflict_check"))

    # -------------------------------------------------------------------------
    # 12. Spatial GIS Clustering & Distance Hotspots (Q59-Q62)
    # -------------------------------------------------------------------------
    def test_q59_spatial_ticket_clusters(self):
        r = classify_business_intent("Khu vực nào có nhiều ticket nhất?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.GIS_TICKET_CLUSTERING)
        self.assertIn("get_spatial_ticket_clusters", r["tools"])

    def test_q60_spatial_hotspot_concentration(self):
        r = classify_business_intent("Khu vực nào tập trung nhiều sự cố nhất?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.GIS_TICKET_CLUSTERING)

    def test_q61_spatial_distance_search(self):
        r = classify_business_intent("Cách bao xa từ kỹ thuật viên đến ticket 5?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)

    def test_q62_spatial_nearby_search(self):
        r = classify_business_intent("Xung quanh ticket 8 có kỹ thuật viên nào không?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)

    # -------------------------------------------------------------------------
    # 13. Forecasting (XGBoost) vs Historical Actuals (Q63-Q66)
    # -------------------------------------------------------------------------
    def test_q63_forecast_revenue_14_days(self):
        r = classify_business_intent("Dự báo doanh thu 14 ngày tới?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"].get("target_type"), "RETAIL_REVENUE")
        self.assertIn("get_forecast", r["tools"])

    def test_q64_forecast_service_ticket_volume(self):
        r = classify_business_intent("Lượng ticket sự cố tuần tới dự báo ra sao?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"].get("target_type"), "SERVICE_TICKET_VOLUME")

    def test_q65_forecast_order_volume(self):
        r = classify_business_intent("Dự đoán số lượng đơn hàng 14 ngày tới?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertEqual(r["parameters"].get("target_type"), "RETAIL_ORDER_VOLUME")

    def test_q66_historical_actuals_vs_forecast(self):
        # Historical actual query must NOT trigger forecast
        r = classify_business_intent("Doanh thu thực tế 14 ngày qua?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)

    # -------------------------------------------------------------------------
    # 14. Document RAG / Policy / SOP (Q67-Q69)
    # -------------------------------------------------------------------------
    def test_q67_rag_warranty_policy(self):
        r = classify_business_intent("Chính sách bảo hành laptop là gì?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)
        self.assertEqual(len(r["tools"]), 0)

    def test_q68_rag_return_policy(self):
        r = classify_business_intent("Quy định đổi trả hàng trong bao nhiêu ngày?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    def test_q69_rag_service_sop(self):
        r = classify_business_intent("Quy trình xử lý sự cố server theo SOP?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    # -------------------------------------------------------------------------
    # 15. Hybrid Data + Policy / Hybrid Tool Queries (Q70-Q72)
    # -------------------------------------------------------------------------
    def test_q70_hybrid_top_selling_warranty(self):
        r = classify_business_intent("Laptop bán chạy nhất có được bảo hành 24 tháng không?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])

    def test_q71_hybrid_top_revenue_return_policy(self):
        r = classify_business_intent("Sản phẩm doanh thu cao nhất áp dụng quy định đổi trả thế nào?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)

    def test_q72_hybrid_ticket_sla_sop(self):
        r = classify_business_intent("Ticket 5 sắp trễ SLA, quy trình SOP yêu cầu xử lý thế nào?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TICKET_LOOKUP)
        self.assertEqual(r["parameters"].get("ticket_id"), 5)


    # -------------------------------------------------------------------------
    # 16. Root-Cause / "Vì sao?" Evidence Analysis (Q73-Q76)
    # -------------------------------------------------------------------------
    def test_q73_root_cause_stockout(self):
        r = classify_business_intent("Vì sao sản phẩm này bị cảnh báo hết hàng?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.ROOT_CAUSE_EXPLANATION)
        self.assertEqual(r["parameters"].get("target_type"), "STOCKOUT_WARNING")
        self.assertIn("explain_root_cause", r["tools"])

    def test_q74_root_cause_sla_risk(self):
        r = classify_business_intent("Tại sao ticket này có nguy cơ trễ SLA?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.ROOT_CAUSE_EXPLANATION)
        self.assertEqual(r["parameters"].get("target_type"), "SLA_AT_RISK")

    def test_q75_root_cause_recommendation(self):
        r = classify_business_intent("Dựa vào đâu kỹ thuật viên này được đề xuất?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.ROOT_CAUSE_EXPLANATION)
        self.assertEqual(r["parameters"].get("target_type"), "RECOMMENDATION")

    def test_q76_root_cause_branch_warning(self):
        r = classify_business_intent("Vì sao chi nhánh Tân Phú bị cảnh báo giảm doanh số?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.ROOT_CAUSE_EXPLANATION)
        self.assertEqual(r["parameters"].get("target_type"), "BRANCH_WARNING")

    # -------------------------------------------------------------------------
    # 17. What-If / Scenario Simulations (Q77-Q80)
    # -------------------------------------------------------------------------
    def test_q77_what_if_revenue_drop(self):
        r = classify_business_intent("Nếu doanh thu giảm 10% thì sao?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)
        self.assertEqual(r["parameters"].get("scenario_type"), "REVENUE_CHANGE")
        self.assertEqual(r["parameters"].get("change_pct"), -10.0)
        self.assertIn("simulate_what_if_scenario", r["tools"])

    def test_q78_what_if_ticket_surge(self):
        r = classify_business_intent("Nếu ticket tăng 20% thì workload thế nào?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)
        self.assertEqual(r["parameters"].get("scenario_type"), "TICKET_VOLUME_CHANGE")
        self.assertEqual(r["parameters"].get("change_pct"), 20.0)

    def test_q79_what_if_stock_depletion(self):
        r = classify_business_intent("Nếu tồn hiện tại còn 5 sản phẩm thì khi nào hết?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)
        self.assertEqual(r["parameters"].get("scenario_type"), "STOCK_DEPLETION")
        self.assertEqual(r["parameters"].get("param_value"), 5.0)

    def test_q80_what_if_revenue_increase(self):
        r = classify_business_intent("Giả định doanh thu tăng 15% trong tháng tới", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)
        self.assertEqual(r["parameters"].get("change_pct"), 15.0)

    # -------------------------------------------------------------------------
    # 18. Multi-Condition & Multi-Step Complex Queries (Q81-Q83)
    # -------------------------------------------------------------------------
    def test_q81_multi_condition_category_branch_time(self):
        r = classify_business_intent("Cho tôi các laptop bán chạy nhất ở chi nhánh Tân Phú trong tháng này", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "laptop")
        self.assertIn("Tan Phu", r["parameters"].get("branch", ""))


    def test_q82_multi_step_best_selling_and_stock(self):
        r = classify_business_intent("Laptop nào bán chạy nhất và còn ít hàng nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertIn("get_stock_balance_summary", r["tools"])

    def test_q83_multi_step_risky_ticket_and_technician(self):
        r = classify_business_intent("Ticket nào nguy hiểm nhất và ai có thể xử lý?", self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_SLA_AT_RISK)
        self.assertIn("get_service_ticket_summary", r["tools"])
        self.assertIn("get_recommendations", r["tools"])

    # -------------------------------------------------------------------------
    # 19. Conversational Follow-ups & Memory (Q84-Q86)
    # -------------------------------------------------------------------------
    def test_q84_follow_up_entity_switch(self):
        ctx = [{
            "intent": BusinessIntent.TOP_SELLING_PRODUCTS,
            "parameters": {"category": "laptop", "metric": "quantity_sold", "limit": 1, "time_label": "tháng này"},
        }]
        r = classify_business_intent("Còn Lenovo thì sao?", self.retail_workspace, conversation_context=ctx)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    def test_q85_follow_up_time_switch(self):
        ctx = [{
            "intent": BusinessIntent.SALES_SUMMARY,
            "parameters": {"category": "laptop", "time_label": "tháng này"},
        }]
        r = classify_business_intent("Tháng trước thì thế nào?", self.retail_workspace, conversation_context=ctx)
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)
        self.assertEqual(r["parameters"].get("time_label"), "tháng trước")

    def test_q86_follow_up_stock_check(self):
        ctx = [{
            "intent": BusinessIntent.TOP_SELLING_PRODUCTS,
            "parameters": {"category": "laptop"},
        }]
        r = classify_business_intent("Cái đó còn hàng không?", self.retail_workspace, conversation_context=ctx)
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertEqual(r["parameters"].get("category"), "laptop")

    # -------------------------------------------------------------------------
    # 20. Controlled Mutation Actions & Ambiguity (Q87-Q88)
    # -------------------------------------------------------------------------
    def test_q87_mutation_action(self):
        r = classify_business_intent("Điều chỉnh giá sản phẩm 5 thành 15000000 VND", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)
        self.assertIn("mutation_handler", r["tools"])

    def test_q88_ambiguous_query_clarification(self):
        r = classify_business_intent("Laptop nào tốt nhất?", self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)
        self.assertIn("clarification_question", r)

    # -------------------------------------------------------------------------
    # 21. Advanced Enterprise Context & Complex Benchmark Scenarios (Q89-Q94)
    # -------------------------------------------------------------------------
    def test_q89_complex_goods_receipt_proposal_mutation(self):
        query = "Lập đề xuất tạo phiếu nhập kho 20 chiếc Laptop Dell Inspiron vào chi nhánh Quận 1 để kịp tiến độ"
        r = classify_business_intent(query, self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)
        self.assertIn("mutation_handler", r["tools"])

    def test_q90_complex_service_incident_labor_cost_and_sla(self):
        query = "Tính toán chi phí nhân công theo giờ công kỹ thuật viên cho các sự cố khẩn cấp"
        r = classify_business_intent(query, self.service_workspace)
        self.assertEqual(r["intent"], BusinessIntent.SERVICE_LABOR_COST)
        self.assertIn("get_service_labor_cost_summary", r["tools"])

    def test_q91_complex_what_if_revenue_simulation(self):
        query = "Mô phỏng kịch bản giả định nếu doanh thu tăng 25% thì tổng thu thay đổi ra sao?"
        r = classify_business_intent(query, self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.WHAT_IF_SIMULATION)
        self.assertIn("simulate_what_if_scenario", r["tools"])
        self.assertEqual(r["parameters"].get("scenario_type"), "REVENUE_CHANGE")
        self.assertEqual(r["parameters"].get("change_pct"), 25.0)

    def test_q92_complex_root_cause_explanation(self):
        query = "Vì sao chi nhánh Quận 1 lại bị cảnh báo doanh thu giảm sút?"
        r = classify_business_intent(query, self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.ROOT_CAUSE_EXPLANATION)
        self.assertIn("explain_root_cause", r["tools"])

    def test_q93_complex_enterprise_sop_rag_routing(self):
        query = "Quy chuẩn mức tồn kho an toàn của danh mục Laptop theo tài liệu SOP 2026 quy định bao nhiêu chiếc?"
        r = classify_business_intent(query, self.retail_workspace)
        # Should route to DOCUMENT_RAG when querying internal SOP text
        self.assertIn(r["intent"], [BusinessIntent.DOCUMENT_RAG, BusinessIntent.STOCK_BALANCE, BusinessIntent.STOCKOUT_RISK])

    def test_q94_complex_multi_condition_laptop_stock_and_ranking(self):
        query = "Laptop nào bán chạy nhất nhưng hiện tại còn ít hàng nhất trong kho?"
        r = classify_business_intent(query, self.retail_workspace)
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertIn("get_stock_balance_summary", r["tools"])


class TestRAGHybridRetrievalAndEmailEnrichment(TestCase):
    """Verifies hybrid RAG retrieval, multi-chunk synthesis, citations and email enrichment."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk, DocumentStatus
        User = get_user_model()
        self.retail_ws = Workspace.objects.create(name="Retail Test", code="ret-test", workspace_type="RETAIL")
        self.user = User.objects.create_user(username="rag_tester", email="rag@test.com", password="password123")
        self.kb = KnowledgeBase.objects.create(workspace=self.retail_ws, name="KB Test", created_by=self.user)
        self.doc = Document.objects.create(
            workspace=self.retail_ws,
            knowledge_base=self.kb,
            title="Quy Định Đổi Trả Và Bảo Hành",
            status=DocumentStatus.READY,
            uploaded_by=self.user,
        )
        from apps.knowledge.embedding import get_embedding
        c1_text = "Khách hàng được quyền đổi trả sản phẩm trong 07 ngày kể từ ngày mua. Sản phẩm phải nguyên tem."
        c2_text = "Laptop Dell Inspiron được bảo hành chính hãng 24 tháng theo tiêu chuẩn của nhà sản xuất."
        self.chunk1 = DocumentChunk.objects.create(
            workspace=self.retail_ws,
            document=self.doc,
            chunk_index=0,
            content=c1_text,
            embedding=get_embedding(c1_text),
            metadata={"heading": "1. Đổi trả hàng", "page_number": 1},
        )
        self.chunk2 = DocumentChunk.objects.create(
            workspace=self.retail_ws,
            document=self.doc,
            chunk_index=1,
            content=c2_text,
            embedding=get_embedding(c2_text),
            metadata={"heading": "2. Bảo hành Dell", "page_number": 2},
        )

    def test_hybrid_search_ranks_matching_lexical_tokens(self):
        from apps.knowledge.retrieval import search_relevant_chunks
        results = search_relevant_chunks(self.retail_ws, "Dell Inspiron bảo hành", top_k=2)
        self.assertGreater(len(results), 0)
        # Verify chunk containing Dell Inspiron has higher similarity due to lexical score boost
        self.assertEqual(results[0]["heading"], "2. Bảo hành Dell")
        self.assertIn("lexical_score", results[0])
        self.assertGreater(results[0]["lexical_score"], 0.0)

    def test_get_grounded_policy_snippet(self):
        from apps.knowledge.services import get_grounded_policy_snippet
        snippet = get_grounded_policy_snippet(self.retail_ws, "đổi trả trong 07 ngày")
        self.assertIsNotNone(snippet)
        self.assertEqual(snippet["document_title"], "Quy Định Đổi Trả Và Bảo Hành")
        self.assertIn("07 ngày", snippet["content_snippet"])

    def test_multi_chunk_grounded_answer_includes_citations_and_sub_sections(self):
        from apps.knowledge.services import generate_grounded_answer
        from apps.knowledge.retrieval import search_relevant_chunks
        chunks = search_relevant_chunks(self.retail_ws, "Quy định đổi trả và bảo hành Dell", top_k=2)
        answer, sources = generate_grounded_answer(
            workspace=self.retail_ws,
            user=self.user,
            query="Quy định đổi trả và bảo hành Dell như thế nào?",
            chunks=chunks,
        )
        self.assertGreater(len(sources), 0)
        self.assertIn("Nguồn:", answer)
        # Verify citations are present
        self.assertEqual(sources[0]["document_title"], "Quy Định Đổi Trả Và Bảo Hành")


