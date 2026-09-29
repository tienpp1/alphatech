# Đợt 38 — ranh giới công bố chính sách trong email

## Lỗi và bản vá

Email đơn hàng tìm RETAIL workspace đầu tiên, email dịch vụ tìm SERVICE đầu tiên,
rồi gọi `get_grounded_policy_snippet` và đưa nội dung vào email khách hàng.
Không có kiểm tra tài liệu được phép công khai. Đây là đường có nguy cơ tiết lộ
tri thức nội bộ/cross-workspace; chưa có bằng chứng một sự cố tiết lộ thật đã xảy ra.

Đã bỏ cả hai đường retrieval, không chỉ đổi sang workspace của đơn/phiếu.
Email giữ thông tin giao dịch và hướng dẫn xác nhận điều kiện; bỏ claim mặc định
ISO/NDA tuyệt đối, thời hạn SLA tự gán, VAT đã bao gồm. Nhãn CRITICAL sửa đúng model.
Không sửa số tiền, người nhận, dedup, retry, dữ liệu hoặc email đã gửi.

## Bằng chứng

```text
python manage.py test tests.test_customer_email_policy_boundary tests.test_google_oauth_and_email_notifications tests.test_customer_email_outbox_and_oauth_security tests.test_service_email_commit --settings=config.settings_evidence_test --noinput -v 1
37 tests — 197.281s — OK
```

Hai test mới dùng SimpleTestCase (không cho query DB), assert Knowledge lookup
không được gọi, marker nội bộ không có trong HTML/plain, mã đơn/phiếu/số tiền giữ
nguyên và bốn nhãn priority không kèm thời hạn tự hứa. Các integration tests kiểm
recipient/account+form, commit khi lỗi gửi thư, retry, OAuth và outbox ownership.
Provider OAuth/email là mô phỏng/locmem, không bằng chứng inbox hay Google live.

Sau khi nhóm lớn đã khởi chạy, có chỉnh thêm chữ “đã ghi nhận” thay cho “đang phân
bổ kỹ sư”; nhóm policy-boundary được chạy lại riêng cho nội dung cuối. Không cộng
lượt chạy lại vào 37 test riêng biệt. Recheck: 2 tests, 0.015s, OK.

Django check: no issues; makemigrations --check --dry-run: no changes.
Không thay UI web nên không browser acceptance; không render email screenshot.

## Cần tài liệu và phần còn thiếu

User xác nhận có văn bản chính sách đã duyệt, đang chờ file. Inventory web/email/
SOP ở POLICY_PUBLICATION_REVIEW.md ghi cụ thể vị trí cần đối chiếu. Chưa coi 24
SOP là nguồn công khai hợp lệ hoặc xóa chúng; chưa sửa hàng loạt cam kết website
trước khi đọc văn bản người dùng cung cấp. Một số HTML email vẫn nội suy trường
động; đợt này không chứng nhận đã audit toàn bộ HTML escaping.

51/97 (52,6%) giữ nguyên. Mục 43–46 còn một phần. Không push/deploy hoặc sửa
snapshot email cũ. Muốn công bố lại chính sách cần nguồn công khai đã duyệt,
phiên bản/phạm vi/ngày hiệu lực; không tự động xuất tri thức nội bộ qua RAG.
