"""Provider results here are simulations, never live-model quality evidence."""
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.knowledge.embedding import get_embedding, get_embeddings_batch


class EmbeddingProvenanceTests(SimpleTestCase):
    @override_settings(LLM_API_KEY='')
    def test_offline_records_actual_projection_not_configured_model(self):
        metadata = {'stale': 'value'}
        vector = get_embedding('kiểm thử', dimension=32, metadata=metadata)
        self.assertEqual(len(vector), 32)
        self.assertEqual(metadata, dict(mode='DETERMINISTIC', provider=None,
            model='hash-projection-v1', dimension=32, reason='NO_API_KEY'))

    @override_settings(LLM_API_KEY='fixture-secret', LLM_PROVIDER='gemini', EMBEDDING_MODEL='fixture-model')
    @patch('apps.knowledge.embedding._call_gemini_embedding_api', return_value=[0.6, 0.8])
    def test_provider_success_records_returned_dimension(self, provider):
        metadata = {}
        self.assertEqual(get_embedding('sample', metadata=metadata), [0.6, 0.8])
        self.assertEqual(metadata, dict(mode='PROVIDER', provider='gemini',
            model='fixture-model', dimension=2, reason=None))
        self.assertNotIn('fixture-secret', str(metadata))

    @override_settings(LLM_API_KEY='fixture-secret', LLM_PROVIDER='openai', EMBEDDING_MODEL='fixture-model')
    @patch('apps.knowledge.embedding._call_openai_embedding_api', return_value=[1.0, 0.0])
    def test_openai_simulation_records_provider(self, provider):
        metadata = {}
        get_embedding('sample', metadata=metadata)
        self.assertEqual(metadata['provider'], 'openai')
        self.assertEqual(metadata['model'], 'fixture-model')

    @override_settings(LLM_API_KEY='fixture-secret', LLM_PROVIDER='gemini')
    @patch('apps.knowledge.embedding._call_gemini_embedding_api', return_value=None)
    def test_failed_provider_is_not_reported_as_model_success(self, provider):
        metadata = {}
        get_embedding('sample', dimension=16, metadata=metadata)
        self.assertEqual(metadata['reason'], 'PROVIDER_UNAVAILABLE')
        self.assertEqual(metadata['mode'], 'DETERMINISTIC')
        self.assertIsNone(metadata['provider'])

    @override_settings(LLM_API_KEY='fixture-secret', LLM_PROVIDER='unsupported')
    def test_unsupported_provider_is_explicit(self):
        metadata = {}
        get_embedding('sample', metadata=metadata)
        self.assertEqual(metadata['reason'], 'UNSUPPORTED_PROVIDER')

    @override_settings(LLM_API_KEY='fixture-secret', LLM_PROVIDER='gemini')
    @patch('apps.knowledge.embedding._call_gemini_embedding_api', side_effect=[[1.0, 0.0], None])
    def test_mixed_batch_records_each_result_independently(self, provider):
        observations = []
        vectors = get_embeddings_batch(['first', 'second'], dimension=16, metadata=observations)
        self.assertEqual([len(vector) for vector in vectors], [2, 16])
        self.assertEqual([item['mode'] for item in observations], ['PROVIDER', 'DETERMINISTIC'])
