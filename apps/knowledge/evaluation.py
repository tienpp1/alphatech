"""
Evaluation Benchmark Dataset and Automated Metrics Evaluator for Grounded RAG Assistant.
Contains 16 curated test cases across 4 categories:
1. Document-only questions
2. Structured-business-only questions
3. Hybrid questions
4. Out-of-domain / Unsupported questions (Fallback validation)
"""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, List
from django.core.exceptions import PermissionDenied
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


def _benchmark_error_code(error):
    """Return a stable, non-sensitive error code for an evaluation case."""
    if isinstance(error, PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(error, TimeoutError):
        return "PROVIDER_TIMEOUT"
    if isinstance(error, (ConnectionError, OSError)):
        return "PROVIDER_CONNECTION"
    return "BENCHMARK_EXECUTION_ERROR"


def run_benchmark_evaluation(
    workspace: Workspace,
    user: User,
    *,
    capture_errors: bool = False,
    cases=None,
) -> Dict[str, Any]:
    """Run the existing assistant and report a lexical/evidence proxy, not accuracy.

    This calls real application services and may persist conversations or invoke
    providers. Use an isolated benchmark database; this is not a read-only export.
    Exceptions propagate; failed execution must not be reported as a passing case.
    """
    from apps.knowledge.evaluation_scoring import score_case, summarize

    benchmark_cases = BENCHMARK_QUESTIONS if cases is None else cases
    relevant_test_cases = [
        tc for tc in benchmark_cases
        if tc.get("workspace_type") == workspace.workspace_type or tc.get("category") == "OUT_OF_DOMAIN"
    ]
    details = []
    for case in relevant_test_cases:
        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        metadata = {
            "status": "SCORED",
            "evaluated_at": started_at.isoformat(),
        }
        try:
            response = answer_grounded_query(workspace=workspace, user=user, message=case["question"])
        except Exception as error:
            # The default remains fail-fast for callers that use the benchmark
            # as a guard. Evidence exports can opt in to a complete per-case
            # ledger without treating provider failures as passes.
            if not capture_errors:
                raise
            metadata.update({
                "status": "ERROR",
                "error_code": _benchmark_error_code(error),
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            })
            details.append(score_case(case, {}, FALLBACK_NO_CONTEXT_MESSAGE, metadata))
            continue
        metadata["duration_ms"] = round((perf_counter() - started) * 1000, 3)
        details.append(score_case(case, response, FALLBACK_NO_CONTEXT_MESSAGE, metadata))
    return summarize(details)
