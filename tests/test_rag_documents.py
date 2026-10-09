"""
Automated tests for Document Ingestion and lifecycle management.
Covers PDF, DOCX, TXT, MD parsing, status transitions, metadata retention, and error resilience.
"""

import io
from pathlib import Path
import docx
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentFileType,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
    ingest_document,
    delete_document,
)


class DocumentIngestionTests(TestCase):
    def test_source_reviewed_platform_guides_ingest_and_retrieve_in_workspace(self):
        from apps.knowledge.retrieval import search_relevant_chunks
        from apps.knowledge.services import generate_grounded_answer
        guide_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "platform_guides"
        queries = {
            "01_tai_khoan_va_workspace.md": "Vì sao không xem được dữ liệu workspace khác?",
            "02_rag_va_nguon.md": "Hai tài liệu mâu thuẫn thì trả lời thế nào?",
            "03_du_bao_va_phe_duyet.md": "Khi XGBoost kém baseline thì kết luận thế nào?",
            "04_trao_doi_va_kenh_thong_bao.md": "Chat nhóm nội bộ hoạt động như thế nào?",
            "05_don_hang_va_ton_kho.md": "Hủy đơn có tự hoàn tiền không?",
            "06_nhap_du_lieu_va_mapping.md": "Import thành công có nghĩa đã cập nhật dữ liệu bán hàng không?",
            "07_tiep_nhan_dich_vu_va_chan_doan.md": "Ticket thiếu deadline thì có được tính đạt SLA không?",
        }
        documents = {}
        for filename in queries:
            with self.subTest(ingest=filename):
                document = upload_and_ingest_document(
                    self.workspace, self.user, self.kb,
                    SimpleUploadedFile(filename, (guide_dir / filename).read_bytes(), content_type="text/markdown"),
                    filename, "MD")
                self.assertEqual(document.status, DocumentStatus.READY)
                self.assertGreater(document.chunk_count, 0)
                for chunk in document.chunks.all():
                    self.assertEqual(chunk.metadata['embedding_input_kind'], 'heading_and_content_v1')
                documents[filename] = document
        for filename, query in queries.items():
            with self.subTest(retrieve=query):
                chunks = search_relevant_chunks(self.workspace, query, top_k=5)
                self.assertIn(documents[filename].id, [chunk["document_id"] for chunk in chunks])
                self.assertEqual(chunks[0]["document_id"], documents[filename].id)
                answer, sources = generate_grounded_answer(self.workspace, self.user, query, chunks)
                self.assertIn("Nguồn:", answer)
                self.assertTrue(sources)
        foreign = Workspace.objects.create(code="foreign-platform-guide", name="Foreign", workspace_type=WorkspaceType.RETAIL)
        self.assertEqual(search_relevant_chunks(foreign, queries["01_tai_khoan_va_workspace.md"]), [])

    def setUp(self):
        self.user = User.objects.create_user(username="test_admin", email="admin@example.com")
        self.workspace = Workspace.objects.create(
            code="test-ws",
            name="Test Workspace",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.kb = create_knowledge_base(
            workspace=self.workspace,
            user=self.user,
            name="Internal Policies",
        )

    def test_ingest_plain_text_document(self):
        """Test uploading and indexing a plain UTF-8 text document."""
        content = b"Chinh sach bao hanh thiet bi dien tu: Laptop duoc bao hanh 24 thang ke tu ngay mua."
        file_obj = SimpleUploadedFile("warranty.txt", content, content_type="text/plain")

        doc = upload_and_ingest_document(
            workspace=self.workspace,
            user=self.user,
            knowledge_base=self.kb,
            file_obj=file_obj,
            title="Warranty Policy",
            file_type="TXT",
        )

        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertGreater(doc.chunk_count, 0)
        chunks = DocumentChunk.objects.filter(document=doc)
        self.assertEqual(chunks.count(), doc.chunk_count)
        self.assertIn("Laptop duoc bao hanh", chunks.first().content)

    def test_ingest_markdown_document_with_headings(self):
        """Test uploading Markdown document with heading detection."""
        md_content = b"# Chinh sach doi tra\n\nKhach hang duoc doi tra trong 7 ngay.\n\n# Quy dinh hoan tien\n\nTien duoc hoan sau 3 ngay."
        file_obj = SimpleUploadedFile("return_policy.md", md_content, content_type="text/markdown")

        doc = upload_and_ingest_document(
            workspace=self.workspace,
            user=self.user,
            knowledge_base=self.kb,
            file_obj=file_obj,
            title="Return Policy",
            file_type="MD",
        )

        self.assertEqual(doc.status, DocumentStatus.READY)
        chunks = DocumentChunk.objects.filter(document=doc)
        self.assertGreater(chunks.count(), 0)

    def test_ingest_docx_document(self):
        """Test uploading and parsing real binary Microsoft Word (.docx) document."""
        docx_doc = docx.Document()
        docx_doc.add_heading("Quy trinh lap dat may chu", level=1)
        docx_doc.add_paragraph("Ky thuat vien phai kiem tra nguon dien UPS va tiep dia truoc khi bat may.")
        bio = io.BytesIO()
        docx_doc.save(bio)

        file_obj = SimpleUploadedFile("server_install.docx", bio.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        doc = upload_and_ingest_document(
            workspace=self.workspace,
            user=self.user,
            knowledge_base=self.kb,
            file_obj=file_obj,
            title="Server Install SOP",
            file_type="DOCX",
        )

        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertGreater(doc.chunk_count, 0)
        chunk = DocumentChunk.objects.filter(document=doc).first()
        self.assertIsNotNone(chunk.embedding)
        self.assertIn("UPS", chunk.content)

    def test_ingest_empty_file_fails_gracefully(self):
        """Test that an empty 0-byte file transitions to FAILED status with clear error."""
        file_obj = SimpleUploadedFile("empty.txt", b"", content_type="text/plain")

        doc = upload_and_ingest_document(
            workspace=self.workspace,
            user=self.user,
            knowledge_base=self.kb,
            file_obj=file_obj,
            title="Empty Document",
            file_type="TXT",
        )

        self.assertEqual(doc.status, DocumentStatus.FAILED)
        self.assertIn("empty", doc.error_message.lower())

    def test_delete_document_cleans_up_chunks(self):
        """Test document deletion cascades to document chunks."""
        content = b"Some confidential company guidelines."
        file_obj = SimpleUploadedFile("guidelines.txt", content, content_type="text/plain")

        doc = upload_and_ingest_document(
            workspace=self.workspace,
            user=self.user,
            knowledge_base=self.kb,
            file_obj=file_obj,
            title="Guidelines",
            file_type="TXT",
        )

        doc_id = doc.id
        self.assertTrue(DocumentChunk.objects.filter(document_id=doc_id).exists())

        delete_document(doc, self.user)

        self.assertFalse(Document.objects.filter(id=doc_id).exists())
        self.assertFalse(DocumentChunk.objects.filter(document_id=doc_id).exists())
