from unittest import TestCase
from apps.knowledge.evidence_metrics import numeric_fact_metrics
from apps.knowledge.evaluation_scoring import score_case, summarize


class NumericFactMetricsTests(TestCase):
    def rubric(self):
        return {'required_numeric_facts': [{'id': 'warranty', 'expected': '24',
                'pattern': r'bảo hành\s+(?P<value>\d+(?:\.\d+)?)\s+tháng'}]}

    def test_correct_number_and_leading_zero(self):
        for answer in ('Bảo hành 24 tháng.', 'BẢO HÀNH 024 tháng.'):
            self.assertTrue(numeric_fact_metrics(self.rubric(), answer)['numeric_facts_ok'])

    def test_wrong_missing_and_conflicting_values_fail(self):
        for answer in ('Bảo hành 12 tháng.', '24 tháng', 'Bảo hành 24 tháng. Bảo hành 12 tháng.'):
            with self.subTest(answer=answer):
                self.assertFalse(numeric_fact_metrics(self.rubric(), answer)['numeric_facts_ok'])

    def test_numbers_in_unrelated_fact_do_not_satisfy_rubric(self):
        self.assertFalse(numeric_fact_metrics(self.rubric(), 'Giao hàng 24 tháng. Bảo hành 12 tháng.')['numeric_facts_ok'])

    def test_unannotated_is_not_assumed_correct(self):
        self.assertIsNone(numeric_fact_metrics({}, '24 tháng')['numeric_facts_ok'])

    def test_invalid_rubric_rejected(self):
        for fact in ({'id': 'x', 'expected': 'NaN', 'pattern': '(?P<value>.*)'},
                     {'id': 'x', 'expected': '24', 'pattern': '24'},
                     {'id': 'x', 'expected': '24', 'pattern': '['}):
            with self.subTest(fact=fact), self.assertRaises(ValueError):
                numeric_fact_metrics({'required_numeric_facts': [fact]}, '24')

    def test_wrong_quantity_blocks_otherwise_complete_lexical_proxy(self):
        case = dict(id='n', category='DOCUMENT_ONLY', expected_document='Policy',
                    expected_keywords=['bảo hành'], should_fallback=False, **self.rubric())
        row = score_case(case, {'answer': 'Bảo hành 12 tháng.',
                        'sources': [{'document_title': 'Policy'}]}, 'No evidence')
        self.assertTrue(row['lexical_complete'])
        self.assertFalse(row['proxy_pass'])
        self.assertEqual(summarize([row])['annotated_numeric_pass_rate'], 0)
        self.assertIsNone(row['semantic_correctness'])

    def test_negation_remains_explicit_semantic_limitation(self):
        result = numeric_fact_metrics(self.rubric(), 'Không bảo hành 24 tháng.')
        self.assertTrue(result['numeric_facts_ok'])  # Quantity occurrence only, NOT truth.
