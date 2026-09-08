"""
Script to ingest advanced enterprise SOPs into the AI Knowledge Bases.
Workspace 'abc-retail' -> SOP_RETAIL_SUPPLY_CHAIN_2026.md
Workspace 'xyz-service' -> SOP_SERVICE_OPS_INCIDENT_SLA_2026.md
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


def main():
    print("=== INGESTING ADVANCED ENTERPRISE SOPS INTO KNOWLEDGE BASE ===")
    
    # 1. Fetch system admin or manager user
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_user:
        print("ERROR: No users found in database!")
        return

    # 2. Ingest Retail Supply Chain SOP into abc-retail
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
        
        doc_path = os.path.join("data", "knowledge", "SOP_RETAIL_SUPPLY_CHAIN_2026.md")
        if os.path.exists(doc_path):
            with open(doc_path, "rb") as f:
                django_file = File(f, name="SOP_RETAIL_SUPPLY_CHAIN_2026.md")
                doc = upload_and_ingest_document(
                    workspace=retail_ws,
                    user=admin_user,
                    knowledge_base=retail_kb,
                    file_obj=django_file,
                    title="Quy Chuẩn Điều Phối Tồn Kho Liên Chi Nhánh & Dự Báo Đứt Hàng 2026",
                    file_type="MD",
                )
                chunk_count = DocumentChunk.objects.filter(document=doc).count()
                print(f"[SUCCESS] Ingested '{doc.title}' (ID: {doc.id}, Status: {doc.status}, Chunks: {chunk_count}) into {retail_ws.name}")

    # 3. Ingest Service Ops SLA SOP into xyz-service
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
        
        doc_path = os.path.join("data", "knowledge", "SOP_SERVICE_OPS_INCIDENT_SLA_2026.md")
        if os.path.exists(doc_path):
            with open(doc_path, "rb") as f:
                django_file = File(f, name="SOP_SERVICE_OPS_INCIDENT_SLA_2026.md")
                doc = upload_and_ingest_document(
                    workspace=service_ws,
                    user=admin_user,
                    knowledge_base=service_kb,
                    file_obj=django_file,
                    title="Quy Trình Xử Lý Sự Cố Khẩn Cấp, Cam Kết MTTR & Phân Bổ Chi Phí Kỹ Thuật Viên 2026",
                    file_type="MD",
                )
                chunk_count = DocumentChunk.objects.filter(document=doc).count()
                print(f"[SUCCESS] Ingested '{doc.title}' (ID: {doc.id}, Status: {doc.status}, Chunks: {chunk_count}) into {service_ws.name}")

    print("\n=== TOTAL KNOWLEDGE BASE DOCUMENTS ===")
    for d in Document.objects.select_related("workspace", "knowledge_base").all():
        print(f"- Doc #{d.id}: {d.title} | Workspace: {d.workspace.code} | Status: {d.status} | Chunks: {d.chunks.count()}")


if __name__ == "__main__":
    main()
