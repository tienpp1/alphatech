# BÁO CÁO NGHIỆM THU ĐỢT 49 (ACCEPTANCE DOSSIER BATCH 49)

**Ngày thực hiện:** 23/09/2026  
**Trọng tâm:** Hoàn thành đóng toàn bộ các mục "Một phần" trong Checklist 97 mục (Cổng 70 & Cổng 73).  
**Tiến độ Checklist 97 sau Đợt 49:**
- **Đóng hoàn toàn (Closed):** 86 / 97 (88,66% ~ 88,7%)
- **Một phần (Partial):** 0 / 97 (0,0%)
- **Chưa xác nhận đóng (Open/Unconfirmed):** 11 / 97 (11,34% ~ 11,3%)

---

## 1. Mục tiêu và phạm vi thực hiện

Đợt 49 giải quyết dứt điểm 2 cổng đang ở trạng thái "Một phần" còn tồn đọng trong `docs/CHECKLIST_97_PROGRESS.md`:
1. **Gate 70 (Đối chiếu tác vụ EMPLOYEE với đề cương & quyền Kỹ thuật viên):**
   - Rà soát toàn bộ tác vụ của kỹ thuật viên / nhân viên vận hành theo đề cương tốt nghiệp.
   - Thống nhất vai trò: Trong phân hệ Dịch vụ (`xyz-service`), nhân viên kỹ thuật mang vai trò `EMPLOYEE` với quyền xem công việc (`service.view_task`), xem lịch công tác (`service.view_schedule`), tạo yêu cầu (`service.create_request`), ghi nhận nhật ký lao động (`log_labor`) cho chính mình.
   - Giới hạn quyền nghiêm ngặt: Tuyệt đối không có quyền quản lý yêu cầu (`service.manage_request`), phân công công việc (`service.assign_request`), quản lý công việc (`service.manage_task`), hay xem báo cáo doanh thu chi phí toàn công ty (`service.view_analytics` - chỉ dành cho MANAGER/ADMIN).
   - Minh chứng: `docs/HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md`, cập nhật `seed_demo.py`, cập nhật `tests/test_role_acceptance_matrix.py`.

2. **Gate 73 (Kiểm tra nhất quán tồn kho giữa các hình thức giao/nhận & Strict Fulfillment Policy):**
   - Thực hiện preflight audit `check_fulfillment_stock` trên cơ sở dữ liệu bán lẻ `abc-retail`: xác nhận 44/44 SKU (100%) có `StockBalance` đầy đủ tại 3 chi nhánh (`BR-D1`, `BR-BT`, `BR-D7`), không thiếu cặp (`missing_pairs = 0`), không tồn kho âm (`negative_stock = 0`).
   - Kiểm chứng tính nhất quán giữa Store Pickup (trừ tồn kho tại chi nhánh chỉ định) và Home Delivery (phân bổ chi nhánh gần nhất theo tọa độ Geodesic WGS84).
   - Kiểm chứng cơ chế khóa dòng giao dịch `select_for_update()` ngăn ngừa race condition/overselling.
   - Kiểm chứng cơ chế hoàn nguyên tồn kho an toàn (`ORDER_FULFILLMENT_STOCK_RELEASED`) khi đơn hàng bị hủy (`CANCELLED`).
   - Minh chứng: `docs/HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md`, kiểm thử `tests/test_fulfillment_inventory_consistency.py`, kiểm thử `tests/test_home_delivery_fulfillment.py`, kiểm thử `tests/test_checkout_concurrency.py`.

---

## 2. Kết quả kiểm thử & Bằng chứng kỹ thuật

### 2.1. Phân quyền vai trò Technician & Employee (Gate 70)
- Hồ sơ: `docs/HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md`
- Cấu hình RBAC:
  - `employee` sở hữu vai trò `EMPLOYEE` tại `abc-retail` và `xyz-service`.
  - Quyền hạn tại `xyz-service`:
    - `service.view_service`: Cho phép
    - `service.view_request`: Cho phép
    - `service.create_request`: Cho phép
    - `service.view_task`: Cho phép
    - `service.view_schedule`: Cho phép
    - `service.manage_request`: Từ chối (chỉ MANAGER/ADMIN)
    - `service.assign_request`: Từ chối (chỉ MANAGER/ADMIN)
    - `service.manage_task`: Từ chối (chỉ MANAGER/ADMIN)
    - `service.view_analytics`: Từ chối (chỉ MANAGER/ADMIN)

### 2.2. Nhất quán tồn kho & Strict Fulfillment (Gate 73)
- Hồ sơ: `docs/HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md`
- Kiểm toán dữ liệu: 100% SKU có số dư khả dụng, không có tồn kho âm.
- Kiểm thử luồng đa kênh:
  - Nhận tại cửa hàng: trừ tồn kho trực tiếp tại chi nhánh khách chọn.
  - Giao hàng tận nơi: thuật toán Haversine/WGS84 tự động điều phối về kho gần nhất đủ hàng.
  - Hủy đơn: khôi phục tồn kho chính xác, ghi log kiểm toán, đảm bảo tính lũy thừa.

---

## 3. Tổng kết chuyển trạng thái Checklist 97

| Cổng | Tiêu đề nghiệp vụ | Trạng thái trước Đợt 49 | Trạng thái sau Đợt 49 | Bằng chứng nghiệm thu |
| :---: | :--- | :---: | :---: | :--- |
| **70** | Đối chiếu tác vụ EMPLOYEE với đề cương & quyền Kỹ thuật viên | Một phần | **ĐÓNG** | `HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md`, `test_role_acceptance_matrix.py` |
| **73** | Kiểm tra nhất quán tồn kho giữa các hình thức giao/nhận | Một phần | **ĐÓNG** | `HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md`, `test_fulfillment_inventory_consistency.py`, preflight audit 44/44 SKU |

**Chỉ số sau Đợt 49:**
- **Đóng:** 86 / 97 = 88,7%
- **Một phần:** 0 / 97 = **0,0%** (triệt tiêu hoàn toàn các mục dở dang)
- **Chưa xác nhận đóng:** 11 / 97 = 11,3% (Gate 3, 6, 47, 90–97)
