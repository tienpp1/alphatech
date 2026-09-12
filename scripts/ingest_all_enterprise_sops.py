"""
Comprehensive Ingestion Script for All 12 Enterprise SOP Documents.
Ingests Retail & Service SOPs into Knowledge Bases of 'abc-retail' and 'xyz-service'.
Ensures idempotent ingestion, clean chunking, and high-dimensional vector embeddings.
"""

import os
import sys
import django
from django.core.files import File

# Configure Django
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk, DocumentStatus
from apps.knowledge.services import upload_and_ingest_document, ingest_document


RETAIL_SOPS = [
    {
        "filename": "SOP_RETAIL_SUPPLY_CHAIN_2026.md",
        "title": "Quy Chuẩn Điều Phối Tồn Kho Liên Chi Nhánh & Dự Báo Đứt Hàng 2026",
    },
    {
        "filename": "SOP_RETAIL_FINANCIAL_MARGIN_2026.md",
        "title": "Quy Chuẩn Quản Trị Biên Lợi Nhuận & Chính Sách Tín Dụng Nhà Cung Cấp 2026",
    },
    {
        "filename": "SOP_CUSTOMER_RETENTION_LOYALTY_2026.md",
        "title": "Quy Chuẩn Vòng Đời Khách Hàng, Phòng Ngừa Rời Bỏ & Cam Kết Dịch Vụ VIP 2026",
    },
    {
        "filename": "SOP_INTER_BRANCH_TRANSFER_2026.md",
        "title": "Quy Chuẩn Cân Đối Tồn Kho Đa Chi Nhánh & Hậu Cần Điều Chuyển Nội Bộ 2026",
    },
    {
        "filename": "SOP_RETAIL_RMA_WARRANTY_2026.md",
        "title": "Quy Chuẩn Tiếp Nhận Bảo Hành, Thẩm Định Đổi Mới DOA & Quản Trị RMA Linh Kiện 2026",
    },
    {
        "filename": "SOP_SUPPLIER_CONTRACT_PENALTIES_2026.md",
        "title": "Quy Chuẩn Hợp Đồng Mua Hàng, Chế Tài Phạt Giao Hàng Trễ & Thu Hồi Lô Hàng Lỗi 2026",
    },
    {
        "filename": "SOP_OMNICHANNEL_FULFILLMENT_2026.md",
        "title": "Quy Chuẩn Đơn Hàng Đa Kênh Omnichannel, BOPIS & Đóng Gói Công Nghệ 2026",
    },
    {
        "filename": "SOP_RETAIL_PROMO_FRAUD_2026.md",
        "title": "Quy Chuẩn Kiểm Soát Gian Lận Khuyến Mãi, Chống Lạm Dụng Voucher & Ưu Đãi Nhân Viên 2026",
    },
    {
        "filename": "SOP_RETAIL_INVENTORY_AUDIT_2026.md",
        "title": "Quy Chuẩn Kiểm Kê Kho Định Kỳ, Xử Lý Hao Hụt & Tiêu Hủy Pin Chai Phồng 2026",
    },
    {
        "filename": "SOP_RETAIL_TRADE_IN_2026.md",
        "title": "Quy Chuẩn Thu Cũ Đổi Mới Trade-In, Thẩm Định Định Giá & Xóa Trắng Dữ Liệu 2026",
    },
]

SERVICE_SOPS = [
    {
        "filename": "SOP_SERVICE_OPS_INCIDENT_SLA_2026.md",
        "title": "Quy Trình Xử Lý Sự Cố Khẩn Cấp, Cam Kết MTTR & Phân Bổ Chi Phí Kỹ Thuật Viên 2026",
    },
    {
        "filename": "SOP_FIELD_ENGINEERING_SAFETY_2026.md",
        "title": "Quy Chuẩn An Toàn Kỹ Thuật Hiện Trường, Chứng Chỉ Nghề & Bảo Mật Thông Tin ISO 27001",
    },
    {
        "filename": "SOP_CUSTOMER_RETENTION_LOYALTY_2026.md",
        "title": "Quy Chuẩn Vòng Đời Khách Hàng & Khắc Phục Sự Cố Khách Hàng VIP 2026",
    },
    {
        "filename": "SOP_CYBERSECURITY_INCIDENT_DRP_2026.md",
        "title": "Quy Trình Ứng Cứu Sự Cố An Ninh Mạng, Cô Lập Ransomware & Phục Hồi Dữ Liệu Thảm Họa 2026",
    },
    {
        "filename": "SOP_SLA_ESCALATION_DISPUTE_2026.md",
        "title": "Quy Chuẩn Ma Trận Leo Thang Sự Cố SLA & Hòa Giải Tranh Chấp Kỹ Thuật 2026",
    },
    {
        "filename": "SOP_DATACENTER_THERMAL_ENERGY_2026.md",
        "title": "Quy Chuẩn Môi Trường Nhiệt Độ Phòng Server, Tiêu Chuẩn Xanh & Dự Phòng Nguồn Điện 2026",
    },
    {
        "filename": "SOP_SVC_CHANGE_MANAGEMENT_2026.md",
        "title": "Quy Chuẩn Quản Lý Thay Đổi Hệ Thống CNTT, ITIL CAB & Kế Hoạch Rollback 2026",
    },
    {
        "filename": "SOP_SVC_ASSET_DECOMMISSION_2026.md",
        "title": "Quy Chuẩn Tiêu Hủy Dữ Liệu Số & Thanh Lý Thiết Bị Lưu Trữ NIST 800-88 2026",
    },
    {
        "filename": "SOP_SVC_BACKUP_RETENTION_2026.md",
        "title": "Quy Chuẩn Sao Lưu Dữ Liệu 3-2-1-1, Lưu Trữ Bất Biến WORM & Diễn Tập Phục Hồi 2026",
    },
]

