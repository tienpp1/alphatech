"""Explicit paragraph replacements after primary-source review; no DOCX edits."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root / 'docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md'
paragraphs = {
 '- **Thuật toán Gradient Tree Boosting': '- **Thuật toán Gradient Tree Boosting (XGBoost):** Chen & Guestrin [14] trình bày hệ thống tree boosting. Nguồn [15] trình bày LightGBM với GOSS/EFB, không phải bằng chứng XGBoost vượt mạng học sâu trên doanh thu của đồ án. Đồ án chọn XGBoost để thử nghiệm trên đặc trưng trễ/lịch; hiệu quả phải đo so với baseline cùng điều kiện.',
 '- **So sánh giữa XGBoost': '- **Đối chiếu các phương pháp dự báo:** M4 [16] ghi nhận kết quả tốt của phương pháp kết hợp và hybrid; không chứng minh XGBoost luôn tốt hơn LSTM trên chuỗi ngắn. Sách [17] và N-BEATS [18] là nguồn tham khảo phương pháp, không thay thế thực nghiệm đối chứng của đồ án. Chưa đo so sánh LSTM/N-BEATS hoặc chi phí GPU nên không công bố ưu thế tương ứng.',
 '- **Kiến trúc Dữ liệu Đa khách thuê': '- **Kiến trúc dữ liệu đa khách thuê:** [3], [4] là nguồn thảo luận kiến trúc SaaS. Trong đồ án, shared-schema với workspace_id là quyết định thiết kế để dùng chung hạ tầng; phải kiểm membership, quyền và phạm vi truy vấn. Chưa đo chi phí/hiệu năng giữa các kiến trúc nên không kết luận đây là lựa chọn tối ưu nhất cho mọi SME. Metadata nguồn [4] còn chờ xác minh trước bản nộp.',
 '- **Giao thức Đánh giá Chuỗi Thời gian': '- **Giao thức đánh giá chuỗi thời gian:** Đồ án dùng chronological split và chỉ tạo đặc trưng từ quá khứ, theo giao thức thực nghiệm đã công bố. Nguồn [19] nghiên cứu cách đánh giá chuỗi thời gian; không diễn giải thành lệnh cấm mọi dạng cross-validation trong mọi điều kiện. Phạm vi và giả định của nguồn cần đối chiếu trước khi trích dẫn sâu.',
}
lines = p.read_text(encoding='utf-8').splitlines()
for prefix, replacement in paragraphs.items():
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    assert len(matches) == 1, prefix
    lines[matches[0]] = replacement
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
p = root / 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md'
lines = p.read_text(encoding='utf-8').splitlines()
for i, line in enumerate(lines):
    if line.startswith('| **Batch 50** |'):
        lines[i] = '| **Batch 50 — kết luận đóng đã thu hồi** | 23/09/2026 | Đã viết hồ sơ hành chính, phân loại SOP và runbook production. Test nội dung tài liệu không chứng minh deploy, CI, email, Sentry, restore hoặc secret rotation. Nội dung lịch sử giữ tại ACCEPTANCE_BATCH_50.md; trạng thái từng mục theo ledger. | **3, 6, 47, 90–97** | ACCEPTANCE_BATCH_50.md |'
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Corrected unsupported comparative conclusions; bibliography gate remains open.')
