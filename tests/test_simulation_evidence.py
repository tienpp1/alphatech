"""Deterministic what-if evidence; does not evaluate live LLM quality."""
from unittest.mock import patch
from django.test import TestCase, override_settings
from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.service_ops.models import Employee
from apps.knowledge.tools import simulate_what_if_scenario, ToolPermissionDenied
from apps.knowledge.services import generate_grounded_answer


class SimulationEvidenceTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code="sim", name="Simulation", workspace_type="RETAIL")
        self.other = Workspace.objects.create(code="other-sim", name="Other", workspace_type="RETAIL")
        self.user = User.objects.create_user(username="sim", email="sim@example.com")
        role = Role.objects.create(name="SIM_READER")
        for code in ("retail.view_order", "retail.view_product", "service.view_request"):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split('.')[0]})
            role.permissions.add(permission)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=role)

    @override_settings(LLM_API_KEY="test-placeholder")
    @patch("apps.knowledge.services._call_gemini_chat_api")
    def test_all_scenarios_keep_labels_without_llm_rewrite(self, provider):
        for scenario in ("REVENUE_CHANGE", "STOCK_DEPLETION", "TICKET_VOLUME_CHANGE"):
            with self.subTest(scenario=scenario):
                data = simulate_what_if_scenario(self.ws, self.user, scenario_type=scenario)
                answer, _ = generate_grounded_answer(self.ws, self.user, "Giả định", [], [data])
                self.assertTrue(data["is_simulation"])
                self.assertIn("MÔ PHỎNG / GIẢ ĐỊNH", answer)
                self.assertIn("không phải dự báo đã kiểm chứng", answer)
                self.assertIn("không thay đổi dữ liệu thật", answer)
        provider.assert_not_called()

    def test_stock_demand_is_explicit_assumption(self):
        data = simulate_what_if_scenario(self.ws, self.user, scenario_type="STOCK_DEPLETION", param_value=10)
        self.assertEqual(data["estimated_days_to_stockout"], 5)
        self.assertIn("nhu cầu giả định cố định", data["impact_analysis"])
        self.assertIn("không lấy từ lịch sử", data["impact_analysis"])

    def test_no_invented_technician_or_cross_workspace_count(self):
        Employee.objects.create(workspace=self.other, code="E1", full_name="Other")
        data = simulate_what_if_scenario(self.ws, self.user, scenario_type="TICKET_VOLUME_CHANGE")
        self.assertEqual(data["active_technicians"], 0)
        self.assertIsNone(data["simulated_workload_per_tech"])
        self.assertIn("chưa thể tính", data["impact_analysis"])

    def test_foreign_workspace_denied_for_every_scenario(self):
        for scenario in ("REVENUE_CHANGE", "STOCK_DEPLETION", "TICKET_VOLUME_CHANGE"):
            with self.subTest(scenario=scenario), self.assertRaises(ToolPermissionDenied):
                simulate_what_if_scenario(self.other, self.user, scenario_type=scenario)
