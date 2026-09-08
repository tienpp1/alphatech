"""
test_ai_intent_router.py
Automated test suite for the deterministic Vietnamese Business Intent Router.
Tests intent classification, entity/parameter extraction, tool selection,
date-range parsing, limit/sort extraction, category detection, and ambiguity handling.

Coverage:
- CATALOG (3)
- SALES ranking (6)
- REVENUE ranking (3)
- CUSTOMER analytics (3)
- BRANCH analytics (3)
- FORECAST (3)
- SERVICE TICKET (3)
- TECHNICIAN / GIS (4)
- RAG / document (3)
- AMBIGUOUS (3)
- MUTATION (3)
Total: 37 cases
"""

from datetime import date
from django.test import TestCase

from apps.knowledge.intent_router import (
    BusinessIntent,
    classify_business_intent,
    extract_product_category,
    extract_limit_and_ordering,
    parse_date_range_from_text,
    strip_accents_and_lower,
)
from apps.workspaces.models import Workspace, WorkspaceType


class IntentRouterUtilTests(TestCase):
    """Unit tests for pure helper functions (no DB)."""

    def test_strip_accents_and_lower_basic(self):
        self.assertEqual(strip_accents_and_lower("Sản Phẩm"), "san pham")

    def test_strip_accents_handles_d_with_stroke(self):
        self.assertEqual(strip_accents_and_lower("Đơn hàng"), "don hang")

    def test_strip_accents_empty_string(self):
        self.assertEqual(strip_accents_and_lower(""), "")

    def test_extract_category_laptop(self):
        self.assertEqual(extract_product_category("Laptop nào bán chạy nhất?"), "laptop")

    def test_extract_category_smartphone(self):
        self.assertEqual(extract_product_category("Điện thoại nào bán chạy nhất?"), "smartphone")

    def test_extract_category_mouse(self):
        self.assertEqual(extract_product_category("chuột nào đang kinh doanh?"), "mouse")

    def test_extract_category_none(self):
        self.assertIsNone(extract_product_category("Sản phẩm nào bán chạy nhất?"))

    def test_extract_limit_top5(self):
        limit, sort = extract_limit_and_ordering("Top 5 laptop bán chạy nhất")
        self.assertEqual(limit, 5)
        self.assertEqual(sort, "DESC")

    def test_extract_limit_top3(self):
        limit, sort = extract_limit_and_ordering("top 3 chi nhánh doanh thu cao nhất")
        self.assertEqual(limit, 3)
        self.assertEqual(sort, "DESC")

    def test_extract_limit_default_for_nhat(self):
        limit, sort = extract_limit_and_ordering("Laptop nào bán chạy nhất?")
        self.assertEqual(limit, 1)
        self.assertEqual(sort, "DESC")

    def test_extract_limit_ascending(self):
        limit, sort = extract_limit_and_ordering("Chi nhánh doanh thu thấp nhất")
        self.assertEqual(sort, "ASC")

    def test_date_range_thang_nay(self):
        today = date(2026, 8, 31)
        start, end, label = parse_date_range_from_text("tháng này", reference_date=today)
        self.assertEqual(start, date(2026, 8, 1))
        self.assertEqual(end, today)
        self.assertIn("tháng", label)

    def test_date_range_thang_truoc(self):
        today = date(2026, 8, 15)
        start, end, label = parse_date_range_from_text("tháng trước", reference_date=today)
        self.assertEqual(start.month, 7)
        self.assertIn("trước", label)

    def test_date_range_7_ngay_qua(self):
        today = date(2026, 8, 31)
        start, end, label = parse_date_range_from_text("7 ngày qua", reference_date=today)
        self.assertEqual((end - start).days, 7)

    def test_date_range_no_mention(self):
        _, _, label = parse_date_range_from_text("Laptop nào bán chạy nhất?")
        self.assertEqual(label, "toàn thời gian")


