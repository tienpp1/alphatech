# Đợt 19 — Strict home-delivery fulfillment (opt-in)

## Phạm vi

- Dùng thông tin đã chốt: `BR-D1` là branch mặc định; `BR-BT` và `BR-D7` là
  fallback; thiếu tổng tồn thì hard-stop.
- Nhận GPS browser qua hidden form fields cho đúng lần checkout; không lưu lịch
  sử dụng vị trí vào hồ sơ khách hàng.
- Giữ tương thích các deployment cũ bằng cờ
  `HOME_DELIVERY_FULFILLMENT_POLICY=legacy|strict`.

## Thay đổi

- Thêm `apps/public_web/fulfillment.py`: validate tọa độ, khóa branch và
  `StockBalance`, chọn một branch có đủ toàn bộ dòng hàng, trừ tồn trong cùng
  transaction; không tạo đơn khi thiếu hàng.
- `public_checkout_place_order_view` gọi service khi policy là `strict`; pickup
  hiện có vẫn giữ nguyên.
- Checkout thêm nút xin quyền vị trí HTML5 và gửi tọa độ một lần; không có GPS
  vẫn checkout theo default/fallback đã cấu hình.
- Thêm các biến cấu hình vào `config/settings.py` và `.env.example`.

## Validation

```text
python manage.py test tests.test_home_delivery_fulfillment \
  --settings=config.settings_evidence_test --keepdb --noinput -v 1
4 tests passed

python manage.py test tests.test_public_ecommerce_cart_and_checkout \
  --settings=config.settings_evidence_test --keepdb --noinput -v 1
20 tests passed in 177.030s

python manage.py test tests.test_gis_spatial tests.test_public_branch_finder \
  --settings=config.settings_evidence_test --keepdb --noinput -v 1
11 tests passed in 0.979s

python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected
```

`git diff --check` không có whitespace error (chỉ cảnh báo chuyển LF/CRLF). Chưa
bật policy trên Render, chưa seed/đối chiếu tồn kho production
và chưa có bằng chứng live endpoint vì mạng môi trường local bị chặn.

SOP mapping input contract:

```text
python manage.py test tests.test_scope_benchmark_inputs \
  --settings=config.settings_evidence_test --keepdb --noinput -v 1
2 tests passed
```

Hai test này chỉ xác nhận source path và expected facts tồn tại trong file SOP;
chúng không thay thế retrieval, semantic grading hoặc xác nhận mọi SOP đã ingest
đúng workspace. Expected facts đã được sửa về đúng wording của SOP, ví dụ loaner
RMA là trên 07 ngày làm việc và ransomware ghi cô lập Internet Gateway thay vì
claim “WAN” không có nguyên văn trong file.

Checklist vẫn **35 đóng / 29 một phần / 33 chưa xác nhận**; mục home-delivery
được củng cố local nhưng chưa đóng production.
