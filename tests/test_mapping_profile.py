"""
Unit tests for MappingProfile & MappingRule CRUD, Ordering, and Discovery.
"""

from django.test import TestCase
from django.db import IntegrityError
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.integration.models import DataSource, SourceType, ImportJob, RawImportRecord
from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    discover_source_fields,
)


class MappingProfileTestCase(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Retail Corp",
            code="retail-corp",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.user = User.objects.create_user(username="mapper_user", email="mapper@example.com")
        self.role_admin = Role.objects.create(name="ADMIN")
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=self.role_admin,
            is_default=True,
        )

        self.data_source = DataSource.objects.create(
            workspace=self.workspace,
            name="Test CSV Source",
            source_type=SourceType.CSV,
        )

    def test_create_mapping_profile(self):
        """Tests successful profile creation."""
        profile = create_mapping_profile(
            workspace=self.workspace,
            user=self.user,
            name="Orders CSV Profile",
            target_entity="Order",
            data_source=self.data_source,
            description="Test description",
        )
        self.assertEqual(profile.name, "Orders CSV Profile")
        self.assertEqual(profile.target_entity, "Order")
        self.assertEqual(profile.workspace, self.workspace)
        self.assertEqual(profile.active_rules_count, 0)

    def test_unique_workspace_profile_name(self):
        """Verifies duplicate profile names in same workspace raise ValueError or IntegrityError."""
        create_mapping_profile(
            workspace=self.workspace,
            user=self.user,
            name="Duplicate Profile",
            target_entity="Order",
        )
        with self.assertRaises(ValueError):
            create_mapping_profile(
                workspace=self.workspace,
                user=self.user,
                name="Duplicate Profile",
                target_entity="Customer",
            )

    def test_add_and_order_rules(self):
        """Tests adding rules and verifying execution ordering."""
        profile = create_mapping_profile(
            workspace=self.workspace,
            user=self.user,
            name="Customer Mapping",
            target_entity="Customer",
        )

        r2 = add_mapping_rule(
            profile=profile,
            user=self.user,
            source_field="ten_kh",
            target_field="name",
            rule_type=RuleType.FIELD_MAPPING,
            order=2,
        )
        r1 = add_mapping_rule(
            profile=profile,
            user=self.user,
            source_field="ma_kh",
            target_field="customer_id",
            rule_type=RuleType.FIELD_MAPPING,
            order=1,
        )

        ordered_rules = list(profile.rules.all())
        self.assertEqual(ordered_rules[0].id, r1.id)
        self.assertEqual(ordered_rules[1].id, r2.id)

    def test_field_discovery(self):
        """Tests discovery of columns and sample values from staged import job."""
        job = ImportJob.objects.create(
            workspace=self.workspace,
            data_source=self.data_source,
            total_rows=2,
        )
        RawImportRecord.objects.create(
            workspace=self.workspace,
            import_job=job,
            row_number=1,
            raw_data={"so_hd": "HD01", "tong_tien": "1.500.000 đ", "ngay": "25/08/2026"},
        )
        RawImportRecord.objects.create(
            workspace=self.workspace,
            import_job=job,
            row_number=2,
            raw_data={"so_hd": "HD02", "tong_tien": "2.000.000 đ", "ngay": "26/08/2026"},
        )

        disc = discover_source_fields(import_job=job)
        self.assertEqual(disc["total_staged_rows"], 2)
        self.assertIn("so_hd", disc["columns"])
        self.assertIn("tong_tien", disc["columns"])
        self.assertEqual(disc["column_stats"]["tong_tien"]["inferred_type"], "DECIMAL")