CORE_SOPS = [
    {
        "filename": "SOP_CORE_WORKING_HOURS_LEAVE_2026.md",
        "title": "Nội Quy Lao Động, Thời Giờ Làm Việc, Chấm Công & Nghỉ Phép Năm 2026",
    },
    {
        "filename": "SOP_CORE_EXPENSE_TRAVEL_REIMBURSEMENT_2026.md",
        "title": "Quy Chế Tạm Ứng, Thanh Toán Công Tác Phí & Hoàn Ứng Chi Phí 2026",
    },
    {
        "filename": "SOP_CORE_IT_SECURITY_DEVICE_USAGE_2026.md",
        "title": "Quy Định An Toàn Thông Tin, Quản Lý Mật Khẩu & Sử Dụng Thiết Bị 2026",
    },
    {
        "filename": "SOP_CORE_ONBOARDING_PROBATION_2026.md",
        "title": "Quy Trình Tiếp Nhận Nhân Viên Mới & Đánh Giá Hết Hạn Thử Việc 2026",
    },
    {
        "filename": "SOP_CORE_CODE_OF_CONDUCT_CULTURE_2026.md",
        "title": "Chuẩn Mực Văn Hóa Doanh Nghiệp, Trang Phục & Giải Quyết Xung Đột 2026",
    },
    {
        "filename": "SOP_CORE_PERFORMANCE_BENEFITS_BONUS_2026.md",
        "title": "Quy Chế Đánh Giá Hiệu Suất KPI, Lương Tháng 13 & Phúc Lợi Nhân Viên 2026",
    },
]


def ingest_sop(ws: Workspace, kb: KnowledgeBase, user: User, sop_info: dict):
    filename = sop_info["filename"]
    title = sop_info["title"]
    filepath = os.path.join("data", "knowledge", filename)

    if not os.path.exists(filepath):
        print(f"  [ERROR] File not found: {filepath}")
        return None

    # Check if already exists in this KB
    existing = Document.objects.filter(knowledge_base=kb, title=title).first()
    if existing:
        # Re-ingest to ensure chunks are up to date
        print(f"  [INFO] Updating existing document '{title}' (ID: {existing.id})...")
        with open(filepath, "rb") as f:
            existing.file.save(filename, File(f), save=True)
        doc = ingest_document(existing.id)
        chunk_count = DocumentChunk.objects.filter(document=doc).count()
        print(f"  [SUCCESS] Updated '{doc.title}' (ID: {doc.id}, Status: {doc.status}, Chunks: {chunk_count})")
        return doc
    else:
        with open(filepath, "rb") as f:
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
            print(f"  [SUCCESS] Ingested '{doc.title}' (ID: {doc.id}, Status: {doc.status}, Chunks: {chunk_count})")
            return doc


def main():
    print("=" * 80)
    print("STARTING COMPREHENSIVE ENTERPRISE SOP INGESTION PIPELINE")
    print("=" * 80)

    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_user:
        print("[ERROR] No admin user found in database.")
        return

    # 1. Retail Workspace
    retail_ws = Workspace.objects.filter(code="abc-retail").first()
    if retail_ws:
        print(f"\n---> [WORKSPACE: {retail_ws.code} - {retail_ws.name}]")
        retail_kb, _ = KnowledgeBase.objects.get_or_create(
            workspace=retail_ws,
            defaults={
                "name": "Quy chế Bán hàng & Dịch vụ Khách hàng",
                "description": "Kho tài liệu quy chế nội bộ, chính sách chuỗi cung ứng, tài chính và bán lẻ 2026",
                "created_by": admin_user,
            }
        )
        for sop in RETAIL_SOPS + CORE_SOPS:
            ingest_sop(retail_ws, retail_kb, admin_user, sop)

    # 2. Service Workspace
    service_ws = Workspace.objects.filter(code="xyz-service").first()
    if service_ws:
        print(f"\n---> [WORKSPACE: {service_ws.code} - {service_ws.name}]")
        service_kb, _ = KnowledgeBase.objects.get_or_create(
            workspace=service_ws,
            defaults={
                "name": "Quy trình & Tiêu chuẩn Vận hành Dịch vụ",
                "description": "Kho tài liệu quy trình kỹ thuật, tiêu chuẩn an toàn, an ninh mạng và SLA 2026",
                "created_by": admin_user,
            }
        )
        for sop in SERVICE_SOPS + CORE_SOPS:
            ingest_sop(service_ws, service_kb, admin_user, sop)

    # Summary
    print("\n" + "=" * 80)
    print("INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    for ws in [retail_ws, service_ws]:
        if ws:
            docs = Document.objects.filter(workspace=ws).select_related("knowledge_base")
            chunks_total = DocumentChunk.objects.filter(workspace=ws).count()
            print(f"Workspace {ws.code}: {docs.count()} Documents | {chunks_total} Total Vector Chunks")
            for d in docs:
                print(f"  - [{d.id}] {d.title} | {d.chunks.count()} chunks | Status: {d.status}")


if __name__ == "__main__":
    main()
