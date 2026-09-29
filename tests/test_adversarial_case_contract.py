"""Validate acceptance inputs only; does not certify assistant behavior."""
from django.test import SimpleTestCase
from apps.knowledge.adversarial_cases import ADVERSARIAL_CASES


class AdversarialCaseContractTests(SimpleTestCase):
    def test_required_scenarios_have_actor_fixture_and_expected_behavior(self):
        self.assertEqual(len({case['id'] for case in ADVERSARIAL_CASES}), len(ADVERSARIAL_CASES))
        self.assertEqual({case['kind'] for case in ADVERSARIAL_CASES},
            {'paraphrase', 'missing_data', 'conflicting_documents', 'missing_permission', 'wrong_workspace'})
        for case in ADVERSARIAL_CASES:
            self.assertTrue(case['workspace'])
            self.assertTrue(case['actor'])
            self.assertTrue(case['questions'])
            self.assertTrue(case['expected'])
            self.assertIsNone(case['automatic_semantic_pass'])
        conflict = next(case for case in ADVERSARIAL_CASES if case['kind'] == 'conflicting_documents')
        self.assertEqual(len(conflict['documents']), 2)
        self.assertIn('12 tháng', conflict['documents'][0]['text'])
        self.assertIn('24 tháng', conflict['documents'][1]['text'])
