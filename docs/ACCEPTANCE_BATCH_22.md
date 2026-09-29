# Đợt 22 — Hồ sơ mô hình và bảo vệ metadata khỏi worker cũ

## Kết quả

- Feature config lưu cả mặc định được áp dụng. Training config lưu các giá trị
  thực sự truyền vào XGBoost, kể cả random_state, objective và eval_metric.
- Hồ sơ lưu tên cột đặc trưng, đơn vị target, ngày bắt đầu/kết thúc train/test,
  và ghi rõ không có partition validation riêng. Holdout vẫn là one-step.
- SHA-256 của file model được ghi sau khi save_model thành công để đối chiếu
  artifact với run. Fingerprint dữ liệu vẫn phụ thuộc biểu diễn pandas đã ghi phiên bản.
- Metadata được công bố cùng kết quả dưới kiểm tra lease cuối. Worker hết lease
  giữa quá trình đọc dữ liệu và công bố kết quả không ghi đè job_parameters.
- Giữ các metric kém, không đổi kết luận chất lượng mô hình.

## Kiểm thử

Lệnh:

```text
python manage.py test tests.test_forecasting_training tests.test_forecasting_dataset tests.test_forecasting_queue tests.test_academic_reporting --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

28/28 đạt, 23.674 giây. Có huấn luyện XGBoost thật trên fixture, đối chiếu hash
file model, ngày split và ca hết lease giữa lần chạy. Đây không phải load test
hay bằng chứng worker trên Render. Không gửi email/API AI trong nhóm test này.

Browser đã thử http://127.0.0.1:8011/noibo/forecasting/ và nhận
ERR_CONNECTION_REFUSED; không có server lắng nghe trên 8000/8001/8011 lúc kiểm tra.
Chưa xác nhận giao diện qua browser. Chưa push/deploy.

## Phần còn thiếu

Run lịch sử không tự được bổ sung hồ sơ. Data extract có phiên bản, dữ liệu thực
và chất lượng recursive forecast còn cần nghiệm thu riêng. Code revision môi
trường không chứng minh dirty worktree chính xác. Async failure trước công bố
không lưu provenance chưa được kiểm tra lease. Các giới hạn này giữ mục 22/23
ở trạng thái một phần; không đổi mẫu số hoặc tăng số mục đóng.
