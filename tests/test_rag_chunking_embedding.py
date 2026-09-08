"""
Automated tests for RecursiveTextChunker and dynamic vector embedding generation.
"""

from django.test import TestCase
from apps.knowledge.chunking import RecursiveTextChunker
from apps.knowledge.embedding import (
    get_embedding,
    get_embeddings_batch,
    _generate_deterministic_embedding,
)


class ChunkingAndEmbeddingTests(TestCase):
    def test_recursive_chunker_splits_on_boundaries(self):
        """Test recursive splitter respects chunk_size and split hierarchy."""
        chunker = RecursiveTextChunker(chunk_size=100, chunk_overlap=20)
        long_text = (
            "Paragraph one introduces the company policy. It contains several important guidelines.\n\n"
            "Paragraph two details the warranty process. All laptop devices are covered for two years.\n\n"
            "Paragraph three explains return shipping and RMA handling procedure."
        )
        segments = [{"text": long_text, "page_number": 1, "heading": "Overview"}]
        chunks = chunker.chunk_segments(segments, source_title="Policy.docx")

        self.assertGreater(len(chunks), 1)
        for ch in chunks:
            self.assertLessEqual(len(ch["content"]), 150)
            self.assertEqual(ch["metadata"]["page_number"], 1)
            self.assertEqual(ch["metadata"]["heading"], "Overview")
            self.assertEqual(ch["metadata"]["source_file"], "Policy.docx")

    def test_chunker_sliding_overlap(self):
        """Test chunker produces consecutive index numbers."""
        chunker = RecursiveTextChunker(chunk_size=50, chunk_overlap=15)
        text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau."
        chunks = chunker.chunk_segments([{"text": text, "page_number": 2, "heading": None}])

        indices = [c["chunk_index"] for c in chunks]
        self.assertEqual(indices, list(range(1, len(chunks) + 1)))

    def test_dynamic_embedding_dimension(self):
        """Test that embedding vectors match the configured dynamic dimension."""
        dim_768 = get_embedding("Chinh sach bao hanh", dimension=768)
        self.assertEqual(len(dim_768), 768)

        dim_1536 = get_embedding("Chinh sach bao hanh", dimension=1536)
        self.assertEqual(len(dim_1536), 1536)

    def test_embedding_is_l2_normalized(self):
        """Test embedding vector has unit L2 norm (magnitude ~= 1.0)."""
        import math
        vec = get_embedding("Doanh thu ban hang thang 8", dimension=768)
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=3)

    def test_deterministic_embedding_reproducibility(self):
        """Test same text produces identical deterministic vector."""
        text = "Quy trinh lap dat thiet bi mang tieu chuan"
        v1 = _generate_deterministic_embedding(text, 768)
        v2 = _generate_deterministic_embedding(text, 768)
        self.assertEqual(v1, v2)

    def test_batch_embeddings(self):
        """Test batch embedding generation returns correct count and dimensions."""
        texts = ["Text one", "Text two", "Text three"]
        batch = get_embeddings_batch(texts, dimension=768)
        self.assertEqual(len(batch), 3)
        for vec in batch:
            self.assertEqual(len(vec), 768)
