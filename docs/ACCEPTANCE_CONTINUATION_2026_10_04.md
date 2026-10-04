# Tiếp tục kiểm chứng — 04/10/2026

Không sửa số lượng, cấu trúc hoặc trạng thái trong checklist 97 mục. Đây là
bằng chứng bổ sung độc lập, không phải tuyên bố 97/97 hoặc production 100%.

## 1. Kiểm thử toàn bộ snapshot và sửa lỗi

- Lượt đầu: `output/acceptance_verification/20261004T013519Z`:
  **1192 tests, 409.779s, 33 failures + 7 errors, exit 1**. Fingerprint 710
  đầu vào không đổi trong lượt chạy. Log lỗi giữ nguyên, không ghi đè.
- 7 errors do WorkspaceMiddleware truy cập `request.session` vô điều kiện khi
  chạy với RequestFactory không có SessionMiddleware. Dùng session rỗng khi
  không tồn tại; Google-linked không có bằng chứng phương thức vẫn bị từ chối.
- Fixture quản lý cũ dùng tên AUTHZ_ADMIN/AUTHZ_MANAGER/AUTHZ_EMPLOYEE,
  EMPTY_TEST_MANAGER và Retail Manager không thuộc ba vai trò được người dùng
  cho phép. Chuyển fixture sang ADMIN/MANAGER/EMPLOYEE, giữ nguyên permission
  grants, kiểm tra IDOR, cập nhật dữ liệu, audit, CSV, empty state và denied mutations.
- Test đọc thuần túy dùng EMPLOYEE chỉ có view grants thay vì VIEWER. Bổ sung
  test VIEWER/custom role có view grants vẫn không vào được UI nội bộ; giữ test
  EMPLOYEE không có nút chỉnh sửa và không sửa được bản tin. Không nới policy.
- Các trang con nội bộ giờ từ chối khách hàng bằng 403 trước truy vấn, thay vì
  redirect 302 trước đây. Test xác nhận denial mới; `/noibo/` cho khách thường
  vẫn giữ redirect cũ, còn phiên Google luôn bị chặn ở cổng nội bộ.
- Bổ sung module Google boundary vào manifest tài liệu và workflow CI; không
  bỏ qua test, không thay threshold coverage, không thay schema/migration.
- Rerun nhóm liên quan: **124 tests, 64.458s, 2 failures** còn ở assertion
  redirect khách thường trong CSV/telemetry; sửa đúng expectation 403.
- Lượt cuối toàn bộ: `output/acceptance_verification/20261004T020428Z`:
  **1194 tests, 196.973s, OK, 0 failures/errors/skips, exit 0**;
  1194 test IDs quan sát được. Fingerprint 710 inputs không đổi trong run.
  Log SHA-256 `4c9c7415560c83dfdbc67bb3f7aae830a0d8d1c7d8c2634e398893cb61dca2b9`.

Lệnh tái lập:

```powershell
.venv-acceptance/Scripts/python.exe scripts/run_acceptance_verification.py --fast-test-passwords
.venv-acceptance/Scripts/python.exe scripts/summarize_acceptance_log.py output/acceptance_verification/20261004T020428Z
.venv-acceptance/Scripts/python.exe scripts/audit_use_case_traceability.py --test-summary output/acceptance_verification/20261004T020428Z/test_summary.json --output output/use_case_traceability_20261004.json
.venv-acceptance/Scripts/python.exe manage.py check
.venv-acceptance/Scripts/python.exe manage.py makemigrations --check --dry-run
git diff --check
```

Runner dùng database PostgreSQL/PostGIS local mới, tên ngẫu nhiên; chỉ dọn DB
test do chính lượt chạy tạo. MD5 chỉ là override trong tiến trình TEST để tăng
tốc, không thay password hasher/runtime production. Log child bật unbuffered.
Không dùng test outbox/mocked Google để suy ra inbox/OAuth thật.

- Join ma trận **35 use cases**: không thiếu file tham chiếu hay test ID đã chạy.
  Đây là truy vết thực thi, không chứng nhận độ đầy đủ ngữ nghĩa/visual/live.
- Django check: 0 issues; migration drift: No changes detected; diff check: exit 0.
- Bandit sau patch: exit 0, `output/bandit_final_20261004.json`.
- pip-audit trên packages trong `.venv-acceptance`: không có known vulnerabilities,
  exit 0, `output/pip_audit_20261004.json`; không phải scan CI/Render environment.
- Known-pattern secret scan: 797 files, 0 findings. History local: 34 reachable
  commits, 0 findings. Không fetch remote hoặc kiểm chứng rotation ở provider.

## 2. Live UAT đơn bán lẻ — đang chờ hoàn tất chủ đơn

Domain: `alphatech-26uv.onrender.com`. Browser production đang chạy bản cũ;
không lấy UAT này làm bằng chứng đã triển khai policy Google mới ở local.

