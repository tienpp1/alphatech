# Đợt 18 — Đối chiếu phạm vi và baseline MA-7

## Phạm vi

- Đọc và đối chiếu file `1. Chốt phạm vi nghiệp vụ (Phân tíc.txt` với source,
  tests và commit hiện tại.
- Ghi rõ các giả định chưa đủ bằng chứng trong
  `docs/SCOPE_ALIGNMENT_2026-09-15.md`.
- Bổ sung baseline moving-average 7 ngày cho forecasting, độc lập với baseline
  lag-7 hiện có; mỗi dự đoán chỉ dùng dữ liệu trước thời điểm dự báo.

## Kết quả

- Không đổi route, response schema, migration, secret, production DB hoặc các
  failure AI demonstration đã biết.
- `ForecastRun.baseline_metrics` vẫn giữ các khóa `naive_*` và thêm
  `moving_average_7_*`; không gắn nhãn XGBoost vượt trội.
- Home-delivery allocation vẫn để partial: chưa có branch fulfillment mặc định
  và tọa độ giao hàng đã xác nhận để chọn chi nhánh gần nhất một cách an toàn.
- CSV forecasting trong file phạm vi không có trong repository; nguồn hiện tại
  là DB/fixtures và được ghi rõ là giới hạn.
- Commit production ghi trong file đính kèm không trùng với HEAD hiện tại nên
  không được coi là bằng chứng deploy độc lập.

## Validation

```text
python manage.py test tests.test_forecasting_training tests.test_forecasting_dataset \
  --settings=config.settings_evidence_test --keepdb --noinput -v 1
15 tests passed in 4.256s

python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected

git diff --check
No whitespace errors (only Windows LF/CRLF conversion warnings).
```

Checklist giữ nguyên **35 đóng / 29 một phần / 33 chưa xác nhận**; đợt này
không tự tăng tỷ lệ chỉ vì thêm metric baseline.
