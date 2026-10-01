# Đối chiếu và sửa sau thay đổi của agent — 30/09/2026

## Kết quả có thể kiểm tra

- Checklist được phục hồi từ bản Git trước khi hỏng: 97 dòng, 97 ID duy nhất từ 1 đến 97. Không đổi tiêu chí hoặc đánh số lại.
- Trang AI Command Center và WebSocket dùng quyền telemetry hiện có; chặn customer, tài khoản không active và thiếu permission. Socket nạp lại user/quyền mỗi lần gửi để áp dụng thu hồi; Origin được kiểm tra ở ASGI.
- Dữ liệu DEMO có nhãn cả payload và giao diện. Giao diện tiếng Việt không phụ thuộc CDN; biểu đồ SVG có bảng dữ liệu tương đương, nút tạm dừng và thông báo kết nối thất bại. Không gán số mô phỏng thành độ chính xác AI hoặc doanh thu.
- Khai báo Channels/Daphne trong requirements; thêm regression vào CI thay bước test bị lặp, không hạ coverage gate.
- Backup SQL giữ nguyên trên máy và được ignore khỏi Git. Không chạy restore.

## Xác nhận trực tiếp của chủ dự án trong hội thoại 30/09

- Mục 91: Chủ dự án xác nhận đã nhận email thật cho tạo tài khoản, chốt đơn hàng, cập nhật dịch vụ, khách liên hệ; mô tả dùng Gmail SMTP. Chấp nhận theo xác nhận chủ dự án, không phải agent đã đọc inbox hay kiểm tra message ID/release hiện tại.
- Mục 94: Chủ dự án xác nhận tự cấu hình DSN trên Render và thấy Error Events tại Sentry.io. Chấp nhận theo xác nhận chủ dự án, không có Event ID/timestamp để agent kiểm tra độc lập.
- Mục 57: Chủ dự án xác nhận GPS trên điện thoại và fallback/thông báo đúng khi từ chối quyền. Chưa có đối chiếu sai số lớn, vị trí thực/accuracy; giữ phần còn thiếu trong tiêu chí gốc.
- Mục 93: Chủ dự án yêu cầu nghiệm thu cấu hình và local test vì repo private. Chấp nhận phần local theo phạm vi này; không suy ra GitHub Actions PASS hoặc 100% coverage. Private repo không tự chứng minh thành công hay thất bại.
- Mục 96: Chủ dự án tiếp tục HOÃN VÔ THỜI HẠN, không thiết lập sandbox. Đây là quyết định không thực hiện, không phải restore đã pass. Không chạy lệnh khôi phục.

## Phần còn cần bằng chứng

### Tiếp tục kiểm chứng ngày 30/09

- Worker: sửa lỗi import model trước Django setup ở tiến trình spawn/forkserver. Tiến trình con đóng kết nối DB kế thừa, dừng có timeout và kill khi không đáp ứng. Không thay mô hình hàng đợi hoặc database schema.
- `tests.test_forecast_worker_process tests.test_forecasting_queue tests.test_forecasting_training` trên PostgreSQL evidence cô lập: **16/16 OK, 20.667s**. Bao gồm import trong Python process mới, lease hết hạn, fencing worker cũ, giới hạn retry, cancellation và training. Đây là kiểm thử local; không dùng để xác nhận worker Render đã chạy.
- Quét lịch sử Git đọc-only: **32 commit reachable local, 0 finding** theo các mẫu secret hiện có; `output/secret_history_20260930.json`. Không quét blob binary/unreachable objects, không chứng nhận rotation tại provider.
- `git ls-remote origin HEAD` thất bại kết nối github.com:443 sau 21 giây. Chưa push/deploy hoặc đối chiếu SHA remote được. Không thay URL remote hay credentials để né lỗi mạng.

39: người chấm thật hoàn tất packet đúng/đủ ngữ nghĩa; agent không tự ký thay.
57: kiểm thử sai số/vị trí thật và lỗi không lấy được vị trí.
90: SHA deploy khớp release được test.
92: log worker database queue/lease/recovery thực tế; log Redis hiện có chưa khớp mã.
93: remote CI/artifact chưa được kiểm chứng; local được chủ dự án chấp nhận riêng.
95: header/cookie/CSP trên deployment chưa đọc được do network timeout.
96: hoãn vô thời hạn theo chủ dự án.
97: quét release và quản lý backup đã có; chưa kiểm chứng toàn bộ lịch sử Git/provider rotation độc lập.

## Kiểm thử

- `python manage.py test tests.test_command_center_security tests.test_rag_human_review tests.test_release_secret_scan --settings=config.settings_evidence_test --noinput`: 17/17 OK, 4.858s.
- `python manage.py test tests.test_command_center_security tests.test_noibo_empty_state_and_boundary tests.test_provider_http_boundary --settings=config.settings_evidence_test --noinput`: 21/21 OK, 58.056s. Các lượt có test trùng, không cộng thành 38 test riêng.
- Bandit apps/config, chỉ loại migrations như CI: 0 finding (`output/bandit_repair_20260930.json`).
- Django check: 0 lỗi. Migration drift: No changes detected; kiểm tra lịch sử migration remote gặp connection timeout, chưa chứng nhận DB production.
- Không chạy full suite; không push/deploy bản mới trong đợt này. Các xác nhận của chủ dự án nói về bản đã chạy, không suy rộng sang bản sửa local.
- Chrome qua Playwright, trang template đã render: 1440px và 375px, reduced-motion; nút pause hoạt động, không tràn ngang, không có pageerror. Ảnh đã mở kiểm tra trực quan tại `output/command_center_qa/demo-1440.png` và `demo-375.png`. Đây là visual QA trên template, không phải nghiệm thu đăng nhập/WebSocket production.
- Sau thay template bỏ CDN: chạy lại `tests.test_command_center_security` bằng evidence settings: 7/7 OK, 4.008s. Secret scanner cuối: 773 file, 0 finding, không chứng nhận lịch sử Git/rotation. `git check-ignore backup_ai_business.sql` xác nhận backup được ignore.
