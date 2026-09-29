# Đợt 13 — Bằng chứng forecasting theo chiều dữ liệu và baseline

Ngày đối chiếu: 15/09/2026.

## Phạm vi

Bổ sung regression cho product-demand theo `product_id`, `category_id` và
`branch_id`, kiểm tra workspace isolation và từ chối dimension không hỗ trợ.
Đồng thời kiểm tra baseline dùng đúng số điểm của holdout và MAPE không chia cho
ngày có actual bằng 0.

## Validation

```powershell
python manage.py test tests.test_forecasting_dataset tests.test_forecasting_training --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **12 test passed, 6.300 giây**.

Các test này chỉ chứng minh quy tắc tạo dataset, lọc workspace/dimension,
chronological split, độ dài baseline và công thức MAPE. Chúng không chứng minh
XGBoost tốt hơn baseline, không chứng minh dự báo recursive nhiều ngày và không
thay thế đánh giá dữ liệu thật.

## Checklist được đóng

- **24**: baseline sinh đúng số điểm của test holdout, dùng dữ liệu quá khứ và
  cùng điều kiện split với mô hình.
- **25**: MAPE loại ngày actual bằng 0 để tránh mẫu số vô nghĩa; giới hạn này
  được ghi rõ, không diễn giải là độ chính xác tuyệt đối.

Mục 22/23/26/28 vẫn mở vì còn thiếu validation split, provenance đầy đủ, độ bao
phủ khoảng dự báo và một benchmark forecast độc lập đủ sâu.
