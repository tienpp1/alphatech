# Chat nhóm và bản tin tự cập nhật trên Render Free

## Phạm vi và kế hoạch đã thực hiện

Source đã có TeamChatMessage, InternalBulletin, API, màn hình và migration
notifications/0003. Không tạo lại model hoặc thêm quyền song song. Chủ dự án
chọn hoàn thiện chat nhóm và bản tin tự cập nhật trên hạ tầng hiện tại,
không chuyển WebSocket hoặc bổ sung chat riêng trong đợt này.

1. Rà source/routes/migration/test, bảo toàn workspace và Google/customer boundary.
2. Sửa cursor phân trang chat theo ID, không theo timestamp.
3. Tách client chat ra static JS, giữ bản nháp nếu chưa xác nhận gửi thành công;
   single-flight polling/timeout, không tự replay POST, phục hồi khi online.
4. Thêm polling bản tin bằng API hiện có, chỉ thay feed, không thay form soạn.
5. Bổ sung test backend và JavaScript, kiểm browser synthetic local và schema gate.

## Hành vi

- Chat: GET mỗi 3 giây khi tab đang hiện; timeout 15 giây và thử lại sau lỗi.
  Backlog 50 tin được đọc tiếp theo trang. Tin gửi thành công hiển thị ngay,
  nhưng không đẩy cursor đọc qua tin của người khác chưa đồng bộ.
- Không gửi POST tự động lần hai sau timeout. Provider response chưa xác nhận
  có thể đã ghi dữ liệu: người dùng cần kiểm kênh trước khi gửi lại.
- Bản tin: GET mỗi 10 giây khi tab đang hiện. Thay nội dung khi snapshot thay
  đổi, giữ bản tin cũ khi lỗi. Giữ priority filter, pinned/urgent và quyền sửa.
- 401/403 hoặc redirect đăng nhập dừng đồng bộ, không hiện là đã kết nối.
- Dùng textContent, không ghép HTML từ tên/nội dung do người dùng nhập.
- Danh sách đồng nghiệp là thành viên được cấp quyền, không tuyên bố presence
  online. Không có read receipt, typing indicator, DM hoặc upload đính kèm.
- Polling là gần thời gian thực, không tức thời tuyệt đối; server Free ngủ hoặc
  mạng lỗi có thể làm chậm hơn. Không thêm Redis, worker, schema hay migration.

## Kiểm chứng local

38 tests / 12.565s OK:
tests.test_bulletin_and_team_chat, tests.test_bulletin_update,
tests.test_collaboration_workspace_selection, tests.test_team_chat_display_time.
Test thêm chứng minh 55 tin có timestamp đảo thứ tự vẫn phân trang đủ theo ID.

`node scripts/test_internal_collaboration_js.cjs`: 5 nhóm PASS — cursor/order/
dedupe; giữ draft khi send lỗi và không replay; không poll chồng; pause hidden/
stop revoked access; escaping/control EMPLOYEE/giữ bulletin feed khi lỗi.
Đây là fake transport/minimal DOM, không chứng nhận production hoặc browser thật.

Browser local tại 127.0.0.1:8023 dùng DB test mới và fixture DEMO riêng:
gửi tin chứa thẻ HTML được hiển thị dạng văn bản; phản hồi EMPLOYEE từ HTTP
session khác; bản tin mới xuất hiện qua poll mà không reload hoặc mất draft
trong modal. Chat viewport 375px: sidebar hidden, document scrollWidth 362px,
không tràn ngang. Desktop được kiểm riêng. Ảnh trong output/collaboration_20261009/.
Preview không sửa database nghiệp vụ. Dữ liệu preview disposable được dọn sau test.

`check` 0 issues; `makemigrations --check --dry-run`: No changes detected trên
DB test mới. Syntax check cả hai script và scoped git diff --check đạt.

Lần test đầu: một assertion mới bắt nhầm setInterval của notification bell ở
base template; đã giới hạn kiểm tra vào template chat, không sửa test cũ.
Preview đầu thiếu email riêng cho hai fixture, bị unique constraint chặn;
đã dùng email synthetic khác nhau, không thay constraint hoặc dữ liệu thật.

Bản nâng cấp chưa push/deploy. UAT local không thay bằng chứng release trước,
không thay tiến độ hoặc cấu trúc checklist 97 đã chốt.
