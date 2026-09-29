# Thực nghiệm doanh thu tổng hợp có snapshot — 24/09/2026

## Phạm vi và nguồn dữ liệu

Đây là thực nghiệm offline mới, không truy cập database và không thay thế hay
khôi phục kết quả Batch 44. Không suy ra hiệu quả kinh doanh từ dữ liệu tổng hợp.
Các kết quả lịch sử thiếu snapshot vẫn chưa tái lập được.

Nguồn: `scripts/forecast_reproducible_experiment.py`, bộ sinh `synthetic_formula_v1`,
seed NumPy 20260924. Có 180 quan sát ngày 01/01–29/06/2026, đơn vị VND.
Công thức: 1.000.000 + 4.500 × chỉ số ngày + 350.000 nếu cuối tuần + nhiễu
Normal(0, 120.000); làm tròn, chặn dưới bằng 0. Đây không phải giao dịch thật.
Snapshot đầu vào chỉ có date/target, không có thông tin khách hàng.
Không zero-fill ngầm: thiếu ngày, trùng ngày, số không hữu hạn hoặc doanh thu âm
đều bị từ chối. Không có tìm kiếm tham số hay lựa run theo kết quả đẹp.

## Thiết kế đã thực thi

Tái sử dụng feature và metrics trong ứng dụng. Sau bỏ 14 ngày đầu thiếu lag,
166 hàng được chia theo thời gian: 99 train, 33 calibration, 34 test.
XGBoost 100 cây, depth 4, learning rate 0,05, subsample/colsample 0,8,
seed 42, n_jobs=1. Toàn bộ cấu hình và tên feature nằm trong `config.json`.
Model chỉ fit train, không dùng test làm eval_set hay early stopping.

Đánh giá **one-step observed-history**, không phải dự báo đệ quy 14 ngày.
Lag-7 và trung bình trượt 7 ngày dùng cùng lịch sử quan sát được như model.
Dải minh họa dùng ±1,96 × RMSE trên calibration trước test. Hệ số 1,96 không
chứng minh coverage 95%; không phải khoảng đã hiệu chỉnh xác suất.

| Phương pháp | MAE (VND) | RMSE (VND) | MAPE (%) | R² |
|---|---:|---:|---:|---:|
| XGBoost | 165.179,49 | 193.953,63 | 8,80 | 0,1861 |
| Lag-7 | 153.289,00 | 197.458,10 | 8,45 | 0,1565 |
| Moving average-7 | 170.029,15 | 218.949,58 | 9,12 | −0,0372 |

XGBoost **kém lag-7 về MAE và MAPE**, tốt hơn về RMSE trên tập test này;
không kết luận vượt trội tổng thể. Coverage thực đếm từ actual/lower/upper:
**29/34 = 85,29%**. Giữ cả 5 ngày nằm ngoài dải trong CSV.

## Artifact và tái chạy

Gói gốc: `output/forecast_repro_20260924/`; replay độc lập:
`output/forecast_repro_20260924_replay/`. Mỗi gói có dataset.csv, model.json,
calibration_predictions.csv, test_predictions.csv, config.json, results.json,
manifest.json. Manifest ghi SHA256 từng file, nguồn code và phiên bản runtime.
Runtime lần chạy này: Python 3.14.5, NumPy 2.4.3, pandas 3.0.1, XGBoost 3.4.1.
Không bảo đảm bitwise identity trên mọi hệ điều hành/phiên bản thư viện.

```powershell
python scripts/forecast_reproducible_experiment.py --output output/forecast-new
python scripts/forecast_reproducible_experiment.py --dataset output/forecast-new/dataset.csv --output output/forecast-replay-new
```

Đường dẫn output phải chưa tồn tại. Hai lần CLI đã chạy thành công và trả cùng
kết quả. Test kiểm tra byte predictions, toàn bộ file hash, tính lại coverage,
và từ chối ghi đè gói cũ. Dataset SHA256:
`66f28a3f548de03178bcce8cc0650e2235c2ee2680b34b1f0ac3c7c9c85ddb09`.

## Kiểm tra thực thi

```powershell
python manage.py test tests.test_forecast_experiment_bundle tests.test_forecasting_training tests.test_forecasting_dataset tests.test_academic_reporting --settings=config.settings_evidence_test --noinput -v 1
python manage.py test tests.test_academic_test_manifest_audit tests.test_acceptance_log_summary --settings=config.settings_evidence_test --noinput -v 1
python manage.py check
python manage.py makemigrations --check --dry-run
```

Kết quả: nhóm dự báo **28 tests OK, 16.250s**; nhóm hồ sơ **12 tests OK,
4.559s**. `check`: no issues; migration: no changes detected. Discovery 1.095
chỉ là kiểm kê, không phải 1.095 pass. `git diff --check` trên các file đã sửa
không báo lỗi whitespace (có cảnh báo chuyển LF/CRLF của Git).

## Phần còn thiếu

Gói này bổ sung bằng chứng cho mục 26/83/84. Mục 83/84 toàn hệ thống còn cần
dataset và kết quả RAG/approval cùng hồ sơ đánh giá ngữ nghĩa độc lập; không
đóng cả hai mục chỉ vì một thực nghiệm doanh thu tái lập được. Coverage cũ
10/15 vẫn bị thu hồi, không thay thế số cũ bằng số mới mà bỏ nhãn nguồn.
UI dự báo giờ ghi rõ dải tham khảo chưa hiệu chỉnh, không đổi công thức model.
