# Đợt 3 — Nội dung tư vấn công khai có căn cứ

## Đã sửa

Mã tư vấn trước đây tự đưa ra cam kết không kèm nguồn xác minh: ISO 27001, bồi hoàn 200%, ngân hàng/đối tác trả góp, lãi suất và thời gian duyệt, hóa đơn VAT tự động, đổi trả/bảo hành, miễn phí trọn đời, chiết khấu B2B, trực ngoài giờ và thời gian SLA. Đây là câu trả lời viết sẵn, không phải bằng chứng hệ thống có nghiệp vụ tương ứng.

Đã sửa 11 handler để phân biệt thông tin chưa xác minh với điều kiện thực sự được chấp thuận; giữ liên kết liên hệ/yêu cầu dịch vụ hiện có. Không khẳng định đơn vị không cung cấp dịch vụ — chỉ không tự hứa điều chưa có căn cứ. Không thay đổi thanh toán, phí vận chuyển hay quyết định phê duyệt.

Tra chi nhánh không còn tự dựng địa chỉ/số điện thoại khi dữ liệu thiếu. Niêm yết sản phẩm không đồng nghĩa tồn kho; giá vẫn lấy từ catalog. Dịch vụ vẫn có tên và link đặt yêu cầu, nhưng không lặp mô tả thành chứng nhận chất lượng. Các hướng dẫn cấu hình máy tính tổng quát chưa được kiểm định toàn diện trong đợt này.

## Files chính

- `apps/public_web/alphatech_ai.py`: nội dung tư vấn, greeting, suggestions, trạng thái thiếu dữ liệu.
- `apps/public_web/views.py`: cập nhật mô tả API; giữ route, capabilities và response keys.
- `templates/public/base_public.html`: chỉ sửa chữ trong widget, giữ nguyên CSS/animation.
- `tests/test_public_consultation_evidence.py`: kiểm thử không database, gồm 12 tình huống chính sách và các ca directory/catalog/widget.
- `tests/test_public_copilot_and_cart_api.py`: thay kỳ vọng cam kết sai bằng hợp đồng hành vi mới; không xóa kiểm tra quyền sở hữu, rò rỉ giá vốn hay giỏ hàng.

## Kiểm chứng và giới hạn

29 test qua khi chạy nhóm consultation mới + RAG scorer/runner + academic reporting. Django check không lỗi, không phát sinh migration. Chưa chạy nhóm DB-backed do chưa xác minh database test riêng; chưa kiểm tra trình duyệt hoặc production, chưa push GitHub.

Thay đổi này không rà sạch mọi nội dung marketing trên mọi trang và không sửa dữ liệu seed/tri thức trong database. Chứng nhận, đối tác và chính sách thương mại chỉ nên được đưa trở lại sau khi chủ dự án cung cấp văn bản có người phê duyệt, phạm vi áp dụng, ngày hiệu lực và đầu mối xác nhận. Không cần gửi secret hay dữ liệu cá nhân vào chat.

## Tiếp theo

1. Chuẩn bị database test cô lập, chạy integration ownership/cart/API và benchmark RAG mới; không dùng database đang phục vụ khách hàng.
2. Chốt bộ nguồn/đáp án chuẩn và cách thẩm định câu trả lời RAG; giữ nguyên ca thất bại.
3. Rà các trang marketing và dữ liệu catalog/knowledge seed còn chứa lời cam kết tương tự; phân biệt dữ liệu minh họa đồ án với chính sách thật.
4. Sau đó đo các kịch bản phê duyệt/audit bằng ca thực thi thật trong test DB thay vì suy ra từ số bản ghi.
