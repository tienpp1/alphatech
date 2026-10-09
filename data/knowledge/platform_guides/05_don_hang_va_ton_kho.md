# Hướng dẫn nội bộ: đơn hàng và tồn kho

Phạm vi: hướng dẫn từ apps/retail/services.py và apps/public_web/customer_identity.py, bản 09/10/2026. Không phải chính sách hoàn tiền, giao nhận hoặc bảo hành được doanh nghiệp duyệt.

## Xác nhận đơn có nghĩa đã giao hàng hoặc nhận tiền không?

CONFIRMED có chứng minh đã thu tiền chưa? Không. CONFIRMED chỉ là xác nhận đơn; đã thu tiền cần bằng chứng thanh toán riêng. Đã giao hàng cũng cần bằng chứng giao nhận riêng.

Không suy ra đã giao hàng hoặc đã nhận tiền chỉ từ trạng thái CONFIRMED. Luồng chuyển trạng thái bán lẻ hiện hỗ trợ PENDING sang CONFIRMED hoặc CANCELLED; CONFIRMED sang COMPLETED hoặc CANCELLED. COMPLETED và CANCELLED là trạng thái cuối trong service hiện tại. Đối chiếu dữ liệu thanh toán/giao nhận thực có trước khi kết luận; không tạo trạng thái SHIPPED hoặc PROCESSING chỉ vì một câu hỏi nhắc đến chúng.

## Hủy đơn có tự hoàn tiền không?

Hủy đơn không chứng minh nhà cung cấp thanh toán đã hoàn tiền. Service hủy kiểm tra khóa dòng và giải phóng tồn kho đã được giữ theo cờ fulfillment, tránh giải phóng lặp. Không cập nhật tồn bằng cách sửa số dư thủ công. Đơn đã COMPLETED không có chuyển sang CANCELLED trong state machine hiện có; cần người có thẩm quyền xử lý theo quy trình phù hợp, không bypass validation.

## Giá sản phẩm đổi thì tổng đơn cũ có đổi không?

Đơn tạo bằng service lấy giá và tính tổng ở server, giữ snapshot dòng hàng. Giá danh mục hiện tại không thay thế giá tại thời điểm đặt đơn. Khi giải thích chênh lệch, đối chiếu đúng mã đơn, thời điểm và từng dòng hàng. Không dùng giá vốn làm giá khách thanh toán; không lấy con số do người dùng gửi để tự xác nhận đã thu tiền.

## Vì sao số lượng danh mục khác tồn kho chi nhánh?

Sản phẩm đang niêm yết không chứng minh còn hàng tại mọi chi nhánh. Đối chiếu workspace, sản phẩm, branch và StockBalance được cấp quyền. Dữ liệu tồn không có không đồng nghĩa số lượng bằng không. Không tự nhập kho, điều chuyển hoặc điều chỉnh tồn để đáp ứng lời hỏi. Phiếu nhập, nhận hàng và stock transfer là nghiệp vụ riêng có validation, transaction và audit.
