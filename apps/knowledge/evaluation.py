"""
Evaluation Benchmark Dataset and Automated Metrics Evaluator for Grounded RAG Assistant.
Contains 16 curated test cases across 4 categories:
1. Document-only questions
2. Structured-business-only questions
3. Hybrid questions
4. Out-of-domain / Unsupported questions (Fallback validation)
"""

from typing import Any, Dict, List
from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.knowledge.services import answer_grounded_query, FALLBACK_NO_CONTEXT_MESSAGE


BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    # 1. Document-only questions (Retail & Service)
    {
        "id": "DOC-01",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "RETAIL",
        "question": "Chính sách bảo hành laptop quy định thời hạn bao nhiêu tháng và điều kiện 1 đổi 1 là gì?",
        "expected_keywords": ["24 tháng", "1 đổi 1", "30 ngày", "nhà sản xuất"],
        "expected_document": "Chính Sách Bảo Hành Thiết Bị",
        "should_fallback": False,
    },
    {
        "id": "DOC-02",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "RETAIL",
        "question": "Khách hàng mua hàng tại cửa hàng có được đổi trả trong bao nhiêu ngày?",
        "expected_keywords": ["07 ngày", "tem mác", "hộp"],
        "expected_document": "Chính Sách Bán Hàng Và Đổi Trả",
        "should_fallback": False,
    },
    {
        "id": "DOC-03",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "RETAIL",
        "question": "Khách hàng VIP được hưởng những quyền lợi chiết khấu và giao hàng như thế nào?",
        "expected_keywords": ["10%", "chiết khấu", "15km"],
        "expected_document": "Quy Chế Khách Hàng VIP",
        "should_fallback": False,
    },
    {
        "id": "DOC-04",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "RETAIL",
        "question": "Quy định số lượng sản phẩm mua tối đa trong chương trình Flash Sale là bao nhiêu?",
        "expected_keywords": ["02 sản phẩm", "Flash Sale"],
        "expected_document": "Cẩm Nang Khuyến Mãi Flash Sale",
        "should_fallback": False,
    },
    {
        "id": "DOC-05",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "SERVICE",
        "question": "Cam kết thời gian phản hồi và xử lý cho sự cố mức độ Critical là bao lâu?",
        "expected_keywords": ["15 phút", "02 giờ", "Critical"],
        "expected_document": "Cam Kết Mức Độ Dịch Vụ Kỹ Thuật SLA",
        "should_fallback": False,
    },
    {
        "id": "DOC-06",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "SERVICE",
        "question": "Yêu cầu kiểm tra an toàn và thử tải sau khi lắp đặt máy chủ là gì?",
        "expected_keywords": ["24 giờ", "UPS", "ESD", "65 độ C"],
        "expected_document": "Quy Trình Lắp Đặt Máy Chủ Và Mạng",
        "should_fallback": False,
    },
    {
        "id": "DOC-07",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "SERVICE",
        "question": "Khi chẩn đoán truy vấn chậm trong cơ sở dữ liệu PostgreSQL nên dùng công cụ nào?",
        "expected_keywords": ["pg_stat_statements", "EXPLAIN", "B-tree", "BRIN"],
        "expected_document": "Hướng Dẫn Tối Ưu Hóa PostgreSQL",
        "should_fallback": False,
    },

    # 2. Structured-business-only questions
    {
        "id": "DATA-01",
        "category": "STRUCTURED_ONLY",
        "workspace_type": "RETAIL",
        "question": "Tổng doanh thu và số đơn hàng hiện tại của doanh nghiệp là bao nhiêu?",
        "expected_keywords": ["doanh thu", "đơn hàng"],
        "expected_tool": "get_sales_summary",
        "should_fallback": False,
    },
    {
        "id": "DATA-02",
        "category": "STRUCTURED_ONLY",
        "workspace_type": "RETAIL",
        "question": "Hệ thống hiện đang quản lý bao nhiêu sản phẩm và danh mục nào?",
        "expected_keywords": ["sản phẩm", "kinh doanh"],
        "expected_tool": "get_product_catalog_summary",
        "should_fallback": False,
    },
    {
        "id": "DATA-03",
        "category": "STRUCTURED_ONLY",
        "workspace_type": "SERVICE",
        "question": "Tình hình phiếu yêu cầu kỹ thuật hiện tại: bao nhiêu ticket đang mở và bao nhiêu quá hạn SLA?",
        "expected_keywords": ["phiếu yêu cầu", "SLA"],
        "expected_tool": "get_service_ticket_summary",
        "should_fallback": False,
    },
    {
        "id": "DATA-04",
        "category": "STRUCTURED_ONLY",
        "workspace_type": "SERVICE",
        "question": "Đội ngũ kỹ thuật viên có bao nhiêu nhân sự đang sẵn sàng nhận việc?",
        "expected_keywords": ["kỹ thuật viên", "nhân sự", "sẵn sàng"],
        "expected_tool": "get_technician_workload_summary",
        "should_fallback": False,
    },

    # 3. Hybrid questions (Combines Document Policy + Structured Business Data)
    {
        "id": "HYB-01",
        "category": "HYBRID",
        "workspace_type": "RETAIL",
        "question": "Tổng doanh thu bán hàng hiện tại là bao nhiêu và chính sách bảo hành laptop quy định thế nào?",
        "expected_keywords": ["doanh thu", "24 tháng"],
        "expected_document": "Chính Sách Bảo Hành Thiết Bị",
        "expected_tool": "get_sales_summary",
        "should_fallback": False,
    },
    {
        "id": "HYB-02",
        "category": "HYBRID",
        "workspace_type": "SERVICE",
        "question": "Hiện có bao nhiêu ticket yêu cầu và cam kết thời gian xử lý sự cố khẩn cấp Critical là mấy giờ?",
        "expected_keywords": ["phiếu yêu cầu", "15 phút"],
        "expected_document": "Cam Kết Mức Độ Dịch Vụ Kỹ Thuật SLA",
        "expected_tool": "get_service_ticket_summary",
        "should_fallback": False,
    },

    # 4. Out-of-domain / Unsupported questions (Must return controlled fallback)
    {
        "id": "OOD-01",
        "category": "OUT_OF_DOMAIN",
        "workspace_type": "RETAIL",
        "question": "Giá cổ phiếu của Apple và Tesla trên sàn Nasdaq hôm nay là bao nhiêu?",
        "expected_keywords": [FALLBACK_NO_CONTEXT_MESSAGE],
        "should_fallback": True,
    },
    {
        "id": "OOD-02",
        "category": "OUT_OF_DOMAIN",
        "workspace_type": "SERVICE",
        "question": "Thời tiết ngày mai tại Paris có mưa hay có tuyết rơi không?",
        "expected_keywords": [FALLBACK_NO_CONTEXT_MESSAGE],
        "should_fallback": True,
    },
    {
        "id": "OOD-03",
        "category": "OUT_OF_DOMAIN",
        "workspace_type": "RETAIL",
        "question": "Thời tiết ngày mai tại Tokyo có nắng hay có mưa?",
        "expected_keywords": [FALLBACK_NO_CONTEXT_MESSAGE],
        "should_fallback": True,
    },
]


