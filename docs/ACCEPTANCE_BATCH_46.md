# Đợt 46 — Nghiệm thu Toàn diện Hệ thống Vết Kiểm toán (Audit Trail) & Ràng buộc Quyền/Bất biến

Ngày chốt: 22/09/2026.  
Phạm vi: Cụm Cổng 67 & 78 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) (Hàng 16) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).  
Tài liệu kiểm toán trọng tâm: [docs/HO_SO_KIEM_TOAN_AUDIT_TRAIL.md](file:///d:/ai_business_platform/docs/HO_SO_KIEM_TOAN_AUDIT_TRAIL.md).  
Tệp kiểm thử cốt lõi: [tests/test_audit_trail_evidence.py](file:///d:/ai_business_platform/tests/test_audit_trail_evidence.py) và [tests/test_audit_database_evidence.py](file:///d:/ai_business_platform/tests/test_audit_database_evidence.py).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 67: Đo audit từ sự kiện thực tế, ghi nhận đầy đủ actor, thời gian, trước/sau và hoàn tác**:
  - Biên soạn tài liệu học thuật [docs/HO_SO_KIEM_TOAN_AUDIT_TRAIL.md](file:///d:/ai_business_platform/docs/HO_SO_KIEM_TOAN_AUDIT_TRAIL.md) thiết lập danh mục định danh 28 hành động kiểm toán (Action Type Inventory) xuyên suốt 4 phân hệ cốt lõi: Bán lẻ (Retail), Vận hành Dịch vụ (Service Ops), Phê duyệt Human-in-the-Loop (Approvals), và An ninh Hệ thống (Security).
  - Triển khai bộ kiểm thử tự động chuyên sâu [tests/test_audit_trail_evidence.py](file:///d:/ai_business_platform/tests/test_audit_trail_evidence.py) gồm 8 trường hợp kiểm thử thực nghiệm trên cơ sở dữ liệu PostgreSQL thật:
    1. **Labor Entry Audit**: Ghi nhận chính xác người thực hiện (`actor_user`), thời gian thực thi (`timestamp`), `duration_minutes` (90 phút), lưu ảnh chụp tỷ giá công lao động tại thời điểm tạo (`hourly_rate_snapshot` = 350.000 VNĐ) và chi phí lao động tính toán phía máy chủ (`labor_cost` = 525.000 VNĐ).
    2. **Schedule Allocation Audit**: Ghi nhận việc lập lịch điều phối kỹ thuật viên với ranh giới thời gian `start_time`, `end_time` và liên kết nhiệm vụ `task_id`.
    3. **Task Lifecycle Snapshot**: Chụp ảnh trạng thái trước (`before`) và sau (`after`) khi chuyển trạng thái Task (`PENDING` $\to$ `IN_PROGRESS` $\to$ `COMPLETED`), tự động lưu thời điểm bắt đầu/kết thúc và thời lượng thực tế `actual_duration_minutes`.
    4. **Retail Order Lifecycle & Fulfillment Audit**: Chụp trạng thái đơn hàng (`ORDER_CONFIRMED`, `ORDER_CANCELLED`), ghi nhận provenance địa chỉ IP (`127.0.0.1`) và kích hoạt quy trình hoàn trả hàng dự phòng một cách minh bạch.
    5. **Stock Transfer & Rollback Balance Snapshot**: Xác nhận giao dịch điều chuyển tồn kho giữa Chi nhánh A và Chi nhánh B (`STOCK_TRANSFER_EXECUTED`) ghi nhận chính xác số dư tồn kho trước và sau của cả hai chi nhánh; quy trình bù trừ (`STOCK_TRANSFER_ROLLED_BACK`) khôi phục nguyên trạng số lượng tồn kho và lưu vết lý do hoàn tác.
    6. **Master Catalog Lifecycles**: Lưu vết chi tiết thay đổi từng trường thuộc tính khi cập nhật Danh mục sản phẩm (`Category`) và Nhà cung cấp (`Supplier`).
    7. **Permission Denial Auditing**: Xác thực việc từ chối người dùng không đủ quyền khi cố gắng can thiệp duyệt yêu cầu (`process_approval_decision`) được ghi vết với mã hành động `APPROVAL_PERMISSION_DENIED` kèm `error_code="PERMISSION_DENIED"`.
    8. **PostgreSQL Trigger Tamper-Resistance**: Kiểm chứng việc hàm trigger `prevent_audit_tampering()` trên bảng `audit_auditlog` chặn đứng hoàn toàn mọi thao tác can thiệp trực tiếp bằng SQL raw (`UPDATE` và `DELETE`), ném ra lỗi `DatabaseError: AuditLog is append-only`.

- **Mục 78: Không sửa quyền rộng hơn hoặc làm yếu assertion để đạt test**:
  - Bảo lưu nguyên tắc RBAC phân quyền tối thiểu và bảo vệ bất biến cách ly không gian (workspace isolation).
  - Toàn bộ các kiểm tra quyền trong `apps/approvals/executor.py` và `apps/accounts/services.py` được giữ nguyên vẹn; kiểm thử khẳng định ngoại lệ `ToolPermissionDenied` được ném ra chính xác khi người dùng thiếu quyền `approvals.manage_approval`.
  - Các xác minh kiểm thử (assertions) yêu cầu đối chiếu trường-theo-trường (field-level comparison) của dữ liệu trước/sau (before/after snapshots) thay vì chỉ kiểm tra sự tồn tại bề mặt.

---

## 2. Kết quả Kiểm thử Tự động & Bằng chứng Thực nghiệm

### 2.1. Kiểm tra Toàn vẹn Hệ thống (System Integrity)

```powershell
python manage.py check
```
```text
System check identified no issues (0 silenced).
```

```powershell
python manage.py makemigrations --check --dry-run
```
```text
No changes detected
```

### 2.2. Kiểm thử Bộ bằng chứng Vết Kiểm toán (Audit Trail Evidence)

```powershell
python manage.py test tests.test_audit_trail_evidence tests.test_audit_database_evidence --keepdb
```
```text
Using existing test database for alias 'default'...
..........
----------------------------------------------------------------------
Ran 10 tests in 23.325s

OK
Preserving test database for alias 'default'...
Found 10 test(s).
System check identified no issues (0 silenced).
```

### 2.3. Kiểm thử Hồi quy Nghiệp vụ (Regression Verification)

```powershell
python manage.py test tests.test_service_tasks tests.test_service_labor tests.test_retail_goods_receiving --keepdb
```
```text
Using existing test database for alias 'default'...
..............
----------------------------------------------------------------------
Ran 14 tests in 90.976s

OK
Preserving test database for alias 'default'...
Found 14 test(s).
System check identified no issues (0 silenced).
```

Tổng cộng: **24 test case chuyên sâu vượt qua 100%** mà không cần bỏ qua hoặc nới lỏng bất kỳ kiểm tra an ninh nào.

---

## 3. Cập nhật Bảng Tiến độ Checklist 97

- **Mục 67**: Chuyển trạng thái từ **Một phần** $\to$ **Đóng**.
- **Mục 78**: Chuyển trạng thái từ **Một phần** $\to$ **Đóng**.
- **Tiến độ lũy kế mới**:
  - **Đóng hoàn toàn (Closed with Evidence)**: **78 / 97 mục (80,4%)** (trước: 76 mục, 78,4%).
  - **Một phần (Partially Closed)**: **8 / 97 mục (8,2%)** (trước: 10 mục, 10,3%). Còn lại các mục: 43, 44, 45, 46, 48, 70, 73, 86.
  - **Chưa xác nhận đóng (Unconfirmed / Production Scope)**: **11 / 97 mục (11,3%)** (các mục: 3, 6, 47, 90, 91, 92, 93, 94, 95, 96, 97).
  - **Mẫu số kiểm soát**: Đúng **97 mục gốc**, không biến đổi hay suy diễn.
