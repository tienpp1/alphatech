"""Contract checks for the independent, human-authored RAG benchmark set."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.knowledge.evaluation import BENCHMARK_QUESTIONS, run_benchmark_evaluation
from apps.knowledge.independent_benchmark import INDEPENDENT_BENCHMARK_QUESTIONS
from apps.knowledge.services import FALLBACK_NO_CONTEXT_MESSAGE


class IndependentRAGDatasetTests(SimpleTestCase):
    def test_dataset_is_distinct_and_complete(self):
        primary_questions = {row["question"] for row in BENCHMARK_QUESTIONS}
        ids = [row["id"] for row in INDEPENDENT_BENCHMARK_QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(row["id"].startswith("IND-") for row in INDEPENDENT_BENCHMARK_QUESTIONS))
        self.assertTrue(all(row["question"] not in primary_questions for row in INDEPENDENT_BENCHMARK_QUESTIONS))
        self.assertTrue(any(row["category"] == "HYBRID" for row in INDEPENDENT_BENCHMARK_QUESTIONS))
        self.assertTrue(any(row["should_fallback"] for row in INDEPENDENT_BENCHMARK_QUESTIONS))
        self.assertTrue(all(FALLBACK_NO_CONTEXT_MESSAGE in row["expected_keywords"]
                            for row in INDEPENDENT_BENCHMARK_QUESTIONS if row["should_fallback"]))

    def test_runner_accepts_independent_cases_without_changing_primary_rubric(self):
        case = INDEPENDENT_BENCHMARK_QUESTIONS[0]
        response = {
            "answer": "Bảo hành 24 tháng và hỗ trợ 1 đổi 1.",
            "sources": [{"document_title": case["expected_document"]}],
            "tools_used": [],
        }
        with patch("apps.knowledge.evaluation.answer_grounded_query", return_value=response) as query:
            result = run_benchmark_evaluation(
                SimpleNamespace(workspace_type="RETAIL"), object(), cases=[case]
            )
        self.assertEqual(query.call_args.kwargs["message"], case["question"])
        self.assertEqual(result["total_evaluated"], 1)
        self.assertEqual(result["lexical_evidence_pass_rate"], 100.0)
        self.assertIsNone(result["semantic_correctness_rate"])
