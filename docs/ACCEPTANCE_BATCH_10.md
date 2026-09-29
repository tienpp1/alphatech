# Đợt 10 — Ownership, checkout inventory and transactional email

Ngày: 15/09/2026. Phạm vi: checklist gốc 97 mục; PostgreSQL/PostGIS local test database cô lập. Email transport được mô phỏng có chủ đích, không phải inbox production.

## Kết quả

| Mục | Trạng thái | Bằng chứng |
|---|---|---|
| 72 | Đóng | `customer_for_submission` tạo/tra Customer theo `(workspace, authenticated user)`, không theo email/form name. Test đăng nhập gửi service inquiry bằng email khác; Customer thuộc workspace dịch vụ và user đúng, không thêm membership. Test guest dùng email trùng account nhưng tạo Customer guest mới; không chiếm profile. Order-success/order-history ownership vẫn lọc theo `created_by`. |
| 73 | Một phần | Store pickup kiểm tra và trừ `StockBalance` dưới lock, validates every line before mutation; thiếu row tồn kho nay bị từ chối thay vì coi là vô hạn. Home delivery chưa có branch inventory allocation/deduction, nên chưa thể tuyên bố nhất quán tồn kho mọi phương thức. |
| 74 | Đóng trong phạm vi customer events hiện có | Order và service inquiry được commit khi email backend trả 0/raises; UI có cảnh báo tiếng Việt, outbox FAILED lưu entity; retry thành SENT và lần retry sau không gọi provider lần nữa. Contact/registration failure, retry, ownership đã có test trước đó. Không tuyên bố exactly-once khi provider đã nhận nhưng process chết trước khi lưu SENT. |

## Sửa code

- `apps/public_web/views.py`: pickup không có `StockBalance` bị chặn với thông báo “Chưa xác nhận tồn kho…”. Không thay đổi home-delivery behavior.
- `tests/test_customer_account_identity.py`: service Customer/workspace integrity và guest non-claim regressions.
- `tests/test_public_ecommerce_cart_and_checkout.py`: missing stock rejection; order remains committed on failed email and bounded retry does not duplicate provider call.
- `tests/test_service_email_commit.py`: service request remains committed on failed email, warning is shown, retry is idempotent.

## Kiểm thử

- `python manage.py test tests.test_customer_account_identity tests.test_public_ecommerce_cart_and_checkout --settings=config.settings_evidence_test --keepdb --noinput`: **28 passed, 132.273s**.
- `python manage.py test tests.test_service_email_commit --settings=config.settings_evidence_test --keepdb --noinput`: **1 passed**.
- `python manage.py check`: 0 issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- Computer Use/browser check was attempted twice but the helper failed before opening a target (`failed to write kernel assets`, Windows error 3); no UI success is claimed.

## Remaining boundary

Production domain, live OAuth, Brevo/inbox, device GPS and Render deployment were not changed. Local diagnostic reports SMTP credentials present but `PUBLIC_BASE_URL=http://localhost:8000`, no active Google redirect URI, and OAuth/Brevo configuration not active in this local settings process; secret values were not printed. Use deployment environment diagnostic separately.
