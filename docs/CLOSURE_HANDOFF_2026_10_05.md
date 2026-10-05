# Hướng dẫn xem gói đối chiếu đồ án — 05/10/2026

Đây là gói làm việc, không phải chứng nhận 97/97 hoặc toàn bộ production.
Tên đề tài: Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI.

## Xem theo thứ tự

1. CLOSURE_97_EVIDENCE_2026_10_05.md: từng tiêu chí, nguồn và giới hạn.
2. De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx: bản thầy duyệt nguyên trạng.
3. review.md: chủ dự án đã chấm5 câu ĐẠT lúc09:40 ngày05/10. review.json chứa
   đánh giá được xác nhận; review.initial.json giữ phiếu blank. Không dùng
   policy synthetic như chính sách thương mại thật.
4. FORECAST_INTEGRITY_2026_10_05.md: one-step/recursive và metric không tô hồng.
5. RELEASE_ACCEPTANCE_2026_10_04.md: UAT/restore/provider theo nguồn riêng.

Các JSON/CSV/model trong thư mục forecast là dữ liệu synthetic, không dữ liệu
khách hàng production. Không đưa .env, database dump, session/token hoặc mật
khẩu vào gói. Word giữ SHA256 đã xác nhận, không tự chỉnh bản duyệt.

## Demo an toàn

- Khách Google: dùng cổng public; thử truy cập nội bộ phải bị từ chối.
- ADMIN/MANAGER/EMPLOYEE: dùng tài khoản nội bộ riêng, đọc/mutation theo quyền.
- Demo đơn/dịch vụ: ưu tiên dữ liệu local; production TEST cũ đã hủy, không dùng
  tài khoản khác hoặc đơn thật để tạo lại bằng chứng ăn mừng.
- Chat/bản tin: polling 3 giây được ghi đúng, không tuyên bố WebSocket realtime.
- RAG offline: công bố mode deterministic/no-context; không giả Gemini live.
- Forecast: chỉ metric trên dữ liệu/split/origin đã lưu; không cam kết vượt baseline.
- Restore: dùng hồ sơ diễn tập đã có, không chạy lại/reset database để trình diễn.

## Những việc cần chủ dự án

Chủ dự án xác nhận chưa có báo cáo/slide cuối khác: **chưa nghiệm thu bản nộp cuối**.
Gửi bản cuối khi có để rà sơ đồ/trích dẫn/claims. Bộ IND đã tách từ trước nhưng được dùng để repair
trong đợt này: không gọi là holdout mù độc lập. Muốn đánh giá khả năng tổng quát
cần câu hỏi do reviewer giữ riêng, chưa dùng để sửa router/prompt.

Các lựa chọn Local Storage, async production tắt và offsite backup hoãn được
giữ. Chúng có thể là quyết định phạm vi đồ án, không trở thành PASS production.
Email/Sentry/GPS user-confirmed vẫn giữ nguồn Human Evaluation. Nếu bảo vệ ở
mức đồ án, trình bày đúng giới hạn; nếu tuyên bố production certification, phải
có thêm bằng chứng tương ứng thay vì đổi nhãn các cổng.
