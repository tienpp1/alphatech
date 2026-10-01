# Cổng đóng các cụm việc còn mở

Nguồn trạng thái duy nhất: CHECKLIST_97_PROGRESS.md. Bảng cũ ghi hoàn thành
97/97 từ runbook đã bị thu hồi. Không dùng số test hoặc số tài liệu để tính tiến độ.
Biên niên các đợt không thay thế nghiệm thu hiện hành.

| Mục | Điều kiện tiếp theo |
|---|---|
| 7, 11, 13 | Đối chiếu bản nộp và tài liệu hiện hành; xem ACCEPTANCE_BATCH_2026_09_25_CLAIMS.md. |
| 39 | Chấm đúng/đủ ngữ nghĩa: packet 25/09 có 4 câu trả lời, 2 ca từ chối tách riêng, chưa có điểm người chấm. |
| 46 | Đã đóng bằng ranh giới không công bố: chưa có chính sách bên ngoài được duyệt, mọi kênh công khai không khẳng định mốc demo. |
| 56 | Đã đóng bằng truy vấn Nominatim thật trên deployment ngày 26/09; xem `PRODUCTION_OSM_EVIDENCE_2026_09_26.md`. |
| 57 | Cần GPS/độ chính xác trên thiết bị thật; mock hoặc OSM không thay bằng chứng này. |
| 89 | Đã đóng: kiểm 12/12 nguồn, chuẩn hóa bản Word riêng và render 16/16 trang; xem `IEEE_AND_SUBMISSION_AUDIT_2026_09_26.md`. |
| 90 | Commit triển khai khớp commit đã nghiệm thu. |
| 91 | Đóng theo xác nhận chủ dự án 30/09: nhận email thật cho 4 sự kiện; chưa đối chiếu message ID/release mới độc lập. |
| 92 | Worker/restart/recovery thực tế trên deployment. |
| 93 | Chủ dự án chấp nhận cấu hình/local test; remote CI chưa kiểm chứng. Workflow không phải log thực thi. |
| 94 | Đóng theo xác nhận chủ dự án 30/09: thấy Error Events thật tại Sentry sau cấu hình Render; chưa có Event ID để đối chiếu độc lập. |
| 95 | HTTPS/cookie/CSP enforcement trên deployment. |
| 96 | HOÃN VÔ THỜI HẠN theo xác nhận 30/09. Đã có dump SQL, chưa restore; không chạy sandbox hay production restore. Không tính là test thành công. |
| 97 | Rotation/provider/deployment evidence; scanner local không chứng nhận lịch sử Git hoặc rotation. |

Giữ nguyên ID và tiêu chí gốc. Không thay chính sách, tạo dịch vụ trả phí hoặc
khôi phục database để vượt điều kiện đang thiếu bằng chứng.
