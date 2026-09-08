"""
Automated tests for Vector Search Retrieval, Cosine Similarity, and Multi-Tenant Isolation.
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.knowledge.models import (
    KnowledgeBase,
    DocumentChunk,
    DocumentStatus,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
)
from apps.knowledge.retrieval import (
    search_relevant_chunks,
    calculate_cosine_similarity,
)


class VectorRetrievalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_search_user")

        # Workspace A (Retail)
        self.ws_a = Workspace.objects.create(
            code="ws-retail-a",
            name="Retail Corp A",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.kb_a = create_knowledge_base(self.ws_a, self.user, "Retail Policies A")

        # Ingest document into Workspace A
        retail_doc = b"Chinh sach bao hanh: May tinh xach tay laptop duoc bao hanh 24 thang. Doi tra trong 7 ngay."
        f_a = SimpleUploadedFile("retail_a.txt", retail_doc, content_type="text/plain")
        self.doc_a = upload_and_ingest_document(
            workspace=self.ws_a,
            user=self.user,
            knowledge_base=self.kb_a,
            file_obj=f_a,
            title="Retail Warranty Policy A",
            file_type="TXT",
        )

        # Workspace B (Service)
        self.ws_b = Workspace.objects.create(
            code="ws-service-b",
            name="Service Corp B",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.kb_b = create_knowledge_base(self.ws_b, self.user, "Service Policies B")

        # Ingest document into Workspace B
        service_doc = b"Quy trinh bao tri he thong: Kiem tra nhiet do phong may chu duoi 65 do C, bao duong hang quy."
        f_b = SimpleUploadedFile("service_b.txt", service_doc, content_type="text/plain")
        self.doc_b = upload_and_ingest_document(
            workspace=self.ws_b,
            user=self.user,
            knowledge_base=self.kb_b,
            file_obj=f_b,
            title="Server Maintenance SOP B",
            file_type="TXT",
        )

    def test_calculate_cosine_similarity(self):
        """Test cosine similarity function returns 1.0 for identical vectors."""
        vec1 = [0.6, 0.8]
        vec2 = [0.6, 0.8]
        self.assertAlmostEqual(calculate_cosine_similarity(vec1, vec2), 1.0, places=4)

        # Orthogonal vectors
        vec_ortho = [-0.8, 0.6]
        self.assertAlmostEqual(calculate_cosine_similarity(vec1, vec_ortho), 0.0, places=4)

    def test_retrieval_returns_relevant_chunk(self):
        """Test searching for laptop warranty retrieves doc_a chunks in workspace A."""
        results = search_relevant_chunks(
            workspace=self.ws_a,
            query="Chinh sach bao hanh may tinh xach tay laptop",
            top_k=3,
            threshold=0.30,
        )

        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertEqual(top["document_id"], self.doc_a.id)
        self.assertIn("laptop", top["content"].lower())
        self.assertGreaterEqual(top["similarity"], 0.30)

    def test_strict_workspace_isolation_in_retrieval(self):
        """
        CRITICAL TEST: Searching for 'laptop' in Workspace B must NEVER return
        chunks from Workspace A, even if Workspace A has a 100% semantic match!
        """
        results_in_b = search_relevant_chunks(
            workspace=self.ws_b,
            query="Chinh sach bao hanh may tinh xach tay laptop",
            top_k=5,
            threshold=0.10,
        )

        for chunk in results_in_b:
            self.assertNotEqual(
                chunk["document_id"],
                self.doc_a.id,
                "Cross-tenant retrieval leakage! Workspace B received chunks from Workspace A.",
            )

    def test_threshold_filters_out_unrelated_queries(self):
        """Test high threshold rejects completely irrelevant queries."""
        results = search_relevant_chunks(
            workspace=self.ws_a,
            query="Cong thuc nau mon mi Y spaghetti sot bo bam",
            top_k=5,
            threshold=0.85,
        )
        self.assertEqual(len(results), 0)
