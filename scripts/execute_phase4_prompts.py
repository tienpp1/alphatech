"""
Execute Live Phase 4 Enterprise Prompts against Knowledge Bases of 'abc-retail' and 'xyz-service'.
Verifies that Grounded RAG accurately cites the new Phase 4 SOPs.
"""

import os
import sys
import django

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.knowledge.services import answer_grounded_query

def test_enterprise_prompt(ws: Workspace, user: User, label: str, prompt: str):
    print("=" * 80)
    print(f"[{ws.code.upper()}] TEST: {label}")
    print(f"PROMPT: \"{prompt}\"")
    print("-" * 80)

    res = answer_grounded_query(
        workspace=ws,
        user=user,
        message=prompt,
    )

    print(f"INTENT DETECTED: {res.get('intent')}")
    print(f"TOOL RESULTS COUNT: {len(res.get('tools_data', []))}")
    print(f"CITATIONS COUNT: {len(res.get('sources', []))}")

    print("\n--- CITATIONS ---")
    for i, s in enumerate(res.get("sources", []), 1):
        heading = f" - {s.get('heading')}" if s.get('heading') else ""
        print(f"  {i}. {s['document_title']}{heading} (Chunk #{s['chunk_id']}, Sim: {s['similarity']:.3f})")

    print("\n--- AI ASSISTANT GROUNDED ANSWER ---")
    print(res.get("answer", "").strip())
    print("=" * 80 + "\n")


def main():
    retail_ws = Workspace.objects.get(code="abc-retail")
    service_ws = Workspace.objects.get(code="xyz-service")
    admin_user = User.objects.filter(is_superuser=True).first()

    print("\n" + "#" * 80)
    print("  PHASE 4 ENTERPRISE SOP LIVE PROMPT BENCHMARK")
    print("#" * 80 + "\n")

    # Retail Prompts
    test_enterprise_prompt(
        retail_ws,
        admin_user,
        "PROMO FRAUD & STAFF DISCOUNT 90 DAYS",
        "Quy trình kiểm soát gian lận khuyến mãi, cơ chế Fraud Hold và quy tắc giữ máy 90 ngày của Staff Discount?",
    )

    test_enterprise_prompt(
        retail_ws,
        admin_user,
        "INVENTORY CYCLE COUNT & HAZARDOUS BATTERY DISPOSAL",
        "Quy chuẩn kiểm kê kho định kỳ Cycle Count, xử lý hao hụt vượt 0.2% và tiêu hủy pin chai phồng?",
    )

    test_enterprise_prompt(
        retail_ws,
        admin_user,
        "TRADE-IN VALUATION & ZERO DATA LEAK",
        "Quy trình thu cũ đổi mới Trade-In, ma trận định giá 4 cấp và cam kết xóa trắng dữ liệu khách hàng?",
    )

    # Service Prompts
    test_enterprise_prompt(
        service_ws,
        admin_user,
        "ITIL CHANGE MANAGEMENT & ROLLBACK",
        "Quy chuẩn quản lý thay đổi ITIL CAB, kế hoạch Rollback 15 phút và khung giờ Change Freeze?",
    )

    test_enterprise_prompt(
        service_ws,
        admin_user,
        "NIST 800-88 DATA SANITIZATION",
        "Tiêu chuẩn tiêu hủy dữ liệu số NIST SP 800-88, khử từ Degaussing và nghiền nát SSD?",
    )

    test_enterprise_prompt(
        service_ws,
        admin_user,
        "BACKUP 3-2-1-1 & IMMUTABLE WORM",
        "Chiến lược sao lưu dự phòng 3-2-1-1, lưu trữ bất biến WORM và diễn tập phục hồi Sandbox?",
    )


if __name__ == "__main__":
    main()