def run_benchmark_evaluation(workspace: Workspace, user: User) -> Dict[str, Any]:
    """
    Executes the benchmark evaluation against the active workspace.
    Computes Retrieval Relevance, Grounded Correctness, Citation Attribution,
    and Fallback Precision rates.
    """
    relevant_test_cases = [
        tc for tc in BENCHMARK_QUESTIONS
        if tc.get("workspace_type") == workspace.workspace_type or tc.get("category") == "OUT_OF_DOMAIN"
    ]

    total = len(relevant_test_cases)
    retrieval_successes = 0
    correctness_successes = 0
    citation_successes = 0
    fallback_successes = 0
    fallback_total = 0

    results_detail: List[Dict[str, Any]] = []

    for tc in relevant_test_cases:
        res = answer_grounded_query(
            workspace=workspace,
            user=user,
            message=tc["question"],
        )
        answer = res.get("answer", "")
        sources = res.get("sources", [])
        tools_used = [t["tool"] for t in res.get("tools_used", []) if t.get("status") == "SUCCESS"]

        # 1. Fallback validation
        if tc["should_fallback"]:
            fallback_total += 1
            is_fallback_correct = FALLBACK_NO_CONTEXT_MESSAGE in answer
            if is_fallback_correct:
                fallback_successes += 1
                correctness_successes += 1
            results_detail.append({
                "id": tc["id"],
                "passed": is_fallback_correct,
                "answer": answer[:80],
                "expected": FALLBACK_NO_CONTEXT_MESSAGE,
            })
            continue

        # 2. Retrieval Relevance
        has_retrieved_source = bool(sources) if "expected_document" in tc else False
        has_invoked_tool = (tc.get("expected_tool") in tools_used) if "expected_tool" in tc else False

        retrieval_ok = False
        if tc["category"] == "DOCUMENT_ONLY":
            retrieval_ok = has_retrieved_source
        elif tc["category"] == "STRUCTURED_ONLY":
            retrieval_ok = has_invoked_tool
        elif tc["category"] == "HYBRID":
            retrieval_ok = has_retrieved_source or has_invoked_tool

        if retrieval_ok:
            retrieval_successes += 1

        # 3. Grounded Correctness
        answer_lower = answer.lower()
        matched_keywords = [kw for kw in tc["expected_keywords"] if kw.lower() in answer_lower]
        correct_ok = len(matched_keywords) >= 1

        if correct_ok:
            correctness_successes += 1

        # 4. Citation Accuracy
        citation_ok = True
        if "expected_document" in tc:
            doc_titles = [s["document_title"] for s in sources]
            citation_ok = any(tc["expected_document"].lower() in dt.lower() for dt in doc_titles)
            if citation_ok:
                citation_successes += 1

        results_detail.append({
            "id": tc["id"],
            "category": tc["category"],
            "retrieval_ok": retrieval_ok,
            "correct_ok": correct_ok,
            "citation_ok": citation_ok,
            "matched_keywords": matched_keywords,
            "answer_preview": answer[:100],
        })

    non_fallback_count = total - fallback_total

    metrics = {
        "total_evaluated": total,
        "document_and_data_cases": non_fallback_count,
        "out_of_domain_cases": fallback_total,
        "retrieval_relevance_rate": round(retrieval_successes / max(1, non_fallback_count) * 100, 1),
        "grounded_correctness_rate": round(correctness_successes / max(1, total) * 100, 1),
        "fallback_precision": round(fallback_successes / max(1, fallback_total) * 100, 1),
        "details": results_detail,
    }

    return metrics
