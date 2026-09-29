"""Scorer regression fixtures, not live RAG quality evidence."""
from unittest import TestCase
from apps.knowledge.evaluation_scoring import score_case, summarize


class RAGScoringTests(TestCase):
    def case(self, **changes):
        result = dict(id='DOC', category='DOCUMENT_ONLY', should_fallback=False,
                      expected_document='Quy chế', expected_keywords=['24 tháng', '30 ngày'])
        result.update(changes)
        return result

    def response(self, **changes):
        result = dict(answer='Bảo hành 24 tháng và đổi trong 30 ngày.',
                      sources=[{'document_title': 'Quy chế'}], tools_used=[])
        result.update(changes)
        return result

    def score(self, case=None, response=None):
        return score_case(case or self.case(), response or self.response(), 'Không có căn cứ.')

    def test_one_keyword_is_not_complete(self):
        row = self.score(response=self.response(answer='24 tháng'))
        self.assertFalse(row['proxy_pass'])
        self.assertEqual(row['missing_keyword_groups'], [['30 ngày']])

    def test_complete_answer_requires_expected_source(self):
        self.assertTrue(self.score()['proxy_pass'])
        for title in ('Khác', 'Quy chế giả mạo'):
            row = self.score(response=self.response(sources=[{'document_title': title}]))
            self.assertFalse(row['retrieval_ok'])
            self.assertFalse(row['proxy_pass'])

    def test_hybrid_requires_both_sources_and_successful_tool(self):
        case = self.case(category='HYBRID', expected_tool='sales')
        for response in (self.response(), self.response(sources=[], tools_used=[{'tool': 'sales', 'status': 'SUCCESS'}]),
                         self.response(tools_used=[{'tool': 'sales', 'status': 'ERROR'}])):
            self.assertFalse(self.score(case, response)['proxy_pass'])
        self.assertTrue(self.score(case, self.response(tools_used=[{'tool': 'sales', 'status': 'SUCCESS'}]))['proxy_pass'])

    def test_phrase_boundaries_reject_wrong_numbers(self):
        self.assertFalse(self.score(response=self.response(answer='124 tháng, 130 ngày'))['proxy_pass'])

    def test_explicit_alternatives_and_normalization(self):
        case = self.case(required_keyword_groups=[['24 tháng', 'hai năm'], ['30 ngày']])
        self.assertTrue(self.score(case, self.response(answer='HAI NĂM và 30   ngày'))['proxy_pass'])

    def test_empty_rubric_does_not_pass(self):
        self.assertFalse(self.score(self.case(expected_keywords=[]))['proxy_pass'])

    def test_refusal_mention_plus_fabrication_does_not_pass(self):
        case = self.case(category='OUT_OF_DOMAIN', should_fallback=True)
        row = self.score(case, self.response(answer='Không có căn cứ. Nhưng giá cổ phiếu là 500.'))
        self.assertFalse(row['proxy_pass'])

    def test_precision_and_recall_have_different_denominators(self):
        ood = self.case(category='OUT_OF_DOMAIN', should_fallback=True)
        refusal = self.response(answer='Không có căn cứ.')
        rows = [self.score(ood, refusal), self.score(response=refusal),
                self.score(ood, self.response()), self.score(ood, self.response())]
        result = summarize(rows)
        self.assertEqual(result['fallback_precision'], 50.0)
        self.assertEqual(result['fallback_recall'], 33.3)
        self.assertEqual(result['fallback_false_positives'], 1)
        self.assertEqual(result['fallback_false_negatives'], 2)
        self.assertEqual(result['lexical_evidence_pass_rate'], 0.0)

    def test_zero_denominators_are_unmeasured(self):
        result = summarize([])
        for key in ('fallback_precision', 'fallback_recall', 'lexical_evidence_pass_rate', 'citation_attribution_rate'):
            self.assertIsNone(result[key])

    def test_semantics_and_provider_not_inferred(self):
        row = self.score(response=self.response(answer='Không bảo hành 24 tháng, không đổi trong 30 ngày.'))
        self.assertTrue(row['proxy_pass'])  # Known lexical limitation, explicitly NOT semantic truth.
        self.assertIsNone(row['semantic_correctness'])
        result = summarize([row])
        self.assertIsNone(result['semantic_correctness_rate'])
        self.assertEqual(result['generation_mode_counts'], {'UNKNOWN': 1})

    def test_declared_contradiction_does_not_pass_lexical_proxy(self):
        case = self.case(forbidden_keyword_groups=[['không bảo hành', 'không đổi']])
        row = self.score(case, self.response(answer='Không bảo hành 24 tháng, nhưng đổi trong 30 ngày.'))
        self.assertTrue(row['contradiction_detected'])
        self.assertEqual(row['matched_forbidden_keyword_groups'], [['không bảo hành', 'không đổi']])
        self.assertFalse(row['proxy_pass'])

    def test_undeclared_contradiction_remains_explicit_limitation(self):
        row = self.score(response=self.response(answer='Không bảo hành 24 tháng, không đổi trong 30 ngày.'))
        self.assertFalse(row['contradiction_detected'])
        self.assertTrue(row['proxy_pass'])

    def test_details_preserve_full_answer_for_review(self):
        answer = '24 tháng 30 ngày ' + 'Nội dung cần kiểm tra. ' * 20
        self.assertEqual(self.score(response=self.response(answer=answer))['answer'], answer)

    def test_citation_rate_excludes_tool_only_cases(self):
        case = dict(id='DATA', category='STRUCTURED_ONLY', should_fallback=False,
                    expected_keywords=['doanh thu'], expected_tool='sales')
        row = self.score(case, self.response(answer='doanh thu', tools_used=[{'tool': 'sales', 'status': 'SUCCESS'}]))
        result = summarize([self.score(), row])
        self.assertEqual(result['citation_cases'], 1)
        self.assertEqual(result['citation_attribution_rate'], 100.0)
