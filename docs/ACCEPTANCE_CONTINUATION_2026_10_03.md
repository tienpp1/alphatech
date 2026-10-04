# Kiểm chứng tiếp nối ngày 03/10/2026

Không đổi cấu trúc hoặc số tiến độ checklist 97 mục (AGENTS Rule 12).
Không chứng nhận 97/97 hoặc production 100% từ kết quả test local.

## 1. Full suite thực chạy — snapshot trước sửa câu chữ mua hàng

Lệnh: `.venv-acceptance/Scripts/python.exe scripts/run_acceptance_verification.py`.
Runner gọi `manage.py test tests --settings=config.settings_evidence_test --noinput -v 2`.

- **1179 tests, 3108.343s, OK**; 0 failures, 0 errors, 0 skipped,
  0 expected failures, 0 unexpected successes; wrapper exit 0.
- Thời điểm wrapper chạy subprocess: 08:50:11–09:45:27 ngày 03/10,
  UTC+7. Thời gian test theo unittest không bao gồm toàn bộ startup/cleanup.
- Database riêng `test_alphatech_evidence_1b74879fef3041cc` trên loopback
  PostgreSQL/PostGIS, được runner tự dọn sau khi kết thúc. Không reset DB
  development/production.
- 705 file input được fingerprint; không đổi trong lượt chạy.
- Wrapper mở rộng fingerprint sang templates/static/data/docs/scripts/.github
  và requirements/README/AGENTS, không đọc .env hoặc payload backup.
- Evidence: `output/acceptance_verification/20261003T014851Z/`
  (`django.log`, `result.json`, `source_before.json`, `test_summary.json`).
- Log SHA-256: `272f997f5c8fc5daf12f53ec00bea16cfbc4a9e49f60110fdc74562d699bcaf2`.
- Parser quan sát đủ 1179 unique test IDs; không cộng rerun vào số này.
- Join 35 use case với test summary: không thiếu file, không có file test tham
  chiếu mà chưa quan sát ID; artifact `output/use_case_execution_audit_20261003.json`.
  Đây là traceability/execution, không chứng minh đầy đủ nghiệp vụ hoặc UAT.

Full snapshot này bao gồm sửa stale permission cache và các regression từ
02/10. Nó **không** bao gồm phần sửa câu chữ và 5 test mới dưới đây, vì phần đó
được làm sau khi full run kết thúc; không ghép hai lượt thành full suite mới.

## 2. Khoảng trống tìm thấy sau rà soát nội dung

Các lexical guard cũ bỏ sót biến thể có khoảng trắng và nội dung chỉ xuất hiện
khi giỏ hàng có sản phẩm. Sửa đúng phạm vi template, không đổi schema, routes,
phép tính giá/phí vận chuyển, animation hoặc quyền server-side:

- Product detail: bỏ lời khẳng định có hàng/giao hỏa tốc, đổi mới 30 ngày;
  thay bằng trạng thái/điều kiện cần được xác nhận.
- Cart: không mặc định VAT đã bao gồm, bảo hành 12–24 tháng hay đổi mới 30 ngày.
- Order success: VAT cần xác nhận theo đơn, giữ nguyên tổng tiền thực tế.
- Checkout: không hứa gửi mã vận đơn/hóa đơn điện tử khi chưa có bằng chứng
  triển khai; giữ mức phí 30.000đ/ngưỡng miễn phí 5 triệu đang có trong nghiệp vụ.
- Customer account: staff không được mô tả mặc nhiên có mọi quyền;
  quyền vẫn được kiểm tra theo vai trò/workspace.

Thêm 5 regression trong `tests/test_public_policy_copy.py`: giỏ có sản phẩm,
product defaults, checkout invoice/tracking, order receipt totals và staff banner.
Skill ui-ux-pro-max được đọc để rà UI; hai truy vấn copy không có match phù hợp,
không dùng dữ liệu gợi ý chưa kiểm chứng. Giữ nguyên thiết kế hiện có và áp dụng
ranh giới chính sách công bố của dự án.

