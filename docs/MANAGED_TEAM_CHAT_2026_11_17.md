# Tạo tài khoản nhân viên và mời vào Trao đổi

## Quyền và thao tác

Chủ dự án đã duyệt: chỉ MANAGER và EMPLOYEE được mời tham gia kênh đúng
workspace. ADMIN/superuser, khách hàng và tài khoản Google không được đọc/gửi
chat; quyền ADMIN ở các phân hệ khác không thay đổi.

1. MANAGER đăng nhập bằng mật khẩu tại `/accounts/login/`, mở `/noibo/trao-doi/`
   và chọn đúng workspace.
2. Mở **Tạo tài khoản nhân viên**, điền họ tên, email công việc, username,
   mật khẩu và xác nhận. Tài khoản được cố định EMPLOYEE và chỉ có membership
   trong workspace đã chọn; chưa được đọc/gửi chat.
3. Mở **Thêm nhân viên vào chat**, chọn nhân viên đang chờ và xác nhận. Khi đó
   nhân viên mới mở được kênh và gửi/nhận tin theo cơ chế polling hiện có.

Form không đổi tài khoản đã tồn tại. Nếu email/username đã dùng, phải chọn danh
tính nhân viên mới phù hợp; không tự nối tài khoản khách hàng hay Google.
Tuân thủ bộ kiểm tra mật khẩu hiện có, không lưu/in mật khẩu trong nhật ký.
Không thu thông tin lương, vị trí GPS, hồ sơ kỹ thuật viên hoặc dữ liệu HR
không cần thiết chỉ để chat. Tên đăng nhập do manager điền, không tự đặt mật
khẩu chung hay tăng quyền ADMIN.

## Dữ liệu và giới hạn

Tái sử dụng User và WorkspaceMembership, không thêm bảng nhân viên/chat thứ hai.
`workspaces.0002_team_chat_enabled` thêm boolean, điềnTrue cho membership cũ
để giữ quyền chat nhân viên đã có; mặc địnhFalse cả ORM/database cho membership
mới, kể cả INSERT từ phiên bản app cũ trong lúc chuyển deploy. MANAGER
không cần được mời, nhưng phải còn membership MANAGER hợp lệ trong workspace.
ADMIN/superuser không được bỏ qua kiểm tra này. Không sửa/xóa lịch sử tin nhắn.

Tạo tài khoản/membership/audit trong cùng transaction. Mời nhân viên chỉ đổi
flag của EMPLOYEE đủ điều kiện cùng workspace, không sửa vai trò/membership
khác. Lặp thao tác mời không tạo nhiều sự kiện cấp quyền. Việc thu hồi quyền
được kiểm tra lại ở yêu cầu đọc/gửi tiếp theo; không có quyền chat nhờ bản nháp
hay phiên cũ. Hiện không bổ sung giao diện quản trị nhân sự toàn diện hoặc nút
đổi quyền tùy ý. Bản tin nội bộ và public website giữ ranh giới sẵn có.

Kiểm thử và phát hành được ghi nhận riêng khi có log, không coi implementation
là bằng chứng production. Không chỉnh số lượng/trạng thái97mục hay Word đã duyệt.

## Bằng chứng source trước phát hành

- TDD phân quyền/tạo/mời/validation105/105đạt16,844s, UI root7/7đạt0,313s.
- Chrome trên database TEST riêng:7luồng đạt,0pageerror; tạo chưa được chat,
  mời rồi mới gửi/nhận polling, giữ tin cũ, chặn ADMIN và đọc chéo workspace.
 375x812và812x375mở form bằng bàn phím/nút dùng được, không tràn ngang.
- Full đầu1684tests/423,827s có1ERROR tại test_demo_document_routes do link
  Admin cũ trong tài liệu demo; sửa tài liệu, không bỏ/sửa yếu test. Guard8/8
  đạt0,103s; full cuối1684/1684đạt339,437s,0failure/error/skip, DB TEST tự hủy.
 18file runtime/test giữ hash; fast hasher và legacyfulfillmentfixture chỉ
  trong process TEST, không thay cấu hình kinh doanh hay password validator.
- JavaScript76/76đạt3,677s,5nhóm transport đạt; Bandit9module0findings;
 902file nguồn không known-secret findings (không phải quét secret tuyệt đối).
- Review độc lập backend/UI không còn finding. Scoped VI POST giữ toàn bộ
  validation/CSRF/redaction, không đổi LANGUAGE_CODE chung; bảo toàn ngưỡng
  minimum-length thực khi bản dịch Django hiện tại thiếu đúng msgid.

Render Free dùng build.sh có migrate và collectstatic, đã kiểm cấu hình bằng
API đọc-only; bằng chứng deploy/CI/live ghi riêng sau. Primary hiện cấu hình
database Render khác, probe Windows không kết nối nên chưa xác minh schema của
DBđó. Không thay.env, không tự chuyển môi trường local sang database Neon thật.
