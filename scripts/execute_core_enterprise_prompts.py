"""
Execute Live Core Enterprise Handbook Prompts against Knowledge Bases of 'abc-retail' and 'xyz-service'.
Verifies that Grounded RAG accurately cites the new Core Enterprise SOPs.
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

def test_core_prompt(ws: Workspace, user: User, label: str, prompt: str):
    print("=" * 80)
    print(f"[{ws.code.upper()}] CORE PROMPT TEST: {label}")
    print(f"PROMPT: \"{prompt}\"")
    print("-" * 80)

    res = answer_grounded_query(
        workspace=ws,
        user=user,
        message=prompt,
    )

    print(f"INTENT DETECTED: {res.get('intent')}")
    print(f"CITATIONS COUNT: {len(res.get('sources', res.get('citations', [])))}")

    print("\n--- CITATIONS ---")
    citations = res.get("sources", res.get("citations", []))
    for i, s in enumerate(citations, 1):
        heading = f" - {s.get('heading')}" if s.get('heading') else ""
        print(f"  {i}. {s['document_title']}{heading} (Chunk #{s.get('chunk_id')}, Sim: {s.get('similarity', 0.0):.3f})")

    print("\n--- AI ASSISTANT GROUNDED ANSWER ---")
    print(res.get("answer", "").strip())
    print("=" * 80 + "\n")


def main():
    retail_ws = Workspace.objects.get(code="abc-retail")
    service_ws = Workspace.objects.get(code="xyz-service")
    admin_user = User.objects.filter(is_superuser=True).first()

    print("\n" + "#" * 80)
    print("  CORE ENTERPRISE HANDBOOK LIVE PROMPT BENCHMARK")
    print("#" * 80 + "\n")

    test_core_prompt(
        retail_ws,
        admin_user,
        "WORKING HOURS & ANNUAL LEAVE",
        "Nội quy thời giờ làm việc, quy định đi muộn và số ngày phép năm của nhân viên?",
    )

    test_core_prompt(
        retail_ws,
        admin_user,
        "BUSINESS TRAVEL & REIMBURSEMENT",
        "Quy chế thanh toán công tác phí, hạn mức tiền ăn và thời hạn nộp hóa đơn hoàn ứng?",
    )

    test_core_prompt(
        service_ws,
        admin_user,
        "PASSWORD POLICY & CLEAN DESK",
        "Quy định đặt mật khẩu máy tính, xác thực hai lớp MFA và khóa màn hình khi rời bàn?",
    )

    test_core_prompt(
        service_ws,
        admin_user,
        "ONBOARDING & PROBATION EVALUATION",
        "Thời gian thử việc tối đa là bao lâu và tiêu chuẩn đánh giá ký hợp đồng chính thức?",
    )

    test_core_prompt(
        retail_ws,
        admin_user,
        "DRESS CODE & CODE OF CONDUCT",
        "Quy định trang phục công sở từ thứ 2 đến thứ 6 và chuẩn mực văn hóa ứng xử?",
    )

    test_core_prompt(
        service_ws,
        admin_user,
        "13TH MONTH SALARY & BENEFITS",
        "Điều kiện hưởng thưởng lương tháng 13 và chế độ khám sức khỏe định kỳ hàng năm?",
    )


if __name__ == "__main__":
    main()
