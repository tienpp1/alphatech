"""Repository SOP cases with source-grounded text, not approved business policy.

These cases are an input contract for future RAG evaluation. They deliberately
do not claim that an answer was retrieved or semantically judged at runtime.
"""


REPOSITORY_SCOPE_CASES = (
    {
        "id": "SCOPE-RET-RMA-01",
        "workspace_code": "abc-retail",
        "source_path": "data/knowledge/SOP_RETAIL_RMA_WARRANTY_2026.md",
        "question": "Laptop lỗi phần cứng trong 72 giờ đầu thì chính sách đổi trả ra sao?",
        "required_facts": ("72 giờ", "30 phút", "trên 07 ngày làm việc"),
    },
    {
        "id": "SCOPE-RET-BOPIS-01",
        "workspace_code": "abc-retail",
        "source_path": "data/knowledge/SOP_OMNICHANNEL_FULFILLMENT_2026.md",
        "question": "Đơn BOPIS được giữ bao lâu và hoàn tiền khi hủy như thế nào?",
        "required_facts": ("48 giờ", "hoàn tiền 100%", "24 giờ làm việc"),
    },
    {
        "id": "SCOPE-RET-FRAUD-01",
        "workspace_code": "abc-retail",
        "source_path": "data/knowledge/SOP_RETAIL_PROMO_FRAUD_2026.md",
        "question": "Khi nào đơn hàng bị Fraud Hold và quy tắc ưu đãi nhân viên là gì?",
        "required_facts": ("Fraud Hold", "15 phút", "90 ngày"),
    },
    {
        "id": "SCOPE-RET-TRADEIN-01",
        "workspace_code": "abc-retail",
        "source_path": "data/knowledge/SOP_RETAIL_TRADE_IN_2026.md",
        "question": "Quy trình thu cũ đổi mới xử lý dữ liệu máy cũ như thế nào?",
        "required_facts": ("Factory Data Reset", "xóa sạch dữ liệu 100%"),
    },
    {
        "id": "SCOPE-SVC-SLA-01",
        "workspace_code": "xyz-service",
        "source_path": "data/knowledge/SOP_SERVICE_OPS_INCIDENT_SLA_2026.md",
        "question": "Sự cố P1 có SLA phản hồi và MTTR như thế nào?",
        "required_facts": ("15 phút", "02 giờ"),
    },
    {
        "id": "SCOPE-SVC-RANSOMWARE-01",
        "workspace_code": "xyz-service",
        "source_path": "data/knowledge/SOP_CYBERSECURITY_INCIDENT_DRP_2026.md",
        "question": "Khi phát hiện ransomware, kỹ sư phải làm gì trước tiên?",
        "required_facts": ("No-Reboot Rule", "Ngắt đường truyền Internet Gateway"),
    },
    {
        "id": "SCOPE-SVC-CHANGE-01",
        "workspace_code": "xyz-service",
        "source_path": "data/knowledge/SOP_SVC_CHANGE_MANAGEMENT_2026.md",
        "question": "Thay đổi production cần CAB và rollback trong bao lâu?",
        "required_facts": ("48 giờ", "15 phút", "CHANGE FREEZE WINDOW"),
    },
    {
        "id": "SCOPE-SVC-DECOMMISSION-01",
        "workspace_code": "xyz-service",
        "source_path": "data/knowledge/SOP_SVC_ASSET_DECOMMISSION_2026.md",
        "question": "Tiêu hủy ổ đĩa theo tiêu chuẩn nào và ngưỡng kỹ thuật ra sao?",
        "required_facts": ("NIST SP 800-88", "10,000 Gauss", "2mm"),
    },
    {
        "id": "SCOPE-CORE-HOURS-01",
        "workspace_code": "shared",
        "source_path": "data/knowledge/SOP_CORE_WORKING_HOURS_LEAVE_2026.md",
        "question": "Giờ làm việc, ân hạn đi muộn và phép năm được quy định thế nào?",
        "required_facts": ("08:00", "17:30", "12 ngày phép"),
    },
    {
        "id": "SCOPE-CORE-EXPENSE-01",
        "workspace_code": "shared",
        "source_path": "data/knowledge/SOP_CORE_EXPENSE_TRAVEL_REIMBURSEMENT_2026.md",
        "question": "Định mức công tác phí và hạn quyết toán là bao lâu?",
        "required_facts": ("350,000 VNĐ", "07 ngày làm việc"),
    },
)

# Keep the historical import compatible, without implying commercial approval.
APPROVED_SCOPE_CASES = REPOSITORY_SCOPE_CASES
from .sop_catalog import PRIMARY_SOPS

PRIMARY_SCOPE_CASES = tuple(case for case in REPOSITORY_SCOPE_CASES
                           if case['source_path'].rsplit('/', 1)[-1] in PRIMARY_SOPS)
SUPPLEMENTARY_SCOPE_CASES = tuple(case for case in REPOSITORY_SCOPE_CASES
                                 if case not in PRIMARY_SCOPE_CASES)
