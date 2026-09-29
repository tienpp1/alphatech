"""Human-authored RAG cases kept separate from the router/rubric benchmark."""

from apps.knowledge.services import FALLBACK_NO_CONTEXT_MESSAGE


INDEPENDENT_BENCHMARK_QUESTIONS = [
    {
        "id": "IND-DOC-01",
        "category": "DOCUMENT_ONLY",
        "workspace_type": "RETAIL",
        "question": "Nếu màn hình laptop phát sinh lỗi sớm sau khi mua, tài liệu bảo hành nói thời hạn và phương án đổi máy ra sao?",
        "expected_keywords": ["24 tháng", "1 đổi 1"],
        "expected_document": "Chính Sách Bảo Hành Thiết Bị",
        "should_fallback": False,
    },
    {
        "id": "IND-DATA-01",
        "category": "STRUCTURED_ONLY",
        "workspace_type": "SERVICE",
        "question": "Hãy cho biết hiện còn bao nhiêu yêu cầu kỹ thuật đang mở và quá hạn.",
        "expected_keywords": ["phiếu yêu cầu", "SLA"],
        "expected_tool": "get_service_ticket_summary",
        "should_fallback": False,
    },
    {
        "id": "IND-HYB-01",
        "category": "HYBRID",
        "workspace_type": "RETAIL",
        "question": "Đối chiếu doanh thu hiện tại với điều khoản bảo hành laptop trong kho tài liệu.",
        "expected_keywords": ["doanh thu", "24 tháng"],
        "expected_document": "Chính Sách Bảo Hành Thiết Bị",
        "expected_tool": "get_sales_summary",
        "should_fallback": False,
    },
    {
        "id": "IND-OOD-01",
        "category": "OUT_OF_DOMAIN",
        "workspace_type": "RETAIL",
        "question": "Hãy dự báo giá vàng thế giới ngày mai và cho tôi lời khuyên đầu tư.",
        "expected_keywords": [FALLBACK_NO_CONTEXT_MESSAGE],
        "should_fallback": True,
    },
    {
        "id": "IND-MISSING-01",
        "category": "OUT_OF_DOMAIN",
        "workspace_type": "SERVICE",
        "question": "Cho tôi biết chính sách nội bộ chưa được nạp vào kho tri thức của doanh nghiệp.",
        "expected_keywords": [FALLBACK_NO_CONTEXT_MESSAGE],
        "should_fallback": True,
    },
]
