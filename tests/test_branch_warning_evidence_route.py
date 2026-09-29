"""Deterministic route regressions, not live model quality measurements."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.knowledge.intent_router import classify_business_intent
from apps.knowledge.tools import explain_root_cause


class BranchWarningEvidenceRouteTests(SimpleTestCase):
    def setUp(self):
        self.workspace = SimpleNamespace(code="retail", workspace_type="RETAIL")

    def test_generic_warning_uses_recorded_recommendations(self):
        route = classify_business_intent(
            "Tại sao chi nhánh bị cảnh báo flagged?", self.workspace
        )
        self.assertIn("get_recommendations", route["tools"])
        self.assertEqual(route["parameters"]["entity_name"], "")

    def test_named_branch_does_not_borrow_workspace_recommendations(self):
        route = classify_business_intent(
            "Vì sao chi nhánh Quận 1 lại bị cảnh báo doanh thu giảm sút?",
            self.workspace,
        )
        self.assertNotIn("get_recommendations", route["tools"])
        self.assertTrue(route["parameters"]["entity_name"])

    def test_missing_evidence_does_not_invent_cause(self):
        result = explain_root_cause(
            self.workspace, None, target_type="BRANCH_WARNING", entity_name="Quận 1"
        )
        self.assertEqual(result["evidence_factors"], [])
        self.assertIn("Chưa có bằng chứng", result["explanation"])
