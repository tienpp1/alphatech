from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from apps.approvals.registry import ToolPermissionDenied
from apps.knowledge.services import detect_and_handle_mutation_request, answer_grounded_query, _call_gemini_chat_api
from apps.knowledge.embedding import _call_gemini_embedding_api, _call_openai_embedding_api


class AIErrorBoundaryTests(SimpleTestCase):
    def test_price_action_does_not_swallow_denial_or_execution_failure(self):
        for error in (ToolPermissionDenied('private detail'), RuntimeError('private detail')):
            with self.subTest(error=type(error).__name__), patch('apps.approvals.executor.execute_tool', side_effect=error):
                with self.assertLogs('apps.knowledge.services', level='WARNING') as logs:
                    with self.assertRaises(type(error)):
                        detect_and_handle_mutation_request('điều chỉnh giá sản phẩm 1 thành 20000', None, None)
                self.assertNotIn('private detail', str(logs.output))

    def test_failed_mutation_is_sanitized_and_does_not_become_rag_answer(self):
        for error, code in [(ToolPermissionDenied('private-secret'), 'PERMISSION_DENIED'),
                            (RuntimeError('private-secret'), 'MUTATION_FAILED')]:
            with self.subTest(code=code), patch('apps.knowledge.services.ConversationSession.objects.create', return_value=SimpleNamespace(id=1)), patch('apps.knowledge.services.ChatMessage.objects.create', return_value=SimpleNamespace(id=2)) as messages, patch('apps.knowledge.services.detect_and_handle_mutation_request', side_effect=error), patch('apps.knowledge.services.search_relevant_chunks') as retrieval:
                with self.assertLogs('apps.knowledge.services', level='WARNING') as logs:
                    result = answer_grounded_query(SimpleNamespace(), SimpleNamespace(is_superuser=True), 'action')
                self.assertEqual(result['error'], code)
                self.assertEqual(result['tools_used'][0]['status'], 'FAILED')
                self.assertNotIn('approval_request_id', result)
                self.assertNotIn('private-secret', str(result) + str(messages.call_args_list) + str(logs.output))
                retrieval.assert_not_called()

    def test_provider_fallback_logs_only_fixed_codes(self):
        for module, fn in [('apps.knowledge.embedding', _call_gemini_embedding_api),
                           ('apps.knowledge.embedding', _call_openai_embedding_api),
                           ('apps.knowledge.services', _call_gemini_chat_api)]:
            target = 'apps.knowledge.embedding.open_provider_request' if 'embedding' in module else 'config.provider_http.open_provider_request'
            with self.subTest(provider=fn.__name__), patch(target, side_effect=RuntimeError('sensitive upstream response')):
                with self.assertLogs(module, level='WARNING') as logs:
                    self.assertIsNone(fn('fixture', 'fixture-model', 'fixture-key'))
                self.assertNotIn('sensitive upstream response', str(logs.output))
                self.assertNotIn('fixture-key', str(logs.output))
