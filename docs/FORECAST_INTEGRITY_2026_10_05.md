# Đợt 05/10 — Dự báo có cấu hình và bằng chứng đúng

Phục vụ đối chiếu nhóm 18/20/22/23/24/83/84/85, không sửa trạng thái hoặc cấu
trúc ledger 97. Không mở lại các quyết định Local Storage, worker production
tắt, off-site backup hoãn và phạm vi action advisory đã chốt.

## Root causes và sửa đổi

- Inference hard-code lag 1/7/14, windows 7/14, calendar dù training hỗ trợ cấu
  hình khác: dùng lại build_features với provenance lưu ở run.
- Rolling std inference dùng population std, training dùng sample std: builder
  chung khắc phục lệch feature. Predictions sau mỗi bước trở thành history,
  tuyệt đối không nhận actual của các ngày tương lai.
- model_config có thể sửa sau training: ưu tiên snapshot feature/columns,
  granularity/dimensions; run cũ thiếu provenance chỉ fallback cấu hình hiện có,
  không giả định tái lập được cấu hình lịch sử.
- Weekly total trước đây dự báo trên ngày liên tiếp: giữ nhịp 7 ngày. Tham số
  horizon_days vẫn là số điểm như interface hiện có; tên gọi lịch sử còn hạn chế.
- RMSE thiếu/âm/không finite bị thay 1; RMSE zero cũng bị thay 1: thiếu/invalid
  trả bounds null, zero giữ zero. Không tuyên bố interval calibrated.
- Xóa kết quả tốt trước khi predict: chuẩn bị toàn bộ điểm trước, khóa run và
  thay kết quả trong transaction. Prediction/insert failure không mất kết quả cũ.

Không thay schema, reset DB, huấn luyện trên production hay sửa failure AI demo.

## Thực nghiệm mới và tái lập

Hai lệnh CLI chạy với output mới, không ghi đè gói 24/09:

```powershell
python scripts/forecast_reproducible_experiment.py --output output/forecast_recursive_20261005
python scripts/forecast_reproducible_experiment.py --dataset output/forecast_recursive_20261005/dataset.csv --output output/forecast_recursive_replay_20261005
```

Nguồn synthetic_formula_v1/seed 20260924, 180 ngày; split train/calibration/test
và hyperparams giữ nguyên. Single origin 26/05/2026, 14 ngày test tiếp theo;
model train-only cũ, không refit hoặc chọn origin đẹp. Cả lag7 và MA7 append
prediction của chính mình, không được dùng actual trong horizon.

| Phương pháp | MAE VND | RMSE VND | MAPE % | R² |
|---|---:|---:|---:|---:|
| XGBoost recursive | 156688.50 | 194878.50 | 8.61 | -0.0760 |
| Lag7 recursive | 153742.36 | 185758.88 | 8.81 | 0.0223 |
| MA7 recursive | 156841.47 | 188116.18 | 8.91 | -0.0027 |

XGBoost kém lag7 về MAE/RMSE; R² âm. Không chứng minh hiệu quả kinh doanh thật
hoặc tổng quát hóa từ một origin tổng hợp. Chưa đánh giá interval calibration
recursive. One-step cũ vẫn riêng: XGBoost MAE165179.49, lag7 MAE153289.00;
coverage29/34 không được dùng làm coverage14ngày.

Gói có recursive_predictions.csv, results/config/manifest SHA256, dataset và
model JSON. Replay trả cùng metrics; test đối chiếu byte CSV và hash mọi file.
Regression thay future actual +10 triệu mà recursive predictions không đổi.

## Kiểm thử

`manage.py test tests.test_forecast_recursive_integrity tests.test_forecasting_prediction tests.test_forecasting_training tests.test_forecasting_queue --settings=config.settings_evidence_test --noinput -v 1`:
**25 tests, 85.897s, OK**; database test riêng được hủy sau chạy.

`manage.py test tests.test_forecast_experiment_bundle --settings=config.settings_evidence_test --noinput -v 1`:
**4 tests, 10.044s, OK** (không cộng hai nhóm thành full-suite).

Full staged release tree `0fb3a0ec4d6f48eb48a741495d020759c0839c87`:
**1197 tests, 323.998s, OK**, không failure/error/skip. Log
`output/policy_release_pi3guvup/tests.log`; DB test UUID độc lập, fast hasher chỉ
trong process test, không đổi hasher production. `check`: 0 issues; migration
drift: No changes detected; known-pattern secret scan: 802 files/0 findings,
không chứng nhận rotation hay mọi loại secret. Giữ nguyên assertions và failure
lịch sử. Full release không gồm các thay đổi unrelated/untracked của agent khác.

CI run 37252582257 (9f54cfa) giữ nguyên trạng thái failure: 77 tests OK nhưng
teardown DROP test_platform_ci bị ObjectInUse do một session còn mở. Đọc raw
job log 111583073636 xác nhận lỗi, không phải SMTP/test assertion failure.
ConcurrentOutboxTests dùng close_old_connections trong finally; nó giữ healthy
persistent connection. Sửa test worker finally dùng connections.close_all và
assert connection đã None; giữ race/once-only assertions, không keepdb/skip.
Đang kiểm chứng lại cùng nhóm và CI commit tiếp nối.
Kiểm thử riêng ConcurrentOutboxTests với CONN_MAX_AGE=600 trong process test
độc lập: 1 test/1.959s OK, teardown hủy đúng test database UUID thành công.
Không terminate session hoặc reset DB nghiệp vụ để làm xanh runner.

CI/deploy đang chờ kiểm chứng commit tiếp nối. Không cần browser cho kiểm chứng số
liệu backend này và không tạo giao dịch production.
