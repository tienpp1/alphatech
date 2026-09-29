"""Compatibility gate using stored vectors, not a semantic benchmark."""
from unittest.mock import patch
from django.test import TestCase, override_settings
from apps.workspaces.models import Workspace
from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk
from apps.knowledge.embedding import get_embedding
from apps.knowledge.retrieval import search_relevant_chunks


@override_settings(LLM_API_KEY='')
class EmbeddingSpaceIsolationTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code='vector-space', name='Fixture', workspace_type='RETAIL')
        kb = KnowledgeBase.objects.create(workspace=self.ws, name='Fixture')
        doc = Document.objects.create(workspace=self.ws, knowledge_base=kb,
            title='Fixture', file_type='TXT', status='READY')
        self.provenance = {}
        self.vector = get_embedding('bảo hành', metadata=self.provenance)
        self.chunk = DocumentChunk.objects.create(workspace=self.ws, document=doc,
            chunk_index=0, content='bảo hành', embedding=self.vector,
            metadata={'embedding_provenance': self.provenance})

    def search(self):
        metadata = {}
        result = search_relevant_chunks(self.ws, 'bảo hành', threshold=0, metadata=metadata)
        return result, metadata

    def test_matching_projection_is_searchable(self):
        results, metadata = self.search()
        self.assertEqual(len(results), 1)
        self.assertEqual(metadata['incompatible_embeddings_skipped'], 0)

    def test_provider_document_is_excluded_from_offline_query_despite_identical_values(self):
        self.chunk.metadata = {'embedding_provenance': dict(self.provenance,
            mode='PROVIDER', provider='gemini', model='fixture-model')}
        self.chunk.save(update_fields=['metadata'])
        results, metadata = self.search()
        self.assertEqual(results, [])
        self.assertEqual(metadata['incompatible_embeddings_skipped'], 1)

    def test_different_model_and_provider_are_excluded(self):
        for key, value in [('model', 'other-model'), ('provider', 'other-provider')]:
            with self.subTest(key=key):
                self.chunk.metadata = {'embedding_provenance': dict(self.provenance, **{key: value})}
                self.chunk.save(update_fields=['metadata'])
                self.assertEqual(self.search()[0], [])

    def test_dimension_mismatch_never_passes_zero_threshold(self):
        self.chunk.embedding = [1.0, 0.0]
        self.chunk.metadata = {}
        self.chunk.save(update_fields=['embedding', 'metadata'])
        results, metadata = self.search()
        self.assertEqual(results, [])
        self.assertEqual(metadata['incompatible_embeddings_skipped'], 1)

    def test_legacy_is_reported_without_invented_provenance(self):
        self.chunk.metadata = {}
        self.chunk.save(update_fields=['metadata'])
        results, metadata = self.search()
        self.assertEqual(results[0]['embedding_provenance'], {'mode': 'UNKNOWN'})
        self.assertEqual(metadata['legacy_embeddings_considered'], 1)

    def test_provider_query_cannot_use_hash_document(self):
        def provider_query(text, *, metadata):
            metadata.update(dict(self.provenance, mode='PROVIDER', provider='gemini', model='fixture'))
            return self.vector
        with patch('apps.knowledge.retrieval.get_embedding', side_effect=provider_query):
            self.assertEqual(self.search()[0], [])
