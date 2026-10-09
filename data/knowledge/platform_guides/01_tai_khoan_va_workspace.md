# Hướng dẫn nội bộ: tài khoản và workspace

Phạm vi: hướng dẫn sử dụng nền tảng từ mã nguồn, không phải chính sách kinh doanh. Bản ngày 09/10/2026. Nguồn: AGENTS.md, docs/PROJECT_CONTEXT.md, apps/workspaces và apps/accounts. Chỉ dùng trong Knowledge Base nội bộ; không công bố hồ sơ nhân sự hoặc dữ liệu workspace ra web.

## Vì sao không xem được dữ liệu workspace khác?

Workspace là ranh giới dữ liệu. Người dùng phải có membership đang hoạt động và quyền tương ứng. Chọn workspace không tự cấp quyền. X-Workspace-ID là header chính; X-Workspace theo mã chỉ là tương thích có xác minh membership. Khi chọn rõ workspace không hợp lệ, không được tự rơi về workspace mặc định. Không đổi ID trong URL để tìm dữ liệu doanh nghiệp khác. Nếu không được cấp quyền, liên hệ quản trị thay vì tìm cách vượt kiểm soát.

## Google và khách hàng có được đăng nhập nội bộ không?

Tài khoản Google-linked và khách hàng không được nhận quyền nội bộ. Nhân sự dùng danh tính riêng không liên kết Google, đăng nhập bằng mật khẩu tại /accounts/login/. ADMIN/superuser được quản trị theo kiểm soát hiện có; MANAGER và EMPLOYEE chỉ có quyền được cấp. Không suy ra quyền từ tên đăng nhập. Không xin mật khẩu, mã OTP, client secret hoặc access token trong hội thoại AI.

## Vì sao nhân viên không thấy nút sửa?

Ẩn nút là hỗ trợ giao diện; kiểm tra quyền trên server mới quyết định. Quyền đọc không đồng nghĩa quyền quản lý. Thiếu permission trả denial; đối tượng ở workspace khác phải không tiết lộ sự tồn tại. Trợ lý không tự cấp role hoặc membership. Yêu cầu quản trị xem quyền đã seed và vai trò thực tế, không sửa database trực tiếp để bỏ qua RBAC.

## Khi câu trả lời có số liệu khác dashboard thì làm gì?

Đối chiếu workspace, khoảng ngày, trạng thái đơn, bộ lọc và thời điểm truy vấn. Số liệu runtime phải lấy từ tool được cấp quyền, không lấy số liệu ví dụ trong tài liệu làm doanh thu thực. Nếu còn chênh lệch, ghi câu hỏi, thời điểm và bộ lọc để điều tra; không tự kết luận dashboard sai hoặc tạo số liệu thay thế.
