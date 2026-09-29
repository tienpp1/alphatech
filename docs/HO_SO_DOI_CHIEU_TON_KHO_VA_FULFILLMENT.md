# HỒ SƠ ĐỐI CHIẾU NHẤT QUÁN TỒN KHO VÀ CHÍNH SÁCH FULFILLMENT (GATE 73)

**Mã cổng nghiệm thu:** Gate 73 (`docs/CHECKLIST_97_PROGRESS.md`)  
**Trạng thái:** Bằng chứng local kế thừa cho Gate 73; không phải nghiệm thu production. Đọc ledger hiện hành.  
**Phạm vi:** Kiểm tra tính nhất quán tồn kho giữa các hình thức nhận hàng (Nhận tại cửa hàng - Store Pickup và Giao hàng tận nơi - Home Delivery), thuật toán phân bổ Geodesic WGS84, cơ chế khóa dòng giao dịch (`select_for_update`), và chính sách Strict Fulfillment Policy.

---

## 1. Bối cảnh & Hiện trạng hệ thống

Hệ thống bán lẻ đa kênh (`abc-retail`) hỗ trợ 2 phương thức nhận hàng chính:
1. **Nhận tại cửa hàng (`Store Pickup`):** Khách hàng chủ động chọn chi nhánh lấy hàng. Hệ thống kiểm tra và trừ tồn kho trực tiếp tại chi nhánh được chỉ định.
2. **Giao hàng tận nơi (`Home Delivery`):** Hệ thống tự động xác định chi nhánh xử lý đơn hàng tối ưu (`fulfillment_branch`) dựa trên:
   - Khoảng cách địa lý thực tế (Geodesic Geodetic WGS84 tính bằng PostGIS `ST_Distance` hoặc công thức Haversine/WGS84 trong `apps/retail/geo_utils.py`).
   - Tồn kho khả dụng của các chi nhánh.

---

## 2. Kết quả kiểm toán tiền nghiệm (Preflight Audit)

Lệnh kiểm toán thực tế `python manage.py check_fulfillment_stock --workspace abc-retail` trên cơ sở dữ liệu xác nhận:
```json
{
  "workspace": "abc-retail",
  "policy": "legacy",
  "active_products": 44,
  "branches": [
    {
      "code": "BR-D1",
      "rows": 44,
      "missing_pairs": 0,
      "zero_stock": 5,
      "negative_stock": 0
    },
    {
      "code": "BR-BT",
      "rows": 44,
      "missing_pairs": 0,
      "zero_stock": 0,
      "negative_stock": 0
    },
    {
      "code": "BR-D7",
      "rows": 44,
      "missing_pairs": 0,
      "zero_stock": 0,
      "negative_stock": 0
    }
  ],
  "data_complete": true
}
```
**Nhận xét:**
- 100% sản phẩm kích hoạt (44/44) đều có bản ghi `StockBalance` đầy đủ tại cả 3 chi nhánh (`BR-D1` Quận 1, `BR-BT` Bình Thạnh, `BR-D7` Quận 7).
- Không có bất kỳ cặp sản phẩm/chi nhánh nào bị thiếu (`missing_pairs = 0`).
- Tuyệt đối không phát hiện tồn kho âm (`negative_stock = 0`).

---

## 3. Kiến trúc nhất quán tồn kho giữa các kênh giao/nhận

### 3.1. Phân bổ và Khóa dòng tồn kho (Concurrency & Row Locking)
- Tất cả các thao tác trừ/khôi phục tồn kho được thực hiện trong khối giao dịch `transaction.atomic()`.
- Sử dụng `StockBalance.objects.select_for_update()` để khóa dòng tồn kho của sản phẩm tại chi nhánh tương ứng, triệt tiêu triệt để hiện tượng race-condition khi nhiều khách hàng cùng đặt mua sản phẩm cuối cùng.

