# Hướng dẫn nội bộ: nhập dữ liệu và mapping

Phạm vi: hướng dẫn từ apps/integration/services.py, apps/mapping/services.py và AGENTS.md, bản 09/10/2026. Không chứa endpoint, token hoặc dữ liệu khách hàng thật.

## Import thành công có nghĩa đã cập nhật dữ liệu bán hàng không?

Import đọc dữ liệu vào staging RawImportRecord; không mặc định đã ghi vào model canonical như Product, Customer hoặc Order. Cần profile mapping, preview, validation và thao tác apply được cấp quyền. Giữ phân biệt số dòng đọc, dòng hợp lệ và dòng thực sự áp dụng. Không báo doanh thu mới chỉ vì file CSV đã tải lên thành công.

## Cần chuẩn bị file import thế nào?

Luồng upload hỗ trợ csv, xlsx và xls với giới hạn kích thước hiện tại 10 MB. Kiểm tra header, kiểu dữ liệu, mã định danh, ngày tháng, đơn vị tiền và dữ liệu thiếu trước preview. File hợp lệ về phần mở rộng chưa chứng minh nội dung đúng nghiệp vụ. Không đổi đuôi file để vượt validation; ưu tiên mẫu nhỏ không chứa thông tin cá nhân khi chẩn đoán.

## AI gợi ý mapping có được tự áp dụng không?

AI mapping rule có thể apply không cần validation không? Không. Rule gợi ý phải được kiểm tra bằng preview và validation; apply cần quyền riêng. Chấp nhận gợi ý chưa có nghĩa dữ liệu đã được áp dụng.

Gợi ý AI không chứng minh field map hoặc transform đúng. Xem mẫu đầu vào/đầu ra, trường bắt buộc và validation canonical trước khi chấp nhận rule. Quyền đọc mapping, quản lý rule và apply là các quyền khác nhau. Không chạy mã Python tùy ý hoặc SQL lấy từ file nguồn để transform. Thiếu trường cần hỏi lại, không tự bịa ID khách hàng, chi nhánh hoặc workspace.

## Khi apply mapping lỗi thì cần cung cấp thông tin gì?

Ghi workspace, ImportJob/Profile ID, loại entity, số dòng lỗi, thông báo an toàn và một ví dụ đã bỏ PII. Kiểm tra related objects cùng workspace trước khi thử lại. Không xóa/reset database hoặc đánh dấu tất cả dòng VALID để bỏ qua lỗi. Không gửi connection_config, password, API key hoặc raw dữ liệu nhạy cảm trong hội thoại.
