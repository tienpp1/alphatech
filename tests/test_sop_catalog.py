from pathlib import Path
from unittest import TestCase
from apps.knowledge.sop_catalog import inventory, PRIMARY_SOPS, SUPPLEMENTARY_SOPS
from apps.knowledge.scope_benchmark import (
    REPOSITORY_SCOPE_CASES, APPROVED_SCOPE_CASES, PRIMARY_SCOPE_CASES, SUPPLEMENTARY_SCOPE_CASES,
)


class SOPCatalogTests(TestCase):
    def test_all_repository_sops_classified_once(self):
        root = Path(__file__).resolve().parents[1] / 'data' / 'knowledge'
        files = [row['filename'] for row in inventory()]
        self.assertEqual(len(files), len(set(files)))
        self.assertEqual(set(files), {path.name for path in root.glob('SOP_*.md')})

    def test_inventory_does_not_invent_approval(self):
        for row in inventory():
            self.assertEqual(row['approval_status'], 'UNVERIFIED')
            self.assertFalse(row['public_publication_approved'])

    def test_hr_datacenter_not_primary_academic_cases(self):
        self.assertFalse(any('SOP_CORE_' in name or 'DATACENTER' in name for name in PRIMARY_SOPS))
        self.assertEqual(len(PRIMARY_SOPS) + len(SUPPLEMENTARY_SOPS), 24)

    def test_split_keeps_every_original_case_without_silently_dropping_tests(self):
        self.assertIs(APPROVED_SCOPE_CASES, REPOSITORY_SCOPE_CASES)
        self.assertEqual({case['id'] for case in PRIMARY_SCOPE_CASES},
                         {'SCOPE-RET-RMA-01', 'SCOPE-RET-BOPIS-01', 'SCOPE-SVC-SLA-01'})
        self.assertEqual({case['id'] for case in PRIMARY_SCOPE_CASES + SUPPLEMENTARY_SCOPE_CASES},
                         {case['id'] for case in REPOSITORY_SCOPE_CASES})
