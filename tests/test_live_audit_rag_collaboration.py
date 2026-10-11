"""11/10 audit regressions. Synthetic DB; no live provider/production writes."""
import json
from types import SimpleNamespace
from unittest.mock import patch
from io import StringIO
from django.core.management import call_command

from django.test import TestCase, SimpleTestCase, override_settings
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.public_web.models import SocialIdentity
from apps.notifications.models import TeamChatMessage, InternalBulletin
from apps.notifications.chat_service import get_workspace_colleagues, verify_chat_access
from apps.knowledge.services import generate_grounded_answer, _numeric_source_disagreements
from apps.knowledge.services import detect_and_handle_mutation_request
from apps.knowledge.retrieval import _matches_requested_navigation_topic


class CollaborationAuditRegressions(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(name="Audit", code="audit-root", workspace_type="RETAIL")
        self.manager = User.objects.create_user(username="audit-manager")
        self.role = Role.objects.create(name="MANAGER")
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.manager, role=self.role, is_default=True)
        self.client.force_login(self.manager)

    def test_non_object_and_non_text_json_is_rejected_without_business_write(self):
        for path in ("/api/v1/notifications/chat/send/", "/api/v1/notifications/bulletins/create/"):
            for payload in ([], None, "text", 42, {"message": [], "title": {}, "content": 2}):
                with self.subTest(path=path, payload=payload):
                    self.assertEqual(self.client.post(path, json.dumps(payload), content_type="application/json").status_code, 400)
        self.assertEqual(TeamChatMessage.objects.count(), 0)
        self.assertEqual(InternalBulletin.objects.count(), 0)

    def test_invalid_bulletin_choices_and_length_return_400(self):
        for change in ({"priority": "INVALID"}, {"title": "x" * 256}):
            payload = {"title": "Title", "content": "Body", "workspace_id": str(self.ws.pk), **change}
            self.assertEqual(self.client.post("/api/v1/notifications/bulletins/create/", json.dumps(payload), content_type="application/json").status_code, 400)

    def test_roster_and_direct_chat_exclude_google_viewer_and_inactive(self):
        for username, role_name, google, active in (("viewer", "VIEWER", False, True),
                ("linked", "EMPLOYEE", True, True), ("inactive", "EMPLOYEE", False, False)):
            user = User.objects.create_user(username=username, email=f"{username}@example.test", is_active=active)
            role, _ = Role.objects.get_or_create(name=role_name)
            WorkspaceMembership.objects.create(workspace=self.ws, user=user, role=role)
            if google:
                SocialIdentity.objects.create(user=user, provider="GOOGLE", subject=username, provider_email="audit@example.test")
            self.assertFalse(verify_chat_access(user, self.ws))
        self.assertEqual([m["user_id"] for m in get_workspace_colleagues(self.ws)], [self.manager.pk])

    def test_customer_denial_html_and_api_contract(self):
        SocialIdentity.objects.create(user=self.manager, provider="GOOGLE", subject="manager-linked", provider_email="linked@example.test")
        response = self.client.get("/noibo/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Về tài khoản khách hàng", status_code=403)
        api = self.client.get("/api/v1/notifications/chat/messages/", HTTP_ACCEPT="application/json")
        self.assertEqual(api.status_code, 403)
        self.assertIn("detail", api.json())

    def test_incomplete_actions_never_choose_first_entities(self):
        from apps.retail.models import Product, Branch, Supplier, Category
        from apps.approvals.models import ApprovalRequest
        category = Category.objects.create(workspace=self.ws, code="safe-category", name="Laptop")
        Product.objects.create(workspace=self.ws, category=category, sku="safe-product", name="Laptop", unit_price=100)
        Branch.objects.create(workspace=self.ws, code="safe-branch", name="Branch")
        Supplier.objects.create(workspace=self.ws, code="safe-supplier", name="Supplier")
        for query in ("Tạo phiếu nhập kho 20 laptop", "Lập đề xuất điều chuyển laptop",
                      "Đề xuất hạ giá xả kho cho laptop", "Lập đề xuất đổi mới DOA",
                      "Lập đề xuất chi viện"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                detect_and_handle_mutation_request(query, self.ws, self.manager)
        self.assertEqual(ApprovalRequest.objects.count(), 0)

    def test_ambiguous_goods_receipt_cost_never_creates_proposal(self):
        from apps.retail.models import Product, Branch, Supplier, Category
        from apps.approvals.models import ApprovalRequest
        category = Category.objects.create(workspace=self.ws, code="cost-category", name="Laptop")
        Product.objects.create(workspace=self.ws, category=category, sku="LAP-COST", name="Cost laptop", unit_price=100)
        Branch.objects.create(workspace=self.ws, code="BR-COST", name="Cost branch")
        Supplier.objects.create(workspace=self.ws, code="SUP-COST", name="Cost supplier")
        for value in ("12.5", "12,5", "0", "1.25.000", "-100"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                detect_and_handle_mutation_request(f"Tạo phiếu nhập 20 chiếc sản phẩm LAP-COST chi nhánh BR-COST nhà cung cấp SUP-COST đơn giá {value}", self.ws, self.manager)
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_quantity_percentage_and_price_do_not_parse_partial_signed_numbers(self):
        from apps.retail.models import Product, Category, Branch, Supplier
        category = Category.objects.create(workspace=self.ws, code="parse-laptop", name="Laptop")
        product = Product.objects.create(workspace=self.ws, category=category, sku="PARSE-SKU", name="Laptop", unit_price=1000000)
        Branch.objects.create(workspace=self.ws, code="PARSE-BR", name="Parse branch")
        Supplier.objects.create(workspace=self.ws, code="PARSE-SUP", name="Parse supplier")
        queries = [f"Điều chỉnh giá sản phẩm #{product.pk} thành {value} VND" for value in ("12.5", "-125", "0")]
        queries += [f"Giảm giá PARSE-SKU {value}%" for value in ("12.5", "-5", "0", "100")]
        queries += [f"Tạo phiếu nhập {value} chiếc PARSE-SKU chi nhánh PARSE-BR nhà cung cấp PARSE-SUP đơn giá 1000" for value in ("1.5", "-2", "0")]
        with patch("apps.approvals.executor.execute_tool") as executor:
            for query in queries:
                with self.subTest(query=query), self.assertRaises(ValueError):
                    detect_and_handle_mutation_request(query, self.ws, self.manager)
            executor.assert_not_called()

    def test_procedure_and_hypothetical_questions_never_create_proposals(self):
        with patch("apps.approvals.executor.execute_tool") as executor:
            for query in ("Khi nào nên giảm giá laptop 5%?", "Quy trình lập lịch bảo trì ticket 1", "Nếu nhập thêm 20 chiếc thì sao?"):
                self.assertIsNone(detect_and_handle_mutation_request(query, self.ws, self.manager))
            executor.assert_not_called()

    def test_schedule_router_requires_explicit_ticket_and_preserves_selected_id(self):
        with patch("apps.approvals.executor.execute_tool", return_value={"status": "PENDING"}) as executor:
            with self.assertRaises(ValueError):
                detect_and_handle_mutation_request("Lập lịch nhiệm vụ bảo trì cho kỹ thuật viên 3", self.ws, self.manager)
            detect_and_handle_mutation_request('Lập lịch "TEST bảo trì" cho ticket #29 kỹ thuật viên 3', self.ws, self.manager)
            self.assertEqual(executor.call_args.kwargs["parameters"], {"title": "TEST bảo trì", "ticket_id": 29, "employee_id": 3})


@override_settings(LLM_API_KEY="", GEMINI_API_KEY="")
class GroundingAuditRegressions(SimpleTestCase):
    def chunk(self, text, heading="Bảo hành", page=1, **extra):
        return dict(document_title="Academic policy", content=text, heading=heading,
                    chunk_id=page, similarity=.9, page_number=page, **extra)

    def test_list_numbers_are_not_semantic_conflicts(self):
        self.assertEqual(_numeric_source_disagreements([self.chunk("1. Mua hàng\n2. Mua hàng", heading="Mua hàng")]), [])

    def test_purchase_navigation_does_not_use_unrequested_return_and_churn_sections(self):
        for heading in ("Đổi trả trong 7 ngày", "Khuyến mại Flash Sale", "Khách hàng rời bỏ"):
            self.assertFalse(_matches_requested_navigation_topic("Quy trình mua hàng thế nào?", "Guide", heading))
        self.assertTrue(_matches_requested_navigation_topic("Mua hàng rồi đổi trả thế nào?", "Guide", "Đổi trả"))

    def test_different_heading_or_effective_period_is_not_a_conflict(self):
        self.assertEqual(_numeric_source_disagreements([
            self.chunk("Thời gian xử lý là 12 tháng.", heading="Bảo hành"),
            self.chunk("Thời gian xử lý là 24 tháng.", heading="Hợp đồng", page=2)]), [])
        self.assertEqual(_numeric_source_disagreements([
            self.chunk("Laptop bảo hành 12 tháng.", effective_from="2025-01-01"),
            self.chunk("Laptop bảo hành 24 tháng.", effective_from="2026-01-01", page=2)]), [])

    def test_same_subject_unit_scope_conflict_is_retained(self):
        self.assertEqual(_numeric_source_disagreements([
            self.chunk("Laptop bảo hành 12 tháng."),
            self.chunk("Laptop bảo hành 24 tháng.", page=2)]), [["12", "24"]])

    def test_percent_conflict_remains_detectable(self):
        self.assertEqual(_numeric_source_disagreements([
            self.chunk("Hạn mức chiết khấu là 10%.", heading="Chiết khấu"),
            self.chunk("Hạn mức chiết khấu là 20%.", heading="Chiết khấu", page=2)]), [["10", "20"]])

    def test_empty_risk_list_does_not_prove_safe_inventory(self):
        answer, _ = generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Tồn kho?", [],
            tools_data=[{"tool": "get_stockout_risk_summary", "products_at_risk": [], "unassessed_demand_count": 3}])
        self.assertIn("không đủ căn cứ", answer)
        self.assertIn("3 sản phẩm", answer)
        self.assertNotIn("✅", answer)

    def test_service_counts_answer_includes_each_returned_status(self):
        answer, _ = generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Thống kê dịch vụ theo từng trạng thái", [],
            tools_data=[{"tool": "get_service_ticket_summary", "total_tickets": 3, "open_tickets": 1,
                         "overdue_sla_tickets": 0, "status_distribution": {"OPEN": 1, "CLOSED": 2, "CANCELLED": 0}}])
        for count in ("OPEN: 1", "CLOSED: 2", "CANCELLED: 0"):
            self.assertIn(count, answer)

    def test_category_lookup_failure_is_not_reported_as_workspace_margin(self):
        for status in ("NOT_FOUND", "AMBIGUOUS"):
            with self.subTest(status=status):
                answer, _ = generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Biên lợi nhuận?", [],
                    tools_data=[{"tool": "get_category_profit_margins", "category_filter": "UNKNOWN",
                                 "category_match_status": status, "category_breakdown": []}])
                self.assertIn("mã danh mục chính xác", answer)
                self.assertIn("UNKNOWN", answer)
                self.assertNotIn("Tổng doanh thu", answer)

    def test_gis_and_recommendations_preserve_measured_and_stale_qualifications(self):
        answer, _ = generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Gợi ý?", [], tools_data=[
            {"tool": "query_nearby_technicians", "candidates": [{"name": "TEST", "code": "E1", "score_basis": "0.5 distance + 0.5 workload", "skill_match_verified": False}]},
            {"tool": "get_recommendations", "recommendations": [{"title": "TEST", "review_state": {"stale": True}, "proposed_action": "", "explanation": {}}]}])
        self.assertIn("0.5 distance + 0.5 workload", answer)
        self.assertIn("chưa được xác minh", answer)
        self.assertIn("đã cũ/hết hạn", answer)
        self.assertIn("advisory", answer)
        self.assertNotIn("w_skill=0.2", answer)

    def test_forecast_answer_discloses_historical_snapshot_and_baseline_failure(self):
        answer, _ = generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Dự báo?", [],
            tools_data=[{"tool": "get_forecast", "target_type": "REVENUE", "forecast": [
                {"date": "2025-01-02", "predicted": 10, "lower": 8, "upper": 12}],
                "snapshot": {"message": "Snapshot lịch sử, không phải dự báo hiện tại."},
                "quality": {"message": "Baseline tốt hơn XGBoost.", "r2_warning": "R² âm."}}])
        for message in ("Snapshot lịch sử", "Baseline tốt hơn", "R² âm", "2025-01-02", "không phải khoảng tin cậy 95%"):
            self.assertIn(message, answer)

    def test_unverified_source_cannot_confirm_an_approved_policy(self):
        answer, sources = generate_grounded_answer(SimpleNamespace(name="Audit"), None,
            "Chính sách kinh doanh đã được phê duyệt chưa?", [self.chunk("Bảo hành 24 tháng.",
            source_authority={"academic_only": True, "public_publication_approved": False})])
        self.assertIn("chưa có bằng chứng", answer.lower())
        self.assertIn("24 tháng", answer)
        self.assertFalse(sources[0]["public_publication_approved"])

    def test_provider_receives_authority_boundary_not_a_claim_of_certification(self):
        with override_settings(LLM_API_KEY="simulated-key"), patch(
                "apps.knowledge.services._call_gemini_chat_api", return_value="simulation") as provider:
            generate_grounded_answer(SimpleNamespace(name="Audit"), None, "Chính sách?", [self.chunk("Bảo hành 24 tháng.")])
        self.assertIn("UNVERIFIED", provider.call_args.args[0])


class RepairDeploymentGuards(TestCase):
    def test_full_test_discovery_does_not_register_synthetic_migration_models(self):
        from django.apps import apps
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.questioner import MigrationQuestioner
        from django.db.migrations.state import ProjectState
        from django.test.runner import DiscoverRunner

        # Discovery imports the isolation harness; do not execute another suite.
        DiscoverRunner(verbosity=0).build_suite(["tests"])
        loader = MigrationLoader(None, ignore_no_migrations=True)
        changes = MigrationAutodetector(
            loader.project_state(), ProjectState.from_apps(apps), MigrationQuestioner()
        ).changes(graph=loader.graph)
        self.assertEqual(changes, {}, "Test discovery must not create application migration drift.")
        self.assertNotIn("dummytenantentity", apps.all_models["workspaces"])

    def test_system_checks_and_no_migration_drift(self):
        diagnostics = StringIO()
        call_command("check", stdout=diagnostics)
        self.assertIn("no issues", diagnostics.getvalue())
        diagnostics = StringIO()
        call_command("makemigrations", check=True, dry_run=True, stdout=diagnostics)
        self.assertIn("No changes detected", diagnostics.getvalue())
