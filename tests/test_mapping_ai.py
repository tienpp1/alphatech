"""
Unit & Integration tests for AI-Assisted Mapping Suggestions.
Verifies recommendation mode ONLY, confidence scoring, reasoning,
and mandatory human confirmation requirement.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.services import create_mapping_profile, add_mapping_rule
from apps.mapping.engine.transformer import transform_single_record
from apps.mapping.ai_suggester import suggest_mappings_for_fields


class MappingAITestCase(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name="Retail AI", code="retail-ai", workspace_type=WorkspaceType.RETAIL)
        self.user = User.objects.create_user(username="ai_tester", email="aitest@example.com")
        self.role_admin = Role.objects.create(name="ADMIN")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.user, role=self.role_admin, is_default=True)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_ai_suggestion_generation(self):
        """Verifies AI suggester recognizes common Vietnamese aliases with high confidence."""
        source_cols = ["tong_thanh_toan", "ma_khach_hang", "ngay_dat_hang"]
        sample_vals = {
            "tong_thanh_toan": ["1.500.000 đ", "2.000.000 đ"],
            "ma_khach_hang": ["CUST-001", "CUST-002"],
            "ngay_dat_hang": ["2026-08-25", "2026-08-26"],
        }
        inferred = {
            "tong_thanh_toan": "DECIMAL",
            "ma_khach_hang": "STRING",
            "ngay_dat_hang": "DATE",
        }

        suggestions = suggest_mappings_for_fields(
            source_columns=source_cols,
            target_entity="Order",
            sample_values=sample_vals,
            inferred_types=inferred,
        )

        self.assertTrue(len(suggestions) >= 3)
        targets = {s["suggested_target_field"]: s for s in suggestions}

        money_field = "total_amount" if "total_amount" in targets else "revenue"
        self.assertIn(money_field, targets)
        self.assertGreaterEqual(targets[money_field]["confidence"], 0.90)
        self.assertEqual(targets[money_field]["ai_status"], AIConfirmationStatus.PENDING)

        self.assertIn("customer_id", targets)
        self.assertGreaterEqual(targets["customer_id"]["confidence"], 0.90)

    def test_ai_rule_requires_human_confirmation(self):
        """Verifies pending AI rules are not applied until explicitly accepted."""
        profile = create_mapping_profile(self.workspace, self.user, "AI Test Profile", "Order")
        rule = add_mapping_rule(
            profile=profile,
            user=self.user,
            source_field="tong_tien",
            target_field="revenue",
            rule_type=RuleType.AI_ASSISTED_MAPPING,
            confidence_score=0.94,
            ai_status=AIConfirmationStatus.PENDING,
        )

        raw = {"tong_tien": "1500000"}
        # Prior to human acceptance: pending AI rule is ignored
        canonical, errors = transform_single_record(raw, [rule], target_entity="Order")
        self.assertNotIn("revenue", canonical)

        # After human acceptance: rule transforms value
        rule.ai_status = AIConfirmationStatus.ACCEPTED
        rule.save()
        canonical, errors = transform_single_record(raw, [rule], target_entity="Order")
        self.assertIn("revenue", canonical)
        self.assertEqual(canonical["revenue"], "1500000")

    def test_ai_suggest_api_endpoint(self):
        """Tests POST /api/v1/mapping/ai-suggest/ endpoint."""
        url = "/api/v1/mapping/ai-suggest/"
        payload = {
            "target_entity": "Customer",
            "source_columns": ["ho_ten", "so_dien_thoai", "dia_chi_nha"],
            "sample_values": {
                "ho_ten": ["Tran Van C"],
                "so_dien_thoai": ["0912345678"],
                "dia_chi_nha": ["456 Le Loi, Q1"],
            },
        }

        resp = self.client.post(url, payload, format="json", HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        self.assertGreater(resp.data["total_suggestions"], 0)
        self.assertIn("AI suggestions are advisory", resp.data["notice"])
