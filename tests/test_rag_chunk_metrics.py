"""Scoring contract tests, not live LLM or retrieval-quality certification."""
from unittest import TestCase
from apps.knowledge.evaluation_scoring import score_case, summarize
from apps.knowledge.evidence_metrics import chunk_metrics


class GoldChunkMetricsTests(TestCase):
    def score(self, ids=None, sources=None):
        case = dict(id='chunk', category='DOCUMENT_ONLY', should_fallback=False,
                    expected_document='Policy', expected_keywords=['24 tháng'])
        if ids is not None:
            case['expected_chunk_ids'] = ids
        return score_case(case, {'answer': '24 tháng', 'sources': sources or []}, 'No evidence')

    def test_correct_title_wrong_chunk_cannot_pass_gold_rubric(self):
        row = self.score([1], [{'document_title': 'Policy', 'chunk_id': 2}])
        self.assertTrue(row['citation_ok'])
        self.assertEqual(row['chunk_recall'], 0)
        self.assertFalse(row['proxy_pass'])

    def test_partial_gold_and_irrelevant_chunks_count(self):
        row = self.score([1, 2], [{'document_title': 'Policy', 'chunk_id': n} for n in (1, 3)])
        self.assertEqual(row['chunk_recall'], .5)
        self.assertEqual(row['chunk_precision'], .5)
        self.assertEqual(row['missing_chunk_ids'], ['2'])
        self.assertFalse(row['proxy_pass'])

    def test_duplicate_citations_do_not_inflate_recall(self):
        row = self.score([1, 2], [{'document_title': 'Policy', 'chunk_id': 1}] * 3)
        self.assertEqual(row['chunk_recall'], .5)
        self.assertEqual(row['chunk_precision'], 1)

    def test_unknown_citation_identity_is_not_discarded_from_precision(self):
        row = self.score([1], [{'document_title': 'Policy', 'chunk_id': 1}, {'document_title': 'Policy'}])
        self.assertEqual(row['chunk_precision'], .5)
        self.assertEqual(row['unidentified_source_count'], 1)

    def test_annotation_absence_is_unmeasured_and_not_inferred_from_sources(self):
        row = self.score(sources=[{'document_title': 'Policy', 'chunk_id': 1}])
        self.assertIsNone(row['chunk_recall'])
        report = summarize([row])
        self.assertEqual(report['chunk_unannotated_cases'], 1)
        self.assertIsNone(report['chunk_recall_macro_percent'])

    def test_macro_denominator_excludes_unannotated_cases(self):
        report = summarize([self.score([1], [{'document_title': 'Policy', 'chunk_id': 1}]),
                            self.score([2], []), self.score()])
        self.assertEqual(report['chunk_annotated_cases'], 2)
        self.assertEqual(report['chunk_recall_macro_percent'], 50)
        self.assertEqual(report['chunk_precision_macro_percent'], 50)

    def test_invalid_gold_is_configuration_error_not_a_pass(self):
        for value in ([], '', [True], [None], [' '], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                chunk_metrics({'expected_chunk_ids': value}, [])

    def test_json_string_ids_match_database_integer_ids(self):
        row = self.score(['1'], [{'document_title': 'Policy', 'chunk_id': 1}])
        self.assertEqual(row['chunk_recall'], 1)
        self.assertTrue(row['proxy_pass'])
        self.assertIsNone(row['semantic_correctness'])