class RetailWorkspaceIntentTests(TestCase):
    """Intent routing tests using a Retail workspace instance."""

    @classmethod
    def setUpTestData(cls):
        cls.retail_ws = Workspace.objects.create(
            code="retail-intent-test",
            name="Retail Intent Test",
            workspace_type=WorkspaceType.RETAIL,
        )

    def _classify(self, query: str):
        return classify_business_intent(query, self.retail_ws)

    # -----------------------------------------------------------------------
    # CATALOG
    # -----------------------------------------------------------------------
    def test_catalog_count_laptop_vi(self):
        """'Có bao nhiêu laptop?' → CATALOG_COUNT, get_product_catalog_summary, category=laptop"""
        r = self._classify("Có bao nhiêu laptop đang kinh doanh?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertIn("get_product_catalog_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_catalog_count_general_products(self):
        """'Có bao nhiêu sản phẩm?' → CATALOG_COUNT"""
        r = self._classify("Có bao nhiêu sản phẩm đang hoạt động?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertIn("get_product_catalog_summary", r["tools"])

    def test_catalog_active_list(self):
        """'Sản phẩm nào đang kinh doanh?' → CATALOG_COUNT"""
        r = self._classify("Sản phẩm nào đang kinh doanh?")
        self.assertEqual(r["intent"], BusinessIntent.CATALOG_COUNT)
        self.assertIn("get_product_catalog_summary", r["tools"])

    # -----------------------------------------------------------------------
    # SALES RANKING (quantity_sold)
    # -----------------------------------------------------------------------
    def test_sales_top1_laptop_ban_chay_nhat(self):
        """'Laptop nào bán chạy nhất?' → TOP_SELLING_PRODUCTS, get_top_selling_products, category=laptop, metric=quantity_sold"""
        r = self._classify("Laptop nào bán chạy nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertNotIn("get_product_catalog_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")
        self.assertEqual(r["parameters"]["metric"], "quantity_sold")

    def test_sales_top5_laptop_thang_nay(self):
        """'Top 5 laptop bán nhiều nhất tháng này' → TOP_SELLING_PRODUCTS, limit=5, metric=quantity_sold"""
        r = self._classify("Top 5 laptop bán nhiều nhất tháng này")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")
        self.assertEqual(r["parameters"]["limit"], 5)
        self.assertIsNotNone(r["parameters"].get("start_date"))

    def test_sales_top_smartphone_ban_nhieu_nhat(self):
        """'Điện thoại nào bán được nhiều nhất?' → TOP_SELLING_PRODUCTS, category=smartphone"""
        r = self._classify("Điện thoại nào bán được nhiều nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertEqual(r["parameters"]["category"], "smartphone")

    def test_sales_no_category_ban_chay(self):
        """'Sản phẩm nào bán chạy nhất?' → TOP_SELLING_PRODUCTS, category=None"""
        r = self._classify("Sản phẩm nào bán chạy nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertIsNone(r["parameters"].get("category"))

    def test_sales_mat_hang_ban_nhieu_nhat(self):
        """'Mặt hàng nào bán nhiều nhất?' — using synonym 'mặt hàng' → SALES"""
        r = self._classify("Mặt hàng nào bán nhiều nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_SELLING_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])

    def test_sales_ascending_it_ban_nhat(self):
        """'Sản phẩm bán ít nhất?' → sales ranking, ASC sort"""
        r = self._classify("Sản phẩm nào bán ít nhất?")
        self.assertIn(r["intent"], [BusinessIntent.TOP_SELLING_PRODUCTS, BusinessIntent.TOP_REVENUE_PRODUCTS])
        self.assertIn("get_top_selling_products", r["tools"])

    # -----------------------------------------------------------------------
    # REVENUE RANKING
    # -----------------------------------------------------------------------
    def test_revenue_laptop_doanh_thu_cao_nhat(self):
        """'Laptop nào có doanh thu cao nhất?' → TOP_REVENUE_PRODUCTS, metric=revenue"""
        r = self._classify("Laptop nào có doanh thu cao nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_REVENUE_PRODUCTS)
        self.assertIn("get_top_selling_products", r["tools"])
        self.assertEqual(r["parameters"]["metric"], "revenue")
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_revenue_summary_thang_nay(self):
        """'Doanh thu tháng này bao nhiêu?' → SALES_SUMMARY, get_sales_summary"""
        r = self._classify("Doanh thu tháng này bao nhiêu?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)
        self.assertIn("get_sales_summary", r["tools"])

    def test_revenue_general_total(self):
        """'Tổng doanh thu năm nay?' → SALES_SUMMARY"""
        r = self._classify("Tổng doanh thu năm nay?")
        self.assertEqual(r["intent"], BusinessIntent.SALES_SUMMARY)
        self.assertIn("get_sales_summary", r["tools"])

    # -----------------------------------------------------------------------
    # CUSTOMER ANALYTICS
    # -----------------------------------------------------------------------
    def test_customer_top_buyer_mua_nhieu_nhat(self):
        """'Khách hàng nào mua nhiều nhất?' → TOP_CUSTOMERS, get_top_customers"""
        r = self._classify("Khách hàng nào mua nhiều nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertIn("get_top_customers", r["tools"])

    def test_customer_chi_tieu_cao_nhat(self):
        """'Khách hàng nào có doanh thu cao nhất?' → TOP_CUSTOMERS"""
        r = self._classify("Khách hàng nào chi tiêu cao nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertIn("get_top_customers", r["tools"])

    def test_customer_vip_segment(self):
        """'Top 3 khách VIP mua nhiều nhất?' → TOP_CUSTOMERS, limit=3"""
        r = self._classify("Top 3 khách VIP mua nhiều nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TOP_CUSTOMERS)
        self.assertIn("get_top_customers", r["tools"])
        self.assertEqual(r["parameters"]["limit"], 3)

    # -----------------------------------------------------------------------
    # BRANCH ANALYTICS
    # -----------------------------------------------------------------------
    def test_branch_thap_nhat(self):
        """'Chi nhánh nào có doanh thu thấp nhất?' → BRANCH_REVENUE, sort=ASC"""
        r = self._classify("Chi nhánh nào có doanh thu thấp nhất?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertIn("get_branch_sales_analytics", r["tools"])
        self.assertEqual(r["parameters"]["sort_order"], "ASC")

    def test_branch_cao_nhat(self):
        """'Chi nhánh nào bán chạy nhất?' → BRANCH_REVENUE, sort=DESC"""
        r = self._classify("Chi nhánh nào bán chạy nhất?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertIn("get_branch_sales_analytics", r["tools"])
        self.assertEqual(r["parameters"]["sort_order"], "DESC")

    def test_branch_top3(self):
        """'Top 3 chi nhánh doanh thu cao nhất tháng này?' → BRANCH, limit=3"""
        r = self._classify("Top 3 chi nhánh doanh thu cao nhất tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.BRANCH_REVENUE)
        self.assertIn("get_branch_sales_analytics", r["tools"])

    # -----------------------------------------------------------------------
    # FORECAST
    # -----------------------------------------------------------------------
    def test_forecast_14_ngay_toi(self):
        """'Doanh thu 14 ngày tới dự kiến thế nào?' → FORECAST, get_forecast"""
        r = self._classify("Doanh thu 14 ngày tới dự kiến thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertIn("get_forecast", r["tools"])

    def test_forecast_du_bao(self):
        """'Dự báo doanh thu tháng tới?' → FORECAST"""
        r = self._classify("Dự báo doanh thu tháng tới?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertIn("get_forecast", r["tools"])

    def test_forecast_xgboost(self):
        """'Kết quả dự báo XGBoost?' → FORECAST"""
        r = self._classify("Kết quả dự báo XGBoost cho tháng này?")
        self.assertEqual(r["intent"], BusinessIntent.FORECAST_METRICS)
        self.assertIn("get_forecast", r["tools"])

    # -----------------------------------------------------------------------
    # RAG / DOCUMENT
    # -----------------------------------------------------------------------
    def test_rag_chinh_sach_bao_hanh(self):
        """'Chính sách bảo hành laptop là gì?' → DOCUMENT_RAG, no business tool"""
        r = self._classify("Chính sách bảo hành laptop là gì?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)
        # No structured business tool for RAG-only question
        self.assertNotIn("get_top_selling_products", r["tools"])
        self.assertNotIn("get_product_catalog_summary", r["tools"])

    def test_rag_quy_trinh_bao_tri(self):
        """'Quy trình bảo trì server thế nào?' → DOCUMENT_RAG"""
        r = self._classify("Quy trình bảo trì server thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    def test_rag_chinh_sach_doi_tra(self):
        """'Chính sách đổi trả hàng như thế nào?' → DOCUMENT_RAG"""
        r = self._classify("Chính sách đổi trả hàng như thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.DOCUMENT_RAG)

    # -----------------------------------------------------------------------
    # AMBIGUOUS
    # -----------------------------------------------------------------------
    def test_ambiguous_tot_nhat_no_metric(self):
        """'Laptop nào tốt nhất?' → AMBIGUOUS, clarification_question returned"""
        r = self._classify("Laptop nào tốt nhất?")
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)
        self.assertIn("clarification_question", r)
        self.assertTrue(len(r["clarification_question"]) > 0)
        self.assertEqual(r["tools"], [])

    def test_not_ambiguous_when_metric_specified(self):
        """'Laptop nào tốt nhất về doanh thu?' → NOT ambiguous (metric=revenue explicit)"""
        r = self._classify("Laptop nào tốt nhất về doanh thu?")
        # Should route to revenue ranking, not ambiguous
        self.assertNotEqual(r["intent"], BusinessIntent.AMBIGUOUS)

    def test_ambiguous_san_pham_hay_nhat(self):
        """'Sản phẩm hay nhất là gì?' → AMBIGUOUS"""
        r = self._classify("Sản phẩm hay nhất là gì?")
        self.assertEqual(r["intent"], BusinessIntent.AMBIGUOUS)

    # -----------------------------------------------------------------------
    # MUTATION
    # -----------------------------------------------------------------------
    def test_mutation_dieu_chinh_gia(self):
        """'Điều chỉnh giá sản phẩm X thành Y.' → MUTATION"""
        r = self._classify("Điều chỉnh giá sản phẩm 12 thành 5000000.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_mutation_phan_cong(self):
        """'Phân công kỹ thuật viên A cho ticket B.' → MUTATION"""
        r = self._classify("Phân công kỹ thuật viên 3 cho ticket 5.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    def test_mutation_cap_nhat_trang_thai(self):
        """'Cập nhật trạng thái đơn hàng.' → MUTATION"""
        r = self._classify("Cập nhật trạng thái đơn hàng 10 thành COMPLETED.")
        self.assertEqual(r["intent"], BusinessIntent.MUTATION_ACTION)

    # -----------------------------------------------------------------------
    # STOCKOUT RISK & INVENTORY BALANCE INTENTS (RETAIL EXTENSION)
    # -----------------------------------------------------------------------
    def test_stockout_risk_san_pham_nguy_co_het_hang(self):
        """'Sản phẩm nào có nguy cơ hết hàng trong 7 ngày tới?' → STOCKOUT_RISK"""
        r = self._classify("Sản phẩm nào có nguy cơ hết hàng trong 7 ngày tới?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])

    def test_stockout_risk_laptop_sap_het(self):
        """'Laptop nào sắp hết hàng?' → STOCKOUT_RISK, category='laptop'"""
        r = self._classify("Laptop nào sắp hết hàng?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_stockout_risk_chi_nhanh_thieu_laptop(self):
        """'Chi nhánh nào đang thiếu laptop?' → STOCKOUT_RISK, category='laptop'"""
        r = self._classify("Chi nhánh nào đang thiếu laptop?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_stockout_risk_de_xuat_nhap_hang(self):
        """'Đề xuất nhập hàng cho các sản phẩm thiếu hụt?' → STOCKOUT_RISK"""
        r = self._classify("Đề xuất nhập hàng cho các sản phẩm thiếu hụt?")
        self.assertEqual(r["intent"], BusinessIntent.STOCKOUT_RISK)
        self.assertIn("get_stockout_risk_summary", r["tools"])

    def test_stock_balance_ton_kho_laptop(self):
        """'Tồn kho laptop hiện tại thế nào?' → STOCK_BALANCE, category='laptop'"""
        r = self._classify("Tồn kho laptop hiện tại thế nào?")
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertIn("get_stock_balance_summary", r["tools"])
        self.assertEqual(r["parameters"]["category"], "laptop")

    def test_stock_balance_kiem_tra_so_luong_ton(self):
        """'Kiểm tra số lượng tồn kho của các chi nhánh?' → STOCK_BALANCE"""
        r = self._classify("Kiểm tra số lượng tồn kho của các chi nhánh?")
        self.assertEqual(r["intent"], BusinessIntent.STOCK_BALANCE)
        self.assertIn("get_stock_balance_summary", r["tools"])


class ServiceWorkspaceIntentTests(TestCase):
    """Intent routing tests using a Service workspace instance."""

    @classmethod
    def setUpTestData(cls):
        cls.service_ws = Workspace.objects.create(
            code="service-intent-test",
            name="Service Intent Test",
            workspace_type=WorkspaceType.SERVICE,
        )

    def _classify(self, query: str):
        return classify_business_intent(query, self.service_ws)

    def test_service_ticket_sla_at_risk(self):
        """'Ticket nào sắp vi phạm SLA?' → SERVICE_SLA_AT_RISK, get_service_ticket_summary"""
        r = self._classify("Ticket nào sắp vi phạm SLA?")
        self.assertIn(r["intent"], [BusinessIntent.SERVICE_SLA_AT_RISK, BusinessIntent.SERVICE_TICKETS_SUMMARY])
        self.assertIn("get_service_ticket_summary", r["tools"])

    def test_service_ticket_dang_xu_ly(self):
        """'Có bao nhiêu ticket đang xử lý?' → SERVICE_TICKETS_SUMMARY"""
        r = self._classify("Có bao nhiêu ticket đang xử lý?")
        self.assertIn(r["intent"], [BusinessIntent.SERVICE_TICKETS_SUMMARY, BusinessIntent.SERVICE_SLA_AT_RISK])
        self.assertIn("get_service_ticket_summary", r["tools"])

    def test_technician_qua_tai(self):
        """'Kỹ thuật viên nào đang quá tải?' → TECHNICIAN_WORKLOAD, get_technician_workload_summary"""
        r = self._classify("Kỹ thuật viên nào đang quá tải?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_WORKLOAD)
        self.assertIn("get_technician_workload_summary", r["tools"])

    def test_technician_gan_nhat_gis(self):
        """'Kỹ thuật viên nào gần ticket 5 nhất?' → TECHNICIAN_NEARBY_GIS"""
        r = self._classify("Kỹ thuật viên nào gần ticket 5 nhất?")
        self.assertEqual(r["intent"], BusinessIntent.TECHNICIAN_NEARBY_GIS)
        self.assertIn("query_nearby_technicians", r["tools"])
        self.assertEqual(r["parameters"]["ticket_id"], 5)
