# Bài toán dự báo chính và hợp đồng thực nghiệm

## Quyết định phạm vi — mục 28

Bài toán chính: RETAIL_REVENUE, tổng doanh thu đơn COMPLETED theo ngày, đơn vị
VND, trong một workspace Retail xác định. Không gộp workspace, branch, SKU hay
category giữa các run. Cấu hình chính không chọn chiều lọc. Mục tiêu ứng dụng là
hỗ trợ quan sát xu hướng và lập kế hoạch, không tự động đặt hàng hoặc cam kết lợi nhuận.

Chọn doanh thu vì gắn với nghiệp vụ bán hàng chính và cần giải thích cả kết quả
kém baseline đã phát hiện. Không chọn target theo MAE đẹp nhất. ORDER_VOLUME,
SERVICE_TICKET_VOLUME và product-demand là đối chứng/mở rộng, không thay thế
kết quả doanh thu khi doanh thu thất bại. Quyết định này không xóa tính năng nào.

## Hồ sơ bắt buộc cho từng run — mục 22 và 23

- Nguồn: giao dịch trong DB do get_historical_timeseries chọn; seed/test phải
  ghi là tổng hợp. Không gọi CSV chưa tồn tại là dữ liệu đã dùng.
- Ghi khoảng ngày, số hàng quan sát và sau reindex, số kỳ thiếu, zero-fill policy,
  đơn vị và fingerprint. Zero-fill không chứng minh ngày thiếu thực sự không bán.
- Train/test theo thời gian; ghi ngày đầu/cuối và số hàng sau bỏ lag thiếu.
  Không có validation riêng thì phải ghi no_separate_validation_partition.
  Không dùng test để lựa tham số rồi gọi cùng test là độc lập.
- Lưu effective training_config, feature_config/columns, dimensions, horizon,
  model version, runtime Python/Django/pandas/numpy/XGBoost; hash model và source.
  code_revision unknown phải giữ unknown; source hash không thay thế git commit.
- Với run lịch sử thiếu hồ sơ: ghi Chưa ghi nhận. Không hồi điền bằng settings mới.
- Fingerprint nhận diện chuỗi đầu vào, không phải bản backup dữ liệu. Chạy lại
  cần giữ extract cùng phiên bản bên ngoài báo cáo, với quyền truy cập phù hợp.

## Thiết kế đánh giá sâu

1. Khóa nguồn dữ liệu và khoảng ngày trước khi chạy; ghi rõ synthetic/real.
2. So sánh XGBoost với lag-7 và trailing moving-average-7 trên cùng holdout,
   cùng lịch sử được phép biết. Báo MAE, RMSE, R², MAPE và mẫu số MAPE khác 0.
3. One-step observed-history và recursive horizon 14 ngày là hai phép đo riêng.
   Không dùng kết quả one-step để kết luận chất lượng dự báo 14 ngày.
4. Báo tất cả run đã chọn trước, kể cả FAILED/kém baseline; phân tích thiếu mẫu,
   mùa vụ, seed đơn giản, biến động bất thường như giả thuyết cần thử, không gọi
   là nguyên nhân đã chứng minh nếu chưa làm ablation/đối chứng.
5. Dải hiển thị không gọi là khoảng tin cậy hiệu chỉnh nếu chưa có calibration
   và đo coverage độc lập. Kết quả synthetic không suy ra hiệu quả kinh doanh.

## Xuất và nghiệm thu

Gói doanh thu tổng hợp có CSV, model, prediction/bounds và replay thực chạy mới:
`FORECAST_REPRODUCIBLE_BUNDLE_2026_09_24.md`. Không dùng gói này để hợp thức hóa
các con số lịch sử Batch 44 hoặc kết luận chất lượng dự báo production.

Lệnh đọc run cụ thể, không tự huấn luyện hoặc ghi lại kết quả:

```powershell
python manage.py evaluate_academic_metrics --workspace <ma-workspace> --run-id <id> --output output/forecast-evidence-new.md
```

File đích phải mới để không ghi đè bằng chứng cũ. Test nguồn hồ sơ:
tests.test_forecasting_training và tests.test_forecasting_dataset.
Test xuất hồ sơ: tests.test_academic_reporting và tests.test_academic_report_command.

Đóng mục 28 nghĩa là đã chốt bài toán và giao thức, KHÔNG nghĩa thực nghiệm sâu
đã hoàn tất. Chất lượng model, dữ liệu thật, tái lập độc lập, calibration và
production worker vẫn nghiệm thu ở các mục khác (17, 26, 83–85, 92).
