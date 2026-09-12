"""
Execution script for the New Phase 3 Enterprise AI Prompts.
Evaluates grounded RAG synthesis, exact citations, and zero direct DB mutation approvals.
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
from apps.approvals.models import ApprovalRequest


def run_prompt(prompt_num: int, title: str, workspace_code: str, query: str, user: User):
    print("=" * 80)
    print(f"PROMPT {prompt_num}: {title.upper()}")
    print(f"Workspace: {workspace_code}")
    print(f"User Query: \"{query}\"")
    print("-" * 80)

    ws = Workspace.objects.filter(code=workspace_code).first()
    if not ws:
        print(f"ERROR: Workspace {workspace_code} not found!")
        return

    approvals_before = ApprovalRequest.objects.for_workspace(ws).count()
    result = answer_grounded_query(
        workspace=ws,
        user=user,
        message=query,
    )
    approvals_after = ApprovalRequest.objects.for_workspace(ws).count()

    print("\n[AI GROUNDED RESPONSE]:")
    print(result.get("answer", "").strip())

    citations = result.get("citations") or result.get("sources", [])
    print(f"\n[CITATIONS / GROUNDED SOURCES] ({len(citations)} sources cited):")
    for c in citations:
        heading = c.get("heading") or "N/A"
        page = f" | Page: {c.get('page_number')}" if c.get("page_number") else ""
        sim = f"{c.get('similarity', 0.0):.2f}"
        print(f"  - Doc: '{c.get('document_title')}' | Section: '{heading}'{page} | Similarity: {sim}")

    tools = result.get("tools_used", [])
    print(f"\n[TOOLS USED] ({len(tools)}):")
    for t in tools:
        print(f"  - Tool: {t.get('tool')} | Status: {t.get('status')}")

    if approvals_after > approvals_before:
        latest = ApprovalRequest.objects.for_workspace(ws).order_by("-id").first()
        print(f"\n[HUMAN-IN-THE-LOOP APPROVAL CREATED]:")
        print(f"  - ID: #AR-{latest.id}")
        print(f"  - Action: {latest.proposed_action}")
        print(f"  - Risk: {latest.risk_level}")
        print(f"  - Status: {latest.status}")
        print(f"  - Reason: {latest.reason}")
    else:
        print("\n[APPROVAL STATUS]: Read-only query (No mutation required).")

    print("\n" + "=" * 80 + "\n")


def main():
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    print("=== EXECUTING PHASE 3 ENTERPRISE AI PROMPTS ===")

    # 1. Retail RMA & DOA 72h
    p1 = "Chính sách đổi mới sản phẩm lỗi ban đầu DOA trong 72 giờ và điều kiện mượn máy tính thay thế khi bảo hành kéo dài trên 7 ngày quy định thế nào?"
    run_prompt(1, "Retail RMA: DOA 72h Replacement & Loaner PC Policy", "abc-retail", p1, admin_user)

    # 2. Retail Supplier Penalties & AQL 2.0%
    p2 = "Nhà phân phối giao hàng trễ bị phạt bao nhiêu phần trăm mỗi ngày, mức trần phạt tối đa là bao nhiêu và khi nào kích hoạt từ chối toàn bộ lô hàng theo ngưỡng AQL 2.0%?"
    run_prompt(2, "Retail Supplier Contract: Delay Penalties & AQL Batch Rejection", "abc-retail", p2, admin_user)

    # 3. Retail Omnichannel BOPIS & Video Packaging
    p3 = "Quy định giữ hàng đơn BOPIS nhận tại cửa hàng trong bao lâu và tại sao đơn hàng công nghệ trên 5 triệu đồng bắt buộc phải quay video đóng gói?"
    run_prompt(3, "Retail Omnichannel: BOPIS Reservation & High-Value Video Evidence", "abc-retail", p3, admin_user)

    # 4. Service Cybersecurity P0 Ransomware & No-Reboot
    p4 = "Khi phát hiện sự cố mã độc tống tiền Ransomware cấp P0, quy trình cô lập mạng 5 phút thực hiện như thế nào và vì sao nghiêm cấm tuyệt đối việc reboot khởi động lại máy chủ?"
    run_prompt(4, "Service Security: P0 Ransomware 5-Min Quarantine & Strict No-Reboot Rule", "xyz-service", p4, admin_user)

    # 5. Service SLA Escalation Matrix 3-Tier
    p5 = "Ma trận leo thang sự cố SLA 3 cấp độ ở các mốc 50% và 75% thời hạn SLA xử lý ra sao, khi nào điều động thêm kỹ sư chi viện trong bán kính 10km?"
    run_prompt(5, "Service Ops: Proactive 3-Tier SLA Escalation & GIS Backup Dispatch", "xyz-service", p5, admin_user)

    # 6. Service Datacenter Thermal & ATS Diesel Generator
    p6 = "Tiêu chuẩn nhiệt độ hành lang lạnh phòng Server ASHRAE duy trì ở mức nào, ngưỡng ngắt điện khẩn cấp EPO là bao nhiêu và máy phát điện Diesel tự động hòa điện trong bao nhiêu giây?"
    run_prompt(6, "Service Datacenter: Cold Aisle Thermal Standards, EPO & 15s ATS Diesel", "xyz-service", p6, admin_user)

    # 7. HITL Mutation - DOA Replacement Proposal
    p7 = "Lập đề xuất đổi mới DOA 100% cho khách hàng mua laptop bị lỗi điểm sáng trong 72 giờ"
    run_prompt(7, "Controlled State Mutation: DOA 100% Replacement Approval Proposal", "abc-retail", p7, admin_user)


if __name__ == "__main__":
    main()
