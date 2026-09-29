# Đợt 21 — Forecast provenance và gap policy

## Phạm vi

- Giữ nguyên target, model, route và public response schema.
- Dataset selector ghi rõ số quan sát gốc, số ngày bị thiếu và chính sách lấp
  ngày thiếu bằng 0 trong `DataFrame.attrs`.
- Mỗi `ForecastRun` thành công lưu `job_parameters.provenance` gồm workspace,
  target/dimension, model config/version, horizon, feature/training config hiệu
  dụng, khoảng dữ liệu, row counts, chronological split, fingerprint SHA-256 và
  phiên bản Python/Django/pandas/NumPy/XGBoost.
- Không lưu raw business rows vào provenance. `code_revision` lấy từ biến môi
  trường được cấu hình; nếu không có thì ghi `unknown`, không tự bịa commit.

## Kiểm chứng

```text
python manage.py test tests.test_forecasting_dataset tests.test_forecasting_training --settings=config.settings_evidence_test --keepdb --noinput -v 1
15/15 passed, 4.715s
python manage.py check
0 issues
python manage.py makemigrations --check --dry-run
No changes detected
```

## Giới hạn

- Fingerprint chứng minh input của run đã được ghi nhận, không chứng minh dữ
  liệu là production hay chất lượng dự báo tốt hơn baseline.
- Chưa có data catalog/versioned raw extract, external model registry, semantic
  forecast review hay production worker evidence.
- Mục 22/23/83/84 được củng cố ở local nhưng chưa đóng toàn bộ; các mục đánh giá
  chất lượng XGBoost, recursive horizon và deploy vẫn giữ nguyên giới hạn.
