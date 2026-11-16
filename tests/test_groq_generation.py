"""Simulated transport contracts, not live-model quality evidence."""
import io
import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, TestCase, override_settings
from apps.knowledge.services import generate_grounded_answer, FALLBACK_NO_CONTEXT_MESSAGE
from apps.knowledge.embedding import get_embedding


class Response(io.BytesIO):
    status = 200


def completion(content='Doanh thu 100 VND từ 1 đơn, nguồn get_sales_summary.', **updates):
    data = {
        'id': 'chatcmpl-fixture', 'object': 'chat.completion', 'created': 1,
        'model': 'openai/gpt-oss-120b',
        'choices': [{'index': 0, 'finish_reason': 'stop',
                     'message': {'role': 'assistant', 'content': content}}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
    }
    data.update(updates)
    return json.dumps(data).encode()


@override_settings(LLM_GENERATION_PROVIDER='groq', GROQ_API_KEY='fixture-groq-only',
                   GROQ_MODEL='openai/gpt-oss-120b', LLM_API_KEY='')
class GroqGenerationTests(SimpleTestCase):
    def generate(self, query='Doanh thu?', facts=None, chunks=None):
        metadata = {}
        if facts is None:
            facts = [{'tool': 'get_sales_summary', 'total_revenue': '100 VND',
                      'total_orders': 1, 'completed_orders': 1}]
        answer, sources = generate_grounded_answer(
            SimpleNamespace(name='Fixture'), None, query, chunks or [],
            tools_data=facts, generation_metadata=metadata)
        return answer, sources, metadata

    def test_groq_sends_chat_only_to_fixed_https_host_with_bounded_output(self):
        requests = []
        def transport(request, **kwargs):
            requests.append((request, kwargs))
            return Response(completion())
        with patch('config.provider_http.open_provider_request', side_effect=transport):
            answer, _, meta = self.generate()
        self.assertEqual(meta, {'mode': 'LLM_RESPONSE', 'provider': 'groq',
                               'model': 'openai/gpt-oss-120b', 'reason': None})
        self.assertIn('100 VND', answer)
        self.assertEqual(len(requests), 1)
        req, options = requests[0]
        self.assertEqual(req.full_url, 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(req.get_header('Authorization'), 'Bearer fixture-groq-only')
        self.assertEqual(req.get_header('User-agent'), 'AlphaTech/1.0')
        self.assertEqual(options, {'allowed_hosts': {'api.groq.com'}, 'timeout': 12})
        payload = json.loads(req.data)
        self.assertEqual(payload['model'], 'openai/gpt-oss-120b')
        self.assertEqual(payload['max_completion_tokens'], 1024)
        self.assertEqual(payload['reasoning_effort'], 'low')
        self.assertIs(payload['include_reasoning'], False)
        self.assertIs(payload['stream'], False)
        self.assertNotIn('tools', payload)
        self.assertNotIn('fixture-groq-only', json.dumps(payload) + str(meta))

    def test_success_preserves_document_citations(self):
        chunks = [{'document_title': 'Hướng dẫn thử nghiệm', 'chunk_id': 8,
                   'similarity': .9, 'content': 'Đơn hàng được kiểm tra trước khi duyệt.'}]
        with patch('config.provider_http.open_provider_request', return_value=Response(completion())):
            _, sources, meta = self.generate(chunks=chunks)
        self.assertEqual(meta['provider'], 'groq')
        self.assertEqual(sources[0]['chunk_id'], 8)
        self.assertEqual(sources[0]['document_title'], 'Hướng dẫn thử nghiệm')

    def test_no_evidence_never_calls_groq(self):
        with patch('config.provider_http.open_provider_request') as transport:
            answer, sources, meta = self.generate(facts=[])
        self.assertEqual(answer, FALLBACK_NO_CONTEXT_MESSAGE)
        self.assertEqual(sources, [])
        self.assertEqual(meta['reason'], 'NO_EVIDENCE')
        transport.assert_not_called()

    def test_simulation_is_not_rewritten_by_live_model(self):
        with patch('config.provider_http.open_provider_request') as transport:
            _, _, meta = self.generate(facts=[{'tool': 'simulate_what_if_scenario'}])
        self.assertEqual(meta['mode'], 'DETERMINISTIC')
        self.assertEqual(meta['reason'], 'SIMULATION')
        transport.assert_not_called()

    @override_settings(GROQ_API_KEY='', LLM_API_KEY='legacy-key-must-not-be-used')
    def test_missing_groq_key_never_uses_legacy_gemini_key(self):
        with patch('config.provider_http.open_provider_request') as transport:
            answer, _, meta = self.generate()
        self.assertIn('100 VND', answer)
        self.assertEqual(meta['reason'], 'NO_API_KEY')
        transport.assert_not_called()

    def test_network_failures_fall_back_without_second_provider_or_secret_logs(self):
        failures = [TimeoutError('fixture-groq-only'),
                    HTTPError('https://api.groq.com', 429, 'fixture-groq-only', {}, None)]
        for failure in failures:
            with self.subTest(error=type(failure).__name__), \
                 patch('config.provider_http.open_provider_request', side_effect=failure) as transport, \
                 self.assertLogs('apps.knowledge.groq_generation', level='WARNING') as logs:
                answer, _, meta = self.generate()
            self.assertIn('100 VND', answer)
            self.assertEqual(meta['mode'], 'DETERMINISTIC')
            self.assertEqual(meta['reason'], 'PROVIDER_UNAVAILABLE')
            self.assertIsNone(meta['model'])
            self.assertEqual(transport.call_count, 1)
            self.assertNotIn('fixture-groq-only', str(logs.output))

    def test_untrusted_provider_responses_fall_back(self):
        truncated = json.loads(completion())
        truncated['choices'][0]['finish_reason'] = 'length'
        tool_call = json.loads(completion())
        tool_call['choices'][0]['message']['tool_calls'] = [{'id': 'x', 'type': 'function'}]
        refused = json.loads(completion())
        refused['choices'][0]['message']['refusal'] = 'Refused'
        for raw in [b'not-json', b'[]', b'{}', completion(''), completion(' '),
                    completion(model='different-model'), json.dumps(truncated).encode(),
                    json.dumps(tool_call).encode(), json.dumps(refused).encode(),
                    completion(content={'text': 'not a string'}), b' ' * 65537]:
            with self.subTest(raw=raw[:35]), patch(
                    'config.provider_http.open_provider_request', return_value=Response(raw)):
                answer, _, meta = self.generate()
            self.assertIn('100 VND', answer)
            self.assertEqual(meta['mode'], 'DETERMINISTIC')
            self.assertEqual(meta['reason'], 'PROVIDER_UNAVAILABLE')

    def test_sensitive_text_is_blocked_before_socket(self):
        for query in ['Email demo@example.test', 'Gọi 0901234567',
                      'password=not-for-export', 'Mật khẩu: not-for-export',
                      'gsk_abcdefghijklmnopqrstuvwxyz0123456789']:
            with self.subTest(query=query), patch('config.provider_http.open_provider_request') as transport:
                answer, _, meta = self.generate(query=query)
            self.assertIn('100 VND', answer)
            self.assertEqual(meta['reason'], 'SENSITIVE_CONTEXT')
            transport.assert_not_called()

    def test_sensitive_document_title_and_source_metadata_are_not_exported(self):
        for values in [{'document_title': 'demo@example.test'},
                       {'source_authority': {'apiKey': 'do-not-export'}}]:
            chunk = {'document_title': 'Fixture', 'chunk_id': 5, 'similarity': 1,
                     'content': 'Đơn được quản lý kiểm tra.'}
            chunk.update(values)
            with self.subTest(field=list(values)), patch('config.provider_http.open_provider_request') as transport:
                _, sources, meta = self.generate(chunks=[chunk])
            self.assertEqual(meta['reason'], 'SENSITIVE_CONTEXT')
            self.assertEqual(sources[0]['chunk_id'], 5)
            transport.assert_not_called()

    def test_personal_tool_fields_are_blocked_even_without_email_or_phone(self):
        for field in ['customer_name', 'technician_name', 'employee_name', 'full_name',
                      'assigned_to', 'assigned_technician', 'customer_id']:
            with self.subTest(field=field), patch('config.provider_http.open_provider_request') as transport:
                facts = [{'tool': 'get_sales_summary', 'total_revenue': '100 VND',
                          'total_orders': 1, 'completed_orders': 1, 'detail': [{field: 'Fixture Person'}]}]
                _, _, meta = self.generate(facts=facts)
            self.assertEqual(meta['reason'], 'SENSITIVE_CONTEXT')
            transport.assert_not_called()

    def test_prefixed_credentials_are_not_exported_from_query_document_or_structure(self):
        for field in ['DB_PASSWORD', 'GROQ_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'clientSecret']:
            for location in ['query', 'document', 'facts']:
                query = 'Doanh thu?'
                chunks, facts = [], None
                if location == 'query':
                    query = field + '=synthetic-sensitive'
                elif location == 'document':
                    chunks = [{'document_title': 'Fixture', 'chunk_id': 6, 'similarity': 1,
                               'content': field + '=synthetic-sensitive'}]
                else:
                    facts = [{'tool': 'fixture', 'nested': [{field: 'synthetic-sensitive'}]}]
                with self.subTest(field=field, location=location), patch(
                        'config.provider_http.open_provider_request', return_value=Response(completion())) as transport:
                    _, _, meta = self.generate(query=query, chunks=chunks, facts=facts)
                self.assertEqual(meta['reason'], 'SENSITIVE_CONTEXT')
                transport.assert_not_called()

    def test_prompt_budget_falls_back_instead_of_silently_losing_evidence(self):
        with patch('config.provider_http.open_provider_request') as transport:
            answer, _, meta = self.generate(query='x' * 8001)
        self.assertIn('100 VND', answer)
        self.assertEqual(meta['reason'], 'CONTEXT_TOO_LARGE')
        transport.assert_not_called()

    @override_settings(GROQ_MODEL='unapproved-model')
    def test_unapproved_model_is_not_sent_to_provider(self):
        with patch('config.provider_http.open_provider_request') as transport:
            _, _, meta = self.generate()
        self.assertEqual(meta['reason'], 'UNSUPPORTED_MODEL')
        transport.assert_not_called()

    def test_groq_key_does_not_change_embedding_space(self):
        before_meta, after_meta = {}, {}
        with override_settings(GROQ_API_KEY='', LLM_GENERATION_PROVIDER='gemini'):
            before = get_embedding('bảo hành', dimension=32, metadata=before_meta)
        with patch('config.provider_http.open_provider_request') as transport:
            after = get_embedding('bảo hành', dimension=32, metadata=after_meta)
        self.assertEqual(before, after)
        self.assertEqual(before_meta, after_meta)
        self.assertEqual(after_meta['reason'], 'NO_API_KEY')
        transport.assert_not_called()

    @override_settings(LLM_API_KEY='legacy-embedding-only', LLM_PROVIDER='gemini')
    def test_legacy_embeddings_never_receive_groq_key(self):
        with patch('apps.knowledge.embedding._call_gemini_embedding_api', return_value=[1., 0.]) as provider:
            get_embedding('kiểm thử')
        self.assertEqual(provider.call_args.args[2], 'legacy-embedding-only')


@override_settings(LLM_API_KEY='', GROQ_API_KEY='fixture-only', LLM_GENERATION_PROVIDER='groq')
class GroqRetrievalIsolationTests(TestCase):
    def test_public_identity_cannot_invoke_internal_generation(self):
        from apps.accounts.models import User
        user = User.objects.create_user(username='groq-public', password='test-only')
        self.client.force_login(user)
        with patch('config.provider_http.open_provider_request') as transport:
            response = self.client.post('/api/v1/ai/chat/', {'message': 'Doanh thu?'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(user.workspace_memberships.exists())
        transport.assert_not_called()

    def test_google_linked_superuser_still_cannot_invoke_internal_generation(self):
        from apps.accounts.models import User
        from apps.public_web.models import SocialIdentity
        user = User.objects.create_superuser('groq-google', 'fixture@example.test', 'test-only')
        SocialIdentity.objects.create(user=user, provider='GOOGLE', subject='groq-fixture',
                                      provider_email=user.email)
        self.client.force_login(user)
        with patch('config.provider_http.open_provider_request') as transport:
            response = self.client.post('/api/v1/ai/chat/', {'message': 'Doanh thu?'})
        self.assertEqual(response.status_code, 403)
        transport.assert_not_called()

    def test_public_copilot_does_not_use_internal_groq_transport(self):
        with patch('config.provider_http.open_provider_request') as transport:
            response = self.client.post('/api/v1/public/copilot/',
                data=json.dumps({'message': 'Doanh thu và lợi nhuận nội bộ là bao nhiêu?'}),
                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()['reply'], str)
        transport.assert_not_called()

    def test_enabling_chat_does_not_change_retrieval_threshold_or_documents(self):
        from apps.workspaces.models import Workspace
        from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk
        from apps.knowledge.retrieval import search_relevant_chunks
        ws = Workspace.objects.create(code='groq-isolation', name='Fixture', workspace_type='RETAIL')
        kb = KnowledgeBase.objects.create(workspace=ws, name='Fixture')
        doc = Document.objects.create(workspace=ws, knowledge_base=kb,
                                      title='Fixture', file_type='TXT', status='READY')
        provenance = {}
        vector = get_embedding('bảo hành', metadata=provenance)
        chunk = DocumentChunk.objects.create(workspace=ws, document=doc, chunk_index=0,
            content='bảo hành', embedding=vector, metadata={'embedding_provenance': provenance})
        before, after = {}, {}
        with override_settings(GROQ_API_KEY='', LLM_GENERATION_PROVIDER='gemini'):
            before_results = search_relevant_chunks(ws, 'bảo hành', metadata=before)
        with patch('config.provider_http.open_provider_request') as transport:
            after_results = search_relevant_chunks(ws, 'bảo hành', metadata=after)
        self.assertEqual([r['chunk_id'] for r in before_results], [chunk.pk])
        self.assertEqual([r['chunk_id'] for r in after_results], [chunk.pk])
        self.assertEqual(before, after)
        transport.assert_not_called()
