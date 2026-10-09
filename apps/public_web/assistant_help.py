"""Public-only, source-reviewed navigation context. Never imports internal SOPs."""

HELP_TOPICS = (
    (
        ("đăng ký", "tạo tài khoản", "mã xác minh", "xác minh email"),
        "**Đăng ký và xác minh email**\n\nMở [Đăng ký](/dang-ky/), điền thông tin và làm theo bước xác minh được gửi tới email. Kiểm tra cả thư rác; không chia sẻ mã hoặc đường dẫn xác minh trong chat. Email đã thuộc tài khoản hiện có không được đăng ký thêm tài khoản trùng. Nếu đã dùng Google, hãy dùng nút Google tại [Đăng nhập](/dang-nhap/). Tôi không thể xác minh hộ hoặc bỏ qua bước này.",
        ("Không nhận được email", "Đăng nhập bằng Google"),
    ),
    (
        ("không nhận được email", "chưa nhận được mail", "không thấy mã", "email chưa tới"),
        "**Chưa nhận được email**\n\nKiểm tra địa chỉ đã nhập, thư rác và chờ một lúc trước khi yêu cầu gửi lại ở màn hình xác minh. Với email giao dịch, xem trạng thái trong [Tài khoản](/tai-khoan/) và dùng chức năng gửi lại nếu có. Việc ghi nhận đơn hoặc yêu cầu không chứng minh thư đã tới Inbox. Nếu vẫn lỗi, gửi mã đơn/yêu cầu qua [Liên hệ](/lien-he/); không gửi mật khẩu hoặc mã xác minh.",
        ("Cách đăng ký", "Xem đơn hàng"),
    ),
    (
        ("quên mật khẩu", "khôi phục mật khẩu", "đăng nhập google", "tài khoản google"),
        "**Đăng nhập tài khoản khách hàng**\n\nMở [Đăng nhập](/dang-nhap/). Tài khoản tạo bằng Google dùng nút Google; không mặc định có mật khẩu riêng. Với tài khoản đăng ký bằng mật khẩu, dùng [Quên mật khẩu](/quen-mat-khau/). Tài khoản khách hàng/Google không được vào cổng nội bộ. Tôi không thể đọc, đặt lại mật khẩu hay xin mã OTP qua chat.",
        ("Cách đăng ký", "Không nhận được email"),
    ),
    (
        ("cách mua", "đặt hàng thế nào", "giỏ hàng", "cách đặt hàng"),
        "**Các bước đặt mua sản phẩm**\n\nChọn sản phẩm tại [Danh mục](/san-pham/), mở chi tiết rồi thêm vào [Giỏ hàng](/gio-hang/). Kiểm tra số lượng, giá và thông tin giao nhận ở [Thanh toán](/thanh-toan/) trước khi gửi đơn. Sau đó giữ mã đơn và xem lịch sử trong tài khoản. Gửi đơn không đồng nghĩa đã thanh toán hoặc được xác nhận; điều kiện giao hàng cần được xác nhận.",
        ("Xem sản phẩm", "Xem đơn hàng"),
    ),
    (
        ("xem đơn hàng", "lịch sử mua", "đơn của tôi", "tra cứu đơn hàng"),
        "**Tra cứu đơn của bạn**\n\nMở [Lịch sử đơn hàng](/tai-khoan/don-hang/) sau khi đăng nhập đúng tài khoản đặt mua, hoặc nhập đầy đủ mã ORD trong câu hỏi. Đơn của người khác không được hiển thị; không tìm thấy không có nghĩa đơn không tồn tại. Nếu đặt với tư cách khách, giữ phiên duyệt đã đặt đơn hoặc liên hệ để được hỗ trợ xác minh.",
        ("Đăng nhập bằng Google", "Cách đặt hàng"),
    ),
    (
        ("tìm đường", "bật gps", "không lấy được vị trí", "bán kính", "nhập địa chỉ"),
        "**Tìm chi nhánh và đường đi**\n\nMở [Bản đồ chi nhánh](/chi-nhanh/), cấp quyền vị trí hoặc nhập địa điểm. Chọn chi nhánh rồi dùng dẫn đường; có thể tìm theo bán kính 1–10 km. Nếu GPS bị từ chối hoặc sai số lớn, hãy nhập địa điểm thay thế. Tuyến đường phụ thuộc dữ liệu nhà cung cấp, không bảo đảm ngắn nhất tuyệt đối hay giao thông trực tiếp. Không gửi địa chỉ riêng tư vào chat.",
        ("Chi nhánh gần nhất", "Đặt yêu cầu dịch vụ"),
    ),
    (
        ("hủy đơn", "huỷ đơn", "đặt nhầm", "đổi địa chỉ giao", "sửa đơn hàng"),
        "**Cần sửa hoặc hủy đơn đã đặt**\n\nChuẩn bị mã đơn và mở [Lịch sử đơn](/tai-khoan/don-hang/) để đối chiếu, rồi gửi yêu cầu qua [Liên hệ](/lien-he/). Tôi không thể hủy, đổi địa chỉ hoặc xác nhận hoàn tiền trong chat. Khả năng xử lý phụ thuộc trạng thái đơn và xác nhận của nhân viên; không gửi lại đơn mới liên tục vì có thể tạo đơn trùng.",
        ("Xem đơn hàng", "Liên hệ hỗ trợ"),
    ),
    (
        ("chuẩn bị khi báo lỗi", "mô tả sự cố", "gửi log", "báo lỗi cần gì", "dịch vụ cần thông tin gì"),
        "**Thông tin cần khi gửi yêu cầu dịch vụ**\n\nTại [Yêu cầu dịch vụ](/yeu-cau-dich-vu/), mô tả thiết bị/model, triệu chứng, thời điểm bắt đầu và mức ảnh hưởng. Nếu có log, che thông tin cá nhân và bí mật trước khi gửi. Không gửi mật khẩu, OTP, private key hoặc cấp quyền điều khiển từ xa qua chat. Gửi yêu cầu chưa đồng nghĩa lịch hẹn hoặc thời gian xử lý đã được xác nhận.",
        ("Đặt yêu cầu dịch vụ", "Chi nhánh gần nhất"),
    ),
    (
        ("so sánh laptop", "chọn laptop cần gì", "tư vấn cần thông tin gì", "chọn máy phù hợp"),
        "**Để chọn máy phù hợp**\n\nHãy cho biết ngân sách tối đa, phần mềm/công việc chính, nhu cầu di chuyển và thiết bị đang dùng. Tôi có thể tìm giá niêm yết trong danh mục; không thể cam kết hiệu năng, thời lượng pin hay khả năng nâng cấp của model chưa có thông số xác minh. Xem [Sản phẩm](/san-pham/) để chọn các mã cụ thể cần đối chiếu. Không cần cung cấp thông tin tài chính cá nhân hoặc giấy tờ định danh.",
        ("Laptop dưới 20 triệu", "Tư vấn laptop văn phòng"),
    ),
)


def answer_public_help(query, matches):
    # More specific email-failure context wins over a generic registration phrase.
    ordered = (*HELP_TOPICS[6:], HELP_TOPICS[1], HELP_TOPICS[2], HELP_TOPICS[0], *HELP_TOPICS[3:6])
    for keywords, reply, suggestions in ordered:
        if matches(query, keywords):
            return {"reply": reply, "suggestions": list(suggestions)}
    return None