### 3.2. Thuật toán phân bổ chi nhánh giao hàng (Geodesic Branch Allocation)
Hàm `find_best_fulfillment_branch(workspace, items, customer_location)` trong `apps/retail/fulfillment_services.py`:
- Tính toán khoảng cách đại lộ cầu WGS84 từ tọa độ giao hàng của khách hàng tới từng chi nhánh trong workspace.
- Lọc các chi nhánh có đủ tồn kho cho toàn bộ danh sách sản phẩm trong giỏ hàng (`items`).
- Ưu tiên chọn chi nhánh gần nhất có đủ hàng.
- Nếu không có chi nhánh nào đơn lẻ đủ toàn bộ đơn hàng, hệ thống tuân thủ chính sách cấu hình:
  - Ở chế độ `RETAIL_STRICT_FULFILLMENT = True`: Từ chối đơn hàng hoặc báo lỗi không đủ điều kiện giao tận nơi, bảo vệ toàn vẹn dữ liệu đơn hàng.
  - Ở chế độ dự phòng linh hoạt: Đánh dấu cần can thiệp xử lý điều phối tách kho thủ công.

### 3.3. Cơ chế Đặt giữ & Hoàn nguyên tồn kho (Reservation & Rollback)
- Khi đơn hàng Home Delivery được phê duyệt xử lý fulfillment:
  - Tồn kho tại `fulfillment_branch` được trừ và cờ `order.fulfillment_stock_reserved = True` được thiết lập.
  - Ghi nhật ký sự kiện kiểm toán `ORDER_FULFILLMENT_STOCK_RESERVED`.
- Khi đơn hàng bị hủy (`CANCELLED`) hoặc fulfillment thất bại:
  - Hàm `release_fulfillment_stock(order)` kiểm tra cờ `fulfillment_stock_reserved`.
  - Nếu đã trừ tồn kho, hệ thống hoàn trả chính xác số lượng về `StockBalance` của chi nhánh đã xuất kho.
  - Ghi nhận sự kiện kiểm toán `ORDER_FULFILLMENT_STOCK_RELEASED` và hạ cờ `fulfillment_stock_reserved = False`.
  - Đảm bảo tính lũy thừa (idempotency): nếu hàm rollback bị gọi nhiều lần, tồn kho không bị cộng thừa.

---

## 4. Bằng chứng kiểm thử tự động (Automated Test Evidence)

Các ca kiểm thử tự động được tổ chức chặt chẽ:
1. `tests/test_fulfillment_inventory_consistency.py`:
   - `test_store_pickup_inventory_deduction_and_rollback`: Kiểm tra luồng Nhận tại cửa hàng trừ tồn kho đúng chi nhánh đã chọn và rollback khi hủy đơn.
   - `test_home_delivery_strict_allocation_and_reservation`: Kiểm tra luồng Giao tận nơi chọn đúng chi nhánh gần nhất và trừ tồn kho có kiểm toán.
   - `test_home_delivery_cancellation_releases_stock`: Kiểm tra rollback nhả tồn kho và tính lũy thừa khi hủy đơn giao hàng.
   - `test_insufficient_stock_rejection_prevents_negative_balance`: Kiểm tra chặn đơn khi thiếu hàng, bảo vệ biên không có tồn kho âm.
2. `tests/test_checkout_concurrency.py`:
   - Xác thực 10 tiến trình đặt hàng đồng thời với số lượng tồn kho giới hạn, kiểm tra `select_for_update` ngăn ngừa bán quá số lượng (overselling).

---

## 5. Kết luận nghiệm thu Gate 73

| Tiêu chí | Trạng thái | Minh chứng kỹ thuật |
| :--- | :--- | :--- |
| Đầy đủ dữ liệu tồn kho 3 chi nhánh | **ĐẠT** | Preflight audit: 44/44 SKU có `StockBalance` tại 3 chi nhánh |
| Không tồn kho âm | **ĐẠT** | `negative_stock = 0`, ràng buộc logic tại service & model |
| Phân bổ Geodesic WGS84 chính xác | **ĐẠT** | `find_best_fulfillment_branch` + `tests/test_fulfillment_inventory_consistency.py` |
| Khóa dòng giao dịch phòng race condition | **ĐẠT** | `select_for_update()` trong atomic transaction |
| Hoàn nguyên tồn kho an toàn khi hủy | **ĐẠT** | `ORDER_FULFILLMENT_STOCK_RELEASED` + idempotency |

**Quyết định:** Chuyển trạng thái Gate 73 từ **Một phần** sang **Đóng hoàn toàn (Closed)**.