## 3. Kiểm thử sau patch

Lệnh:

```text
.venv-acceptance/Scripts/python.exe manage.py test tests.test_public_policy_copy tests.test_policy_and_claim_consistency tests.test_customer_approval_notices tests.test_public_ecommerce_cart_and_checkout --settings=config.settings_evidence_test --noinput -v 1
```

- Lần đầu cùng nhóm chạy verbosity 2: **48 tests, 113.906s, FAILED (errors=2)**.
  Hai fixture mới thiếu `order.status` và `user.first_name`, khiến Django
  không resolve được argument của filter `default`; không phải lỗi SMTP.
- Bổ sung đúng field của fixture, không bỏ test/giảm assertion/đổi ứng dụng
  để che lỗi. Rerun toàn nhóm: **48 tests, 105.797s, OK, exit 0**.
- Có ca mô phỏng mail failure rồi retry; log failure là expected fixture,
  không phải gửi tới SMTP/inbox thật.
- Check và migration drift trước và sau patch: exit 0, 0 issues/No changes detected.
- `git diff --check`: exit 0. Không có migration/schema mới.

## 4. Browser và cấu hình

- Production: tài khoản thứ hai Sinh mở order-success của đơn TEST
  `ORD-20261002-9733DF` trả trang Not Found, không lộ đơn của chủ khác.
  Tài khoản có banner staff/internal; không tính là khách hàng thường.
- Browser vẫn giữ phiên Sinh tại thời điểm kiểm tra lại. Chủ dự án cho phép
  thêm đơn TEST không giao/thu tiền, nhưng chưa có phiên khách hàng thường;
  **chưa tạo đơn production mới** và chưa ghi UAT notice chưa đọc cross-user PASS.
- Local cũ port 8018 đã dừng; mở lại server loopback, DEBUG chỉ override cho
  process local, tắt exporter trong process, không sửa .env/Render. Browser
  `/san-pham/44/` hiển thị đúng câu chữ mới và bố cục không bị vỡ.
- Screenshot: `output/uat_20261003/product-policy-copy.jpg`.
- Chẩn đoán local `check_customer_integrations`: SMTP backend, credential
  presence có; key Brevo có nhưng backend không chọn Brevo, callback localhost
  không hợp lệ dưới DEBUG=False. Không in secret hoặc suy ra delivery PASS.
- `platform_readiness --json` local: BLOCKED với insecure_secret_key,
  https_oauth_redirect, secure_transport_cookies, hsts_disabled, csp_not_enforced;
  DB kết nối/0 pending migrations. Không phải cấu hình live Render.

## 5. Giới hạn và việc cần người dùng

1. Đăng nhập tài khoản khách hàng thường trong browser để hoàn tất UAT notice
   chưa đọc không lộ sang khách khác, rồi owner thấy animation/ack không lặp.
2. Các patch local chưa được push/deploy trong phiên này; CI xanh của f2a831c
   không bao phủ dirty patch hiện hành. Cần kiểm chứng release tương ứng trước
   khi gọi production đạt.
3. Off-site backup vẫn hoãn theo lựa chọn chủ dự án. Backup ổ D không bảo vệ
   mất máy; không ghi thành off-site PASS.
4. Local Storage được chốt cho đồ án; Render Free media/model persistence và
   các artifact production thiếu file không được chứng nhận phục hồi đầy đủ.
5. Async worker production vẫn tắt theo lựa chọn Render Free; không ghi worker
   production recovery PASS từ test local.
6. Human Evaluation email/Sentry/GPS/UAT đã có vẫn giữ nguồn/giới hạn gốc;
   không tạo Event ID/message ID hay bằng chứng giả.

Không tự tính lại phần trăm hoặc sửa checklist 97 mục để biến các giới hạn
đã hoãn/ngoài phạm vi thành chức năng được kiểm chứng.
