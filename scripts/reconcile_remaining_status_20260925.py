"""Bounded mechanical correction of stale current-status narratives."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / 'docs/NEXT_CLOSURE_GATES.md'
p.write_text('''# Cổng đóng các cụm việc còn mở

Nguồn trạng thái duy nhất: CHECKLIST_97_PROGRESS.md. Bảng cũ ghi hoàn thành
97/97 từ runbook đã bị thu hồi. Không dùng số test hoặc số tài liệu để tính tiến độ.
Biên niên các đợt không thay thế nghiệm thu hiện hành.

| Mục | Điều kiện tiếp theo |
|---|---|
| 7, 11, 13 | Đối chiếu bản nộp và tài liệu hiện hành; xem ACCEPTANCE_BATCH_2026_09_25_CLAIMS.md. |
| 39 | Chấm đúng/đủ ngữ nghĩa: packet 25/09 có 4 câu trả lời, 2 ca từ chối tách riêng, chưa có điểm người chấm. |
| 46 | Cần chính sách được người có thẩm quyền duyệt; bản AI dò code không phải phê duyệt kinh doanh. |
| 56, 57 | Tìm địa chỉ trên deployment và GPS/độ chính xác trên thiết bị thật; mock không thay bằng chứng này. |
| 89 | Kiểm từng trích dẫn IEEE và kết luận được nguồn hỗ trợ. |
| 90 | Commit triển khai khớp commit đã nghiệm thu. |
| 91 | OAuth HTTPS và inbox thực tế gắn release, môi trường, thời điểm. |
| 92 | Worker/restart/recovery thực tế trên deployment. |
| 93 | URL CI run PASS đúng commit; workflow không phải log thực thi. |
| 94 | Sentry/OTLP live event; SDK không thay bằng chứng nhận sự kiện. |
| 95 | HTTPS/cookie/CSP enforcement trên deployment. |
| 96 | HOÃN: pg_dump → pg_restore trên sandbox; TEMPLATE clone/runbook không đủ. |
| 97 | Rotation/provider/deployment evidence; scanner local không chứng nhận lịch sử Git hoặc rotation. |

Giữ nguyên ID và tiêu chí gốc. Không thay chính sách, tạo dịch vụ trả phí hoặc
khôi phục database để vượt điều kiện đang thiếu bằng chứng.
''', encoding='utf-8')

changes = {
 'HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md': {
  '**Trạng thái phê duyệt:** ĐÓNG HOÀN TOÀN (CLOSED)': '**Trạng thái:** RUNBOOK — các cổng 90–97 chưa đủ bằng chứng vận hành thật.',
  'Hệ thống AlphaTech AI Business Platform được thiết kế theo mô hình **Modular Monolith** hiện đại, tối ưu hóa chi phí vận hành và tính sẵn sàng cao cho doanh nghiệp vừa và nhỏ:': 'Hệ thống dùng **Modular Monolith**. Danh sách và sơ đồ dưới đây là cấu hình tham chiếu, không phải inventory deployment đã xác minh. PostgreSQL 18/PostGIS 3.6 local không chứng minh phiên bản trên Render; vùng máy chủ, worker và exporter cần kiểm riêng:',
  'Brevo (Sendinblue) Transactional API / SMTP Relay qua cổng TLS 587.': 'Brevo HTTPS Transactional API cho Render Free; SMTP chỉ là lựa chọn khác khi môi trường hỗ trợ.',
 },
 'HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md': {
  '**Trạng thái phê duyệt:** ĐÓNG HOÀN TOÀN (CLOSED)': '**Trạng thái:** Bằng chứng local kế thừa cho Gate 73; không phải nghiệm thu production. Đọc ledger hiện hành.',
 },
 'HO_SO_RA_SOAT_TAI_LIEU_SOP_VA_TRONG_TAM_NGHIEP_VU.md': {
  '**Trạng thái phê duyệt:** ĐÓNG HOÀN TOÀN (CLOSED)': '**Trạng thái:** Đã phân loại ngữ liệu Gate 47; không phải chính sách doanh nghiệp được duyệt (Gate 46 vẫn mở).',
 },
}
for name, pairs in changes.items():
    p = root / 'docs' / name
    text = p.read_text(encoding='utf-8')
    for old, new in pairs.items():
        assert old in text or new in text, name
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
print('Corrected four status/runbook documents; no business data changed.')
