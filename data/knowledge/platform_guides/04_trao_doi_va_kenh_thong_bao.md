# Hướng dẫn nội bộ: trao đổi và kênh thông báo

Phạm vi: hướng dẫn nền tảng, bản 09/10/2026. Nguồn: apps/notifications, apps/public_web/email_service.py, templates/notifications và docs/PROJECT_CONTEXT.md. Không chứa thông tin cá nhân hoặc credentials.

## Chat nhóm nội bộ hoạt động như thế nào?

Mở /noibo/trao-doi/ trong workspace đã được cấp quyền. Chat nhóm tự cập nhật bằng polling khoảng 3 giây, không phải WebSocket. Nội dung ở workspace khác không được hiển thị. Tab ẩn có thể tạm ngừng đồng bộ; mạng chậm có thể trì hoãn cập nhật. Không gửi lại liên tục khi chưa biết lần gửi trước thành công hay chưa, vì có nguy cơ trùng tin.

## Nhân viên có được đăng bản tin không?

Mở /noibo/bang-tin/ để đọc bản tin workspace. Đăng hoặc sửa phải có permission được server kiểm tra; quyền đọc không tự cấp quyền quản lý. Phiên bản nâng cấp local tự cập nhật feed khoảng 10 giây và giữ nội dung đang soạn. Local chưa deploy không chứng minh production có tính năng đó. Không dùng AI để đăng thay nếu thiếu quyền.

## Email lỗi có làm mất đơn hàng không?

Email là kênh riêng, không đồng nhất với thông báo nội bộ. Nghiệp vụ có thể đã ghi nhận trong khi thư gửi thất bại. Kiểm tra trạng thái gửi từng người nhận; backend chấp nhận thư chưa chứng minh thư đã đến Inbox. Không thông báo gửi thành công khi send trả 0 hoặc FAILED. Retry cần kiểm soát và không cho đổi người nhận tùy ý qua chức năng gửi lại.

## Khách hàng không thấy hiệu ứng cảm ơn thì kiểm tra gì?

Kiểm tra đúng chủ đơn/yêu cầu, trạng thái được xác nhận và thông báo chưa được acknowledge. Không đưa thông báo cho khách khác hoặc workspace khác. Hiệu ứng không phải bằng chứng đã thu tiền hoặc đã giao hàng. Test synthetic, UAT do người dùng xác nhận và kiểm chứng browser phải được ghi rõ loại bằng chứng, không gom thành một chứng nhận production.
