"""
Execution script for the 5 Advanced Enterprise AI Prompts.
Evaluates:
1. RAG vector context retrieval & citation from the newly ingested SOPs.
2. Structured domain data extraction via read-only selectors (Retail, Service, GIS, Labor).
3. Forecasting horizon & trend awareness.
4. What-If stress simulation.
5. Root-cause causal explanation.
6. Controlled agency & Human-In-The-Loop ApprovalRequest creation.
"""

import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.knowledge.services import answer_grounded_query
from apps.approvals.models import ApprovalRequest


def run_prompt(prompt_num: int, title: str, workspace_code: str, query: str, admin_user: User):
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
        user=admin_user,
        message=query,
    )
    approvals_after = ApprovalRequest.objects.for_workspace(ws).count()

    print("\n[AI GROUNDED RESPONSE]:")
    print(result.get("answer", "").strip())

    citations = result.get("citations") or result.get("sources", [])
    print(f"\n[CITATIONS / GROUNDED SOURCES] ({len(citations)} sources cited):")
    for c in citations:
        print(f"  - Document: '{c.get('document_title')}' | Section: '{c.get('heading')}' | Sim: {c.get('similarity')}")

    tool_calls = result.get("tools_used", [])
    print(f"\n[STRUCTURED TOOLS CALLED] ({len(tool_calls)}):")
    for t in tool_calls:
        print(f"  - Tool: {t.get('tool')} | Status: {t.get('status')}")

    if approvals_after > approvals_before:
        latest_approval = ApprovalRequest.objects.for_workspace(ws).order_by("-id").first()
        print(f"\n[HUMAN-IN-THE-LOOP APPROVAL CREATED]:")
        print(f"  - ApprovalRequest ID: #{latest_approval.id}")
        print(f"  - Proposed Action: {latest_approval.proposed_action}")
        print(f"  - Risk Level: {latest_approval.risk_level}")
        print(f"  - Status: {latest_approval.status} (Zero Direct DB Mutation by AI)")
        print(f"  - Parameters: {latest_approval.parameters}")
        print(f"  - Reason: {latest_approval.reason}")
    else:
        print("\n[APPROVAL STATUS]: Read-only or advisory query (No mutation requested).")

    print("\n" + "=" * 80 + "\n")


def main():
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    print("=== EXECUTING 5 HEAVY & COMPLEX ENTERPRISE AI PROMPTS ===")

    # Prompt 1A: Retail Supply Chain + Stockout Risk + Dell SOP RAG + Root Cause
    p1a = (
        "Phân tích các sản phẩm thuộc danh mục Laptop đang có nguy cơ cháy hàng hoặc tồn kho dưới mức "
        "an toàn tại Chi nhánh Quận 1 trong 10 ngày tới, đối chiếu với xu hướng bán hàng và chính sách "
        "nhập hàng từ nhà cung cấp Dell trong tài liệu SOP quy chuẩn tồn kho 2026, giải thích nguyên nhân gốc rễ."
    )
    run_prompt(1, "Retail Supply Chain, Stockout Prediction, Dell SOP RAG & Root Cause", "abc-retail", p1a, admin_user)

    # Prompt 1B: Controlled Mutation - Create Goods Receipt Approval Request
    p1b = (
        "Lập đề xuất tạo phiếu nhập kho 20 chiếc Laptop Dell Inspiron vào chi nhánh Quận 1 để kịp tiến độ bổ sung hàng tồn kho."
    )
    run_prompt(2, "Controlled State Mutation - Requisition Goods Receipt PO (HITL Approval)", "abc-retail", p1b, admin_user)

    # Prompt 2: Service Ops + GIS Spatial Technician Dispatch + Workload + Labor Cost
    p2 = (
        "Kiểm tra các phiếu yêu cầu dịch vụ kỹ thuật khẩn cấp URGENT chưa hoàn thành, tìm kỹ thuật viên "
        "đang ở bán kính gần nhất có kỹ năng xử lý phần cứng và mạng, tính toán ước lượng tổng chi phí nhân công "
        "theo bảng giá giờ công và quy chuẩn SLA sự cố khẩn cấp P1."
    )
    run_prompt(3, "Service Ops Urgent Incident, GIS Spatial Dispatch & Labor Cost SOP", "xyz-service", p2, admin_user)

    # Prompt 3: What-If Stress Testing Simulation
    p3 = (
        "Mô phỏng kịch bản giả định What-If: Nếu nhu cầu bán hàng tăng 25% trong tháng tới nhưng thời gian "
        "nhập hàng từ nhà cung cấp bị trễ thêm 3 ngày thì khả năng cung ứng và dự báo doanh thu thay đổi ra sao?"
    )
    run_prompt(4, "Cross-Domain What-If Simulation & Supply Chain Stress Testing", "abc-retail", p3, admin_user)

    # Prompt 4: Root Cause Explanation & VIP Customer History
    p4 = (
        "Vì sao doanh thu bán lẻ tháng này lại có sự biến động so với tháng trước? "
        "Đối chiếu với danh sách khách hàng mua nhiều nhất và các sản phẩm bán chạy nhất."
    )
    run_prompt(5, "Root-Cause Causal Analysis & Top Customers / Product Ranking", "abc-retail", p4, admin_user)

    # Prompt 5: AI Forecasting Diagnostics & Metrics Comparison
    p5 = (
        "Chính sách bảo hành thiết bị và quy trình đổi trả hàng đối với khách hàng VIP theo quy chế công ty quy định như thế nào?"
    )
    run_prompt(6, "Enterprise Policy RAG: VIP Customer Warranty & Return Regulations", "abc-retail", p5, admin_user)


if __name__ == "__main__":
    main()
