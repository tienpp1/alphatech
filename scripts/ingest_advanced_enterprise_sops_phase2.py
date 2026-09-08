"""
Script to ingest Phase 2 advanced enterprise SOPs into the AI Knowledge Bases.
Workspace 'abc-retail' ->
  - SOP_RETAIL_FINANCIAL_MARGIN_2026.md
  - SOP_CUSTOMER_RETENTION_LOYALTY_2026.md
  - SOP_INTER_BRANCH_TRANSFER_2026.md
Workspace 'xyz-service' ->
  - SOP_CUSTOMER_RETENTION_LOYALTY_2026.md
  - SOP_FIELD_ENGINEERING_SAFETY_2026.md
"""

import os
import sys
import django
from django.core.files import File

# Configure Django
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk
from apps.knowledge.services import upload_and_ingest_document


def ingest_file(ws: Workspace, kb: KnowledgeBase, user: User, filename: str, title: str):
    doc_path = os.path.join("data", "knowledge", filename)
    if not os.path.exists(doc_path):
        print(f"[WARN] File not found: {doc_path}")
        return None

    # Avoid duplicate ingestion if document with same title exists in this kb
    existing = Document.objects.filter(knowledge_base=kb, title=title).first()
    if existing:
        print(f"[INFO] Document '{title}' already exists (ID: {existing.id}, Chunks: {existing.chunks.count()}). Skipping.")
        return existing

    with open(doc_path, "rb") as f:
        django_file = File(f, name=filename)
        doc = upload_and_ingest_document(
            workspace=ws,
            user=user,
            knowledge_base=kb,
            file_obj=django_file,
            title=title,
            file_type="MD",
        )
        chunk_count = DocumentChunk.objects.filter(document=doc).count()
        print(f"[SUCCESS] Ingested '{doc.title}' (ID: {doc.id}, Status: {doc.status}, Chunks: {chunk_count}) into {ws.name}")
        return doc


def main():
    print("=== INGESTING PHASE 2 ADVANCED ENTERPRISE SOPS INTO KNOWLEDGE BASE ===")
    
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_user:
        print("ERROR: No users found in database!")
        return

    # 1. Retail Workspace
    retail_ws = Workspace.objects.filter(code="abc-retail").first()
    if retail_ws:
        retail_kb = KnowledgeBase.objects.filter(workspace=retail_ws).first()
        if not retail_kb:
            retail_kb = KnowledgeBase.objects.create(
                workspace=retail_ws,
                name="Quy chế Bán hàng & Dịch vụ Khách hàng",
                description="Tài liệu quy chế nội bộ và chính sách bán lẻ",
                created_by=admin_user,
            )

        ingest_file(
            retail_ws, retail_kb, admin_user,
            "SOP_RETAIL_FINANCIAL_MARGIN_2026.md",
            "Quy Chuẩn Quản Trị Biên Lợi Nhuận & Chính Sách Tín Dụng Nhà Cung Cấp 2026"
        )
        ingest_file(
            retail_ws, retail_kb, admin_user,
            "SOP_CUSTOMER_RETENTION_LOYALTY_2026.md",
            "Quy Chuẩn Vòng Đời Khách Hàng, Phòng Ngừa Rời Bỏ & Cam Kết Dịch Vụ VIP 2026"
        )
        ingest_file(
            retail_ws, retail_kb, admin_user,
            "SOP_INTER_BRANCH_TRANSFER_2026.md",
            "Quy Chuẩn Cân Đối Tồn Kho Đa Chi Nhánh & Hậu Cần Điều Chuyển Nội Bộ 2026"
        )

    # 2. Service Workspace
    service_ws = Workspace.objects.filter(code="xyz-service").first()
    if service_ws:
        service_kb = KnowledgeBase.objects.filter(workspace=service_ws).first()
        if not service_kb:
            service_kb = KnowledgeBase.objects.create(
                workspace=service_ws,
                name="Quy trình & Tiêu chuẩn Vận hành Dịch vụ",
                description="Tài liệu kỹ thuật và cam kết SLA dịch vụ",
                created_by=admin_user,
            )

        ingest_file(
            service_ws, service_kb, admin_user,
            "SOP_CUSTOMER_RETENTION_LOYALTY_2026.md",
            "Quy Chuẩn Vòng Đời Khách Hàng & Khắc Phục Sự Cố Khách Hàng VIP 2026"
        )
        ingest_file(
            service_ws, service_kb, admin_user,
            "SOP_FIELD_ENGINEERING_SAFETY_2026.md",
            "Quy Chuẩn An Toàn Kỹ Thuật Hiện Trường, Chứng Chỉ Nghề & Bảo Mật Thông Tin ISO 27001"
        )

    print("\n=== TOTAL KNOWLEDGE BASE DOCUMENTS IN SYSTEM ===")
    for d in Document.objects.select_related("workspace", "knowledge_base").order_by("id"):
        print(f"- Doc #{d.id}: {d.title} | Workspace: {d.workspace.code} | Status: {d.status} | Chunks: {d.chunks.count()}")


if __name__ == "__main__":
    main()