1. Khách hàng thường Tien Billy đăng nhập Google; trang tài khoản không có nút
   quản trị. Mở đơn TEST cũ ORD-20261002-9733DF trả Not Found.
2. Theo quyền cụ thể đã được cấp, chuẩn bị một đơn TEST với ghi chú không giao
   hàng/không thu tiền; chính người dùng bấm gửi form có xác nhận điều khoản.
   Đơn **ORD-20261004-7ACE63, ID 162**, một SP-NET-006, tổng 125000 VNĐ,
   tạo 08:57 giờ Việt Nam. Không thực hiện thanh toán hoặc hoàn thành giao hàng.
3. Phiên minhtien xác nhận đúng đơn qua UI `/noibo/retail/orders/162/`;
   giao diện hiện Đã xác nhận. Không mở trang public của chủ đơn sau duyệt.
4. Đăng xuất, người dùng đăng nhập Tien Billy. Dialog celebration không mở,
   tiêu đề/message rỗng; trang đơn 162 trả Not Found. Read-only query riêng
   xác nhận notice 28 thuộc order creator, `is_read=False`, tạo lúc
   `2026-10-04T01:58:53.690558+00:00`.
5. Browser chặn navigation trực tiếp JSON feed bằng ERR_BLOCKED_BY_CLIENT;
   không coi đây là response API của server. Bằng chứng nonowner là UI và
   đối chiếu trạng thái DB, không tuyên bố đã bắt được HTTP response của poll.
6. **Đã hoàn tất bước chủ đơn và cleanup:** người dùng đăng nhập Google của
   chủ đơn; browser hiển thị dialog “Đơn hàng của bạn đã được duyệt!” với đúng
   ORD-20261004-7ACE63. Click “Tuyệt vời, cảm ơn!” rồi reload: không còn dialog.
   Ảnh `owner-celebration.png`, `owner-after-reload.png` trong cùng thư mục UAT.
   Quan sát trực tiếp dialog; không có video đo độ mượt hoặc thời điểm bắt đầu
   animation nên không khẳng định hiệu năng hiệu ứng.
7. Đăng nhập riêng ADMIN bằng mật khẩu, hủy chính TEST 162 qua nút UI.
   Trang trả “Đã hủy”; ảnh `test-cancelled.png`. Query production read-only
   sau đó xác nhận status CANCELLED, notice 28 is_read=True, recipient đúng
   order creator, read_at `2026-10-04T03:12:32.101194+00:00`.
   Không hoàn thành/giao hàng/thu tiền hay xóa đơn. Việc kiểm tra thông báo
   owner/nonowner/ack/reload cho đơn TEST này đã hoàn tất.
8. Ngoài phạm vi kết luận UAT trên: trang tài khoản sau Google login vẫn hiện
   banner và liên kết quản trị nội bộ. Đây là quan sát UI trên production cũ,
   không phải kiểm chứng endpoint nội bộ cho phiên đó; không đóng cổng phân tách
   Google/customer/internal. Các bản vá local chưa được push/deploy trong lượt này.

Evidence tại `output/uat_20261004/observations.json` và các screenshot cùng thư
mục. Không lưu mật khẩu/token trong bằng chứng. Query danh tính admin là read-only,
chỉ đọc username/quyền và boolean có password, không đọc/xuất password hash.

## 3. Ranh giới kết luận 97 mục

- Toàn bộ local suite sau sửa đã xanh; đây không thay thế 97 tiêu chí nghiệm thu.
- Các dòng 90/93 của ledger trỏ release f2a831c/CI 36836448440, không bao phủ
  dirty patch hiện hành. Chưa push/deploy patch trong phiên này.
- Ledger mục 96 còn ghi hoãn, nhưng hồ sơ restore 02/10 ghi actual pg_dump →
  pg_restore vào sandbox mới, 60 bảng/10576 dòng đã kiểm tra. Tham chiếu
  PRODUCTION_RESTORE_DRILL_2026_10_02.md; không tự thay ledger theo Rule 12.
- Off-site backup vẫn hoãn theo chủ dự án. Backup ổ D không bảo vệ mất máy.
- Local Storage là phạm vi học thuật đã chốt; không có bucket R2 thật và không
  chứng nhận phục hồi media/model Render Free. Async production vẫn không dùng.
- Email/Sentry/GPS và cross-device/service UAT giữ đúng nguồn Human Evaluation;
  không tạo thêm message ID/Event ID hoặc chấm điểm người dùng thay họ.
- Không mở mapping reorder/workload khi chưa có domain handler an toàn.

Kết luận: **đã kiểm chứng full local snapshot và thêm bằng chứng cách ly khách
hàng live; chưa đủ để công bố 97 mục hoàn tất trọn vẹn trên production.**
