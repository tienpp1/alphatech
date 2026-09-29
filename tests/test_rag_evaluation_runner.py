"""Mocked runner checks; no database, provider or conversation writes."""
from types import SimpleNamespace
from unittest.mock import patch
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase
from apps.knowledge.evaluation import run_benchmark_evaluation


class RAGEvaluationRunnerTests(SimpleTestCase):
    def test_workspace_filter_and_parameters(self):
        cases = [dict(id=kind, category='DOCUMENT_ONLY', workspace_type=kind,
                      expected_document='Policy', expected_keywords=['answer'],
                      should_fallback=False, question=kind) for kind in ('RETAIL', 'SERVICE')]
        ws, user = SimpleNamespace(workspace_type='RETAIL'), object()
        with patch('apps.knowledge.evaluation.BENCHMARK_QUESTIONS', cases), patch(
            'apps.knowledge.evaluation.answer_grounded_query',
            return_value={'answer': 'answer', 'sources': [{'document_title': 'Policy'}]}
        ) as query:
            result = run_benchmark_evaluation(ws, user)
        query.assert_called_once_with(workspace=ws, user=user, message='RETAIL')
        self.assertEqual(result['total_evaluated'], 1)
        self.assertEqual(result['lexical_evidence_pass_rate'], 100)
        self.assertIsNone(result['semantic_correctness_rate'])
        self.assertEqual(result['generation_mode_counts'], {'UNKNOWN': 1})

    def test_permission_denial_propagates(self):
        with patch('apps.knowledge.evaluation.answer_grounded_query', side_effect=PermissionDenied):
            with self.assertRaises(PermissionDenied):
                run_benchmark_evaluation(SimpleNamespace(workspace_type='RETAIL'), object())

    def test_provider_failure_not_scored_as_success(self):
        with patch('apps.knowledge.evaluation.answer_grounded_query', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                run_benchmark_evaluation(SimpleNamespace(workspace_type='RETAIL'), object())

    def test_capture_errors_records_sanitized_case_timing(self):
        cases = [dict(id='ERR-01', category='DOCUMENT_ONLY', workspace_type='RETAIL',
                      expected_document='Policy', expected_keywords=['answer'],
                      should_fallback=False, question='question')]
        with patch('apps.knowledge.evaluation.BENCHMARK_QUESTIONS', cases), patch(
            'apps.knowledge.evaluation.answer_grounded_query', side_effect=TimeoutError
        ):
            result = run_benchmark_evaluation(
                SimpleNamespace(workspace_type='RETAIL'), object(), capture_errors=True
            )
        self.assertEqual(result['total_evaluated'], 1)
        self.assertEqual(result['scored_cases'], 0)
        self.assertEqual(result['error_cases'], 1)
        detail = result['details'][0]
        self.assertEqual(detail['status'], 'ERROR')
        self.assertEqual(detail['error_code'], 'PROVIDER_TIMEOUT')
        self.assertIsInstance(detail['evaluated_at'], str)
        self.assertGreaterEqual(detail['duration_ms'], 0)
        self.assertNotIn('TimeoutError', str(detail))
