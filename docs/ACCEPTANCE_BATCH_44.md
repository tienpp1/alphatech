# Đợt 44 — Nghiệm thu Hồ sơ Dữ liệu Thực nghiệm, Phân tích Sai số Dự báo & Đo lường Độ bao phủ

Ngày chốt: 22/09/2026.
Phạm vi: Cụm Cổng 17, 26, 83, 84 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).
Tài liệu trọng tâm: [docs/HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md](file:///d:/ai_business_platform/docs/HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 17: Giữ kết quả kém và phân tích nguyên nhân khoa học (Error Analysis)**:
  - Báo cáo trung thực kết quả thực nghiệm trên chuỗi doanh thu bán lẻ `RETAIL_REVENUE` (Run 1):
    - XGBoost: MAE = 38.436.778,67 VND, RMSE = 44.072.449,54 VND, MAPE = 2.033,22%, $R^2 = -3.6589$.
    - Naive Baseline: MAE = 27.712.533,33 VND, RMSE = 33.879.869,23 VND, MAPE = 187,12%, $R^2 = -1.7532$.
    - Kết quả so sánh: **XGBoost kém hơn Baseline -38,70% theo MAE**.
  - Phân tích sâu 4 nguyên nhân khoa học: Độ phân tán giá trị giỏ hàng cực lớn (High Variance & Sparse High-Value Items), Chuỗi quan sát hữu hạn (61 ngày) chưa học được mùa vụ tháng/năm, Hiện tượng trễ suy biến (Lag Feature Degradation), và Bản chất của Naive Baseline trên dữ liệu bậc thang.
  - Khẳng định đạo đức học thuật: Không giấu diếm kết quả kém, không bỏ bài toán doanh thu để chỉ chọn bài toán có kết quả tốt hơn (Run 2: Số đơn hàng tốt hơn +26,32%; Run 3: Số phiếu dịch vụ tốt hơn +27,13%).
  - Giải thích rõ ràng ý nghĩa của $R^2$ âm trong kiểm định ngoài mẫu: Mô hình chưa giải thích được phần lớn phương sai của chuỗi doanh thu và chưa phù hợp để tự động hóa đặt hàng.

- **Mục 26: Đo lường độ bao phủ thực nghiệm & Giới hạn khoảng tin cậy (Empirical Coverage)**:
  - Đo lường độ bao phủ thực nghiệm trên tập holdout 15 ngày của Run 1: Có **10/15 ngày** nằm trọn trong dải độ lệch chuẩn sai số danh nghĩa một bước ($\pm 1 \sigma$), đạt tỷ lệ bao phủ thực tế **66,7%** (khớp với phân phối chuẩn lý thuyết 68,27%).
  - Thiết lập ranh giới phương pháp rõ ràng: Cảnh báo dải danh nghĩa một bước (`one-step observed-history`) **không phải** khoảng tin cậy đã hiệu chuẩn (Calibrated Conformal Prediction) cho chân trời dự báo đệ quy 14 ngày (14-day recursive horizon).

- **Mục 83: Chuẩn hóa hồ sơ dữ liệu thực nghiệm (Data Catalog & Provenance Profile)**:
  - Lập đặc tả siêu dữ liệu chi tiết cho 2 bộ dữ liệu chuỗi thời gian: `AlphaTech-Retail-Timeseries` và `AlphaTech-Service-Timeseries`.
  - Quy định rõ nguồn gốc giao dịch thực tế `retail_order` và phiếu `service_ops_servicerequest`.
  - Phân tích chính sách zero-fill ngày thiếu (là giả định không có đơn, không chứng minh cửa hàng đóng cửa).
  - Xác nhận cơ chế phân chia thời gian Chronological Holdout Split (75% train / 25% test) và giải thích nhãn `no_separate_validation_partition`.
  - Định danh dấu vân tay SHA-256 (`dataset.fingerprint_sha256`) và mã băm cấu hình huấn luyện.

- **Mục 84: Chuẩn hóa bộ kết quả thực nghiệm có thể chạy lại độc lập (Reproducibility Protocol)**:
  - Cung cấp lệnh CLI chuẩn hóa `evaluate_academic_metrics` cho phép tái lập 100% kết quả bất kỳ lúc nào.
  - Đã xuất và lưu trữ 2 tệp báo cáo bằng chứng độc lập:
    - `output/academic_forecast_abc_retail_batch44.md`
    - `output/academic_forecast_xyz_service_batch44.md`

---

## 2. Kết quả Kiểm thử Tự động & Tính Nhất quán

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

```powershell
python manage.py test tests.test_academic_reporting tests.test_academic_report_command --keepdb
```
```text
Ran 14 tests in 0.166s
OK
System check identified no issues (0 silenced).
```

---

## 3. Tác động tới Tiến độ Checklist 97 Mục

- **Mục 17 (Giữ kết quả kém và phân tích nguyên nhân)**: Chuyển từ *Một phần* sang **Đóng**.
- **Mục 26 (Không coi dải hiển thị là khoảng tin cậy nếu chưa đo độ bao phủ)**: Chuyển từ *Một phần* sang **Đóng**.
- **Mục 83 (Chuẩn hóa hồ sơ dữ liệu: nguồn, kích thước, phiên bản, giới hạn)**: Chuyển từ *Một phần* sang **Đóng**.
- **Mục 84 (Chuẩn hóa bộ kết quả thực nghiệm có thể chạy lại)**: Chuyển từ *Một phần* sang **Đóng**.

**Bảng Thống kê Tiến độ Cập nhật:**
- **Đóng hoàn toàn:** **70 / 97 mục (72,16% làm tròn 72,2%)** (tăng thêm 4 mục: 17, 26, 83, 84).
- **Một phần:** **16 mục** (16,5%) (giảm 4 mục).
- **Chưa xác nhận đóng:** **11 mục** (11,3%).
- Mẫu số gốc **97 mục** được bảo toàn 100%, không suy diễn.
