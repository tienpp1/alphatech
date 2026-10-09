# Hướng dẫn nội bộ: tiếp nhận dịch vụ và chẩn đoán

Phạm vi: hướng dẫn từ apps/service_ops/services.py, apps/knowledge/tools.py và docs/PROJECT_CONTEXT.md, bản 09/10/2026. Không cam kết lịch trực, thời hạn SLA hoặc đơn giá.

## Tiếp nhận yêu cầu khác hoàn thành dịch vụ thế nào?

Yêu cầu khách gửi được ghi nhận trước khi phân công và xử lý. Không tuyên bố đã có kỹ thuật viên tới nơi hoặc đã khắc phục chỉ vì tạo ticket. Request, task, schedule và labor entry là các entity khác nhau; cần đúng quyền và workspace cho từng thao tác. Email xác nhận là kênh riêng, không chứng minh task đã hoàn thành.

## Ticket thiếu deadline thì có được tính đạt SLA không?

Thiếu deadline được ghi UNKNOWN, không tự tính là đúng hạn. Tỷ lệ SLA chỉ sử dụng các ticket có đủ dữ liệu đánh giá và phải nêu số unknown/evaluated. Số liệu sức khỏe hiện tại không phải chứng nhận tuân thủ hợp đồng cuối kỳ. Nếu không có hợp đồng hoặc lịch trực đã xác minh, không hứa phản hồi 15 phút hoặc bồi hoàn cụ thể.

## Muốn giải thích nguyên nhân sự cố cần dữ liệu gì?

Cần mã ticket, thời điểm, hệ thống bị ảnh hưởng, triệu chứng, log đã làm sạch và thao tác vừa thực hiện. Tương quan trong biểu đồ không chứng minh nguyên nhân. Không gán nguyên nhân chi nhánh cụ thể từ khuyến nghị toàn workspace. Nếu thiếu bằng chứng, đưa giả thuyết có nhãn và bước kiểm chứng an toàn, không khẳng định lỗi nhân viên hoặc phần cứng.

## Cần bảo vệ dữ liệu nào khi báo sự cố?

Không đưa password, OTP, access token, private key, hồ sơ cá nhân hoặc nội dung database vào chat. Khi gửi log, thay thông tin định danh bằng giá trị giả và giữ cấu trúc lỗi cần chẩn đoán. Không yêu cầu tắt firewall, xóa database hoặc thao tác phá hủy để thử nhanh. Sự cố nghiêm trọng cần người phụ trách có thẩm quyền và kế hoạch khôi phục, không chỉ lời tư vấn AI.
