# Đợt 20 — Biên an toàn phân bổ tồn và kiểm tra trước triển khai

## Đối chiếu file thông tin mới

Đã đọc `1. Chốt phạm vi nghiệp vụ (Phân tíc.txt`, không sửa file gốc.
Các kết luận cần giới hạn:

- Đủ dòng StockBalance chỉ chứng minh độ phủ dữ liệu tại thời điểm đọc; không
  chứng minh mọi giỏ hàng đủ tại một chi nhánh hoặc tồn thực tế đã đối soát.
  Hệ thống hiện không tách đơn nhiều kho.
- Số đếm tài liệu/chunks không chứng minh semantic grounding, embedding API thật
  hay mọi truy vấn đều cách ly workspace đúng.
- Timeout chưa đủ kết luận nguyên nhân là Render ngủ hoặc firewall.
- HEAD không đại diện cho thay đổi chưa commit. Không dùng SHA cũ làm bằng chứng
  tái hiện worktree mới; không tự push tất cả output Word/test/model artifacts.

## Thay đổi và kiểm chứng

- Service chỉ chọn kho trung tâm và dự phòng đã cấu hình, không chọn ngầm branch khác.
- Gộp dòng trùng trước kiểm tra/trừ tồn; từ chối lượng phân số/boolean thay vì ép int.
- Kiểm tra sản phẩm active, chưa xóa và cùng workspace ngay tại service, kể cả
  StockBalance liên kết sai workspace. Khóa theo thứ tự xác định trong transaction.
- Phân biệt `NO_SINGLE_BRANCH_STOCK` (hàng phân tán) với thiếu tổng tồn.
  Không thêm chia đơn; bỏ hotline hard-code khỏi lỗi.
- Đánh dấu rõ đơn nào đã reserve tồn bằng `fulfillment_stock_reserved`; strict
  home delivery và store pickup chỉ set cờ sau khi trừ tồn thành công. Hủy đơn khóa lại Order và
  StockBalance, hoàn tồn đúng một lần qua `fulfillment_stock_released_at`, và
  abort toàn bộ nếu thiếu dòng tồn để tránh hoàn một phần.
- Thêm migration `retail.0007_order_fulfillment_reservation` và regression cho
  reserve, hoàn tồn khi hủy, retry terminal-state và dữ liệu tồn không đầy đủ.
- Lệnh mới chỉ đọc, bắt buộc workspace:

```text
python manage.py check_fulfillment_stock --workspace abc-retail
```

Xuất số đếm missing/zero/negative theo kho; không xuất thông tin khách hàng,
credential hoặc tự bật strict. `data_complete` không phải production READY.

Validation:

```text
python manage.py test tests.test_home_delivery_fulfillment --settings=config.settings_evidence_test --keepdb --noinput -v 1
13/13 passed (4 test cũ + 9 test mới)
python manage.py test tests.test_retail_orders --settings=config.settings_evidence_test --keepdb --noinput -v 1
5/5 passed
python manage.py test tests.test_public_ecommerce_cart_and_checkout.PublicEcommerceCartAndCheckoutTestCase.test_store_pickup_and_branch_stock_deduction tests.test_public_ecommerce_cart_and_checkout.PublicEcommerceCartAndCheckoutTestCase.test_missing_pickup_stock_rejects_without_order --settings=config.settings_evidence_test --keepdb --noinput -v 1
2/2 passed
python manage.py check
0 issues
python manage.py makemigrations --check --dry-run
No changes detected
git diff --check
exit 0, chỉ có cảnh báo LF/CRLF
```

Lần đầu dùng `.venv/Scripts/python.exe` không khởi chạy test vì thiếu Django.
Sau khi xác định runtime Python314/Django 6.0.2 hiện hành, lệnh trên chạy được;
không cài package, không sửa assertions để né lỗi.

Lệnh chỉ đọc trên database cấu hình local xác nhận: policy legacy, 44 sản phẩm;
BR-D1/BR-BT/BR-D7 mỗi nơi 44 dòng, missing=0, negative=0. BR-D1 zero=5,
hai kho còn lại zero=0. Không suy diễn đây là production database.

## Còn lại

Không bật strict trên Render, không sửa secrets, không push/deploy hoặc sửa dữ liệu
nghiệp vụ. Checklist vẫn 35 đóng / 29 một phần / 33 chưa xác nhận.
Mục 73 được củng cố với lifecycle hoàn tồn local nhưng vẫn cần kiểm tra cạnh
tranh checkout, migration và phiên bản triển khai thực tế. Home delivery legacy
không trừ tồn nên không tạo reservation. RAG semantic và production vẫn riêng.
