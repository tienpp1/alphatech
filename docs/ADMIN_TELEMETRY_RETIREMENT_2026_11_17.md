# Gỡ hai giao diện theo quyết định chủ đồ án —17/11/2026

## Cơ sở và giới hạn

Đối chiếu đề cương duyệt teacher_review_v2:
`output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx`,
SHA256 `9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816`.
Đã đọc OOXML và kiểm trực quan PDF/PNG trang8,16. Mục6trang8 có quản lý
tài khoản/quyền/workspace; không ghi tên Django Admin. AI monitoring trang16
thuộc hướng phát triển V3. Chủ dự án được thông báo và chọn:
“Gỡ cả hai, chấp nhận không còn giao diện Django Admin cho các việc trên”.
Không sửa Word và không thay tiến độ/cấu trúc sổ97.

## Thay đổi

- Gỡ mount `/admin/` và toàn bộ URL con, route `/noibo/telemetry/`; trả404.
- Xóa menu/nút nhanh/CTA Admin; xóa view snapshot và template300dòng.
- Không đổi tài khoản ADMIN, MANAGER, EMPLOYEE, mật khẩu, RBAC, membership,
  workspace, dữ liệu kinh doanh, audit, model, migration hoặc secret.
- Không còn giao diện Django Admin cho quản trị tài khoản/quyền/workspace và
  duyệt bảng dữ liệu/audit tổng quát; không tự tạo hệ thống thay thế.
- Giữ các API, AI/RAG, dự báo, khuyến nghị/phê duyệt và bản đồ nghiệp vụ.
  Giữ app Django Admin/migrations để không phá lịch sử schema/dependencies.
  Command Center `/noibo/ai-command-center/` với socket minh họa và
  `/api/health/` là thành phần độc lập, không bị gỡ.

## Kiểm chứng source

- TDD guard mới RED7fail trước sửa → GREEN6/6 không DB.
-101/101 focused qua9module đạt12,321s trên nhánh phát hành;
  workspace chính101/101 đạt15,103s. Không gọi là full-suite.
- Hai DB TEST loopback random riêng tự hủy;10file trọng tâm giữ hash từng lượt.
-76/76 JavaScript đạt2,141s, không skip;5nhóm transport đạt.
- Review độc lập toàn bộ diff: không Critical/Important/Minor.
- Chỉ cập nhật các hợp đồng test thuộc màn hình đã gỡ; giữ redaction probe,
  Google/customer boundary, báo cáo/CSV, scoped queries và CommandCenter/socket.

Chi tiết receipts/log local tại `output/admin_telemetry_retirement_20261117/`.
Push, CI và Render/browser live phải có bằng chứng riêng; local PASS không
tự chứng minh đã triển khai. Template đã xóa có thể khôi phục từ Git commit cha.
