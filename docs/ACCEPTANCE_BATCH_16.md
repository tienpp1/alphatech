# Đợt 16 — Audit vòng đời Task và forecasting worker

Ngày đối chiếu: 15/09/2026.

## Mục tiêu

Gộp hai kiểm tra có thể xác minh độc lập trong cùng một lượt: làm cho audit
chuyển trạng thái Task ghi đủ snapshot vòng đời, và kiểm tra queue forecasting
durable cùng các giới hạn RBAC/API hiện có. Đây là bằng chứng local; không suy
rộng thành chứng nhận production worker sau restart.

## Thay đổi mã nguồn

- `apps/service_ops/services.py`: `TASK_STATUS_CHANGED` hiện lưu `before` và
  `after` gồm trạng thái, `started_at`, `completed_at`, thời lượng thực tế và
  `assigned_to_id`. Không đổi route, response hay schema database.
- `apps/retail/services.py`: audit `GOODS_RECEIPT_RECEIVED` lưu từng thay đổi
  tồn kho trước/sau, lượng nhận và việc tạo mới `StockBalance`.
- `tests/test_service_tasks.py`: regression đọc AuditLog thực tế cho snapshot
  vòng đời sau khi Task chuyển `PENDING → IN_PROGRESS → COMPLETED`.
- `tests/test_retail_goods_receiving.py`: regression đối chiếu snapshot tồn kho
  cho số dư cũ và số dư được tạo mới.
- `apps/forecasting/evaluation.py` và `training.py`: lưu coverage thực nghiệm
  một bước của dải chẩn đoán cùng nominal coverage và nhãn phương pháp; không
  gọi đây là calibration của dự báo đệ quy.
- `tests/test_forecasting_training.py`: kiểm tra coverage và metadata giới hạn.

## Bằng chứng

```powershell
python manage.py test tests.test_service_tasks --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **2 test passed, 3.737 giây**.

```powershell
python manage.py test tests.test_forecasting_queue tests.test_forecasting_security_rbac tests.test_forecasting_api --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **14 test passed, 71.870 giây**. Nhóm này xác minh queue không mất
run trước claim, lease/heartbeat fencing và recovery sau expiry, retry có giới
hạn, cancellation, cùng các kiểm tra API/RBAC forecasting hiện có.

```powershell
python manage.py test tests.test_retail_goods_receiving --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **6 test passed, 19.796 giây**.

```powershell
python manage.py test tests.test_service_schedules tests.test_approval_state_integrity --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **11 test passed, 35.086 giây**; các luồng lịch dịch vụ và approval
state integrity không bị hồi quy.

```powershell
python manage.py test tests.test_forecasting_training tests.test_forecasting_dataset --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **13 test passed, 6.337 giây**. Chronological split, baseline,
product-demand dimensions, MAPE zero-actual và coverage metadata đều qua.

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

Kết quả: Django check không có lỗi; migration drift không có; diff không có
lỗi whitespace (chỉ còn cảnh báo chuyển LF/CRLF của Git trên Windows).

## Tác động tới checklist 97 mục

Mục 67 được bổ sung bằng chứng before/after cho Task lifecycle, nhưng vẫn là
**Một phần** vì chưa bao phủ mọi action (lập lịch, nhận hàng, middleware/API),
outer transaction và độ đầy đủ audit toàn hệ thống. Mục 92 vẫn **Chưa xác nhận
đóng**: worker durable đã có test local, nhưng chưa có deployment production,
restart thật, heartbeat quan sát được hoặc recovery trên hạ tầng thật.

Mục 26 được nâng từ **Chưa xác nhận** lên **Một phần**: run lưu coverage một
bước trên holdout, nhưng dải recursive 14 ngày vẫn chưa có coverage/backtest
độc lập và chưa được xem là calibrated.

Tổng conservative: **35 đóng / 29 một phần / 33 chưa xác nhận**;
35/97 = **36,1%**. Không tính test lặp thành mục mới và không tuyên bố
production.

## Giới hạn

- Không chạy full suite 607 test.
- Không chạy worker thật trên Render và không giả lập restart production.
- Không sửa các AI demonstration failure chưa có bằng chứng mới trong đợt này.
- Không push/deploy hoặc thay đổi secret/database nghiệp vụ.
