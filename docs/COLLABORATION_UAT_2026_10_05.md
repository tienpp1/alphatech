# Kiểm chứng chat và bản tin nội bộ — 05/10/2026

## Quan sát production trước bản sửa timestamp

Browser tại https://alphatech-26uv.onrender.com, khoảng 15:32–15:40
Asia/Bangkok. Người dùng tự đăng nhập lần lượt MANAGER và EMPLOYEE; không
đọc/đổi mật khẩu, membership hoặc tài khoản Google. Nội dung ghi rõ TEST, không
chính sách/chỉ thị/giao dịch. Đã tạo ba tin chat và một bản tin (ID 1) trong
abc-retail; không xóa bản ghi để che dấu vết kiểm thử.

| Kịch bản | Quan sát trực tiếp | Giới hạn |
|---|---|---|
| MANAGER gửi chat | Tin TEST xuất hiện, input được xóa | Không chứng nhận mọi lỗi mạng |
| MANAGER đăng bản tin | UI báo thành công, bản tin hiển thị tác giả/phạm vi | Chỉ một bản tin NORMAL |
| Workspace khác | Chat và bảng tin xyz-service trống, không hiện TEST abc-retail | Cả hai user có membership hai workspace; không phải thử user không có membership |
| Polling | Tab chờ nhận tin TEST-POLL không gọi reload/goto | Hai tab cùng phiên MANAGER, không hai phiên tài khoản độc lập |
| EMPLOYEE đọc/phản hồi | Thấy tin MANAGER và gửi TEST-EMPLOYEE thành công | Hai tài khoản kiểm theo thứ tự |
| EMPLOYEE đọc bản tin | Thấy bản tin, không có nút đăng hoặc sửa | Không gửi POST mutation trái quyền trên production |
| Server authorization | GET URL sửa bản tin 1 hiện 403 Forbidden | Không thay kết quả automated mutation tests bằng GET UAT |

Ảnh local: `output/uat_collaboration_20261005/`: manager_chat.jpg,
manager_bulletin.jpg, xyz_chat_absent.jpg, xyz_bulletin_absent.jpg,
poll_observer_no_reload.jpg, employee_chat_reply.jpg,
employee_bulletin_readonly.jpg, employee_bulletin_edit_denied.jpg.
Không dùng ảnh đăng nhập hoặc chụp mật khẩu/token.

## Lỗi phát hiện và repair

HTML ban đầu hiển thị 15:34 trong khi tin qua polling hiển thị 08:34:
API strftime trực tiếp timestamp UTC, template đổi sang timezone hiện hành.
Send API không trả created_at nên bên gửi hiển thị “Vừa xong”.

`apps/notifications/views.py` dùng timezone.localtime trước định dạng ở cả
poll và send. Format giữ H:i d/m; send bổ sung created_at tương thích với JS
đang đọc field này. Không đổi model, DB timestamp, schema, role hoặc nhịp poll.
Hai test mới kiểm UTC 23:58 ngày 04/10 thành 06:58 ngày 05/10 ở Việt Nam, cùng
send/poll/HTML; active UTC phải giữ 23:58, không hard-code múi giờ Việt Nam.

## Validation / phát hành

Local: bốn module chat/bản tin chạy qua manage.py test với
config.settings_evidence_test: 35 tests/333.401s OK. Snapshot staged tree
aaaab0622afd185c5622e7a79361e669d7479216 chạy lại bảy module (bốn collaboration,
ba academic contracts): 47 tests/14.718s OK, test-process fast hasher, database
test riêng được tạo/hủy; không reset database nghiệp vụ. manage.py check và
makemigrations --check --dry-run đều exit 0, không migration mới.

Đã push commit 0c618c74aeb839952f6e210b02e5f3c751ca182b. Render deploy
dep-db1mb8vavr4c73ckipfg live đúng SHA. Sau deploy, lúc 15:58 ngày 05/10,
EMPLOYEE gửi thêm TEST-UAT-TIME: bên gửi, tab chờ qua polling không reload,
và HTML sau reload đều hiển thị 15:58 05/10. Không còn UTC 08:58 hoặc
placeholder “Vừa xong”. Ảnh chat_timestamp_after_deploy.jpg. Tổng dữ liệu TEST
đợt này là bốn tin chat và một bản tin; không xóa hoặc thay dữ liệu nghiệp vụ.

Kiểm tra lại ngày 06/10 sau khi máy tắt: CI run 37286413162 completed/success
đúng SHA 0c618c74aeb839952f6e210b02e5f3c751ca182b. Tất cả bước job
111686258724 success, gồm academic contracts, internal collaboration,
dependency audit, static scan, coverage gate và HTTPS/email/deployment tests.
Render vẫn live cùng SHA. Không chạy lại hoặc tạo thêm TEST chỉ để lấy lại ảnh.
Ghi nhận sau deploy này là tài liệu local, không giả là nằm trong commit đã test.
Full1201/CI ea18f14 của release trước không hồi gán cho source mới.
Không sửa tiến độ/cấu trúc checklist 97 hoặc bản Word duyệt.
