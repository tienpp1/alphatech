# Đợt 34 — đóng mục theo tiêu chí, không theo số lần sửa

## Kết quả checklist

Đóng thêm 22, 23, 28: từ 44/97 lên 47/97 =48.45%, làm tròn 48.5%.
29 mục một phần, 21 chưa xác nhận. Mục 40 từ chưa xác nhận sang một phần,
không được cộng điểm đóng. Không đổi nội dung gốc hoặc mẫu số 97.

### 22 — dữ liệu train/validation/test

Report xuất period_start/end, số quan sát/hàng sau reindex, số kỳ thiếu,
zero-fill policy, đơn vị, ngày/số hàng train/test. Validation ghi rõ không có
partition riêng, không ngụ ý tuning hợp lệ. Run cũ thiếu metadata ghi thiếu.

### 23 — tham số, phiên bản, dữ liệu từng run

Xuất effective training config, feature config/columns, dimensions/horizon,
model version và runtime Python/Django/pandas/numpy/XGBoost. Dataset/model/source
có SHA-256; test đối chiếu model và bốn file nguồn thật. Git revision vẫn unknown
khi không được cấp, không bịa commit. Không đòi model registry production để đóng
tiêu chí ghi hồ sơ, nhưng chưa chứng nhận backup extract/tái lập độc lập (83–85).

### 28 — chốt bài toán chính

FORECAST_EXPERIMENT_PROTOCOL.md chọn daily RETAIL_REVENUE, gắn bán hàng chính;
không chọn bài toán chỉ vì thắng baseline. Giữ kết quả kém và tách one-step với
recursive horizon 14 ngày. Đóng quyết định phạm vi, không đóng chất lượng dự báo.

### 40 — làm tiếp nhưng chưa đóng

ADVERSARIAL_CASES thêm paraphrase, thiếu dữ liệu, hai nguồn mâu thuẫn 12/24 tháng,
thiếu ai.chat và workspace trái phép. Mỗi ca có fixture, actor, expected behavior;
không gán semantic pass. Cần chạy các fixture cô lập và chấm câu trả lời thực,
đặc biệt conflict; không dùng test cấu trúc dataset làm bằng chứng model trả đúng.

## Lệnh và kết quả chính xác

```powershell
python manage.py test tests.test_forecasting_training tests.test_forecasting_dataset tests.test_academic_reporting tests.test_academic_report_command --settings=config.settings_evidence_test --noinput -v 1
```

- Lượt 1: 30 tests, 7.926s, FAILED (7 errors): Windows TemporaryDirectory bị
  PermissionError lúc ghi và cleanup. Không có assertion chất lượng bị sửa.
- Lượt 2 chuyển temp vào evidence workspace: 30 tests, 7.471s, cùng 7 errors.
  Xác định relocation không khắc phục sandbox/ACL; hoàn nguyên thay đổi fixture.
- Lượt 3, quyền thực thi mở rộng được duyệt: 30 tests, 8.433s, OK.
  Không coi 90 lượt thực thi là 90 test độc lập. Các DB test mới đều destroyed.

```powershell
python manage.py test tests.test_adversarial_case_contract tests.test_rag_security_rbac --settings=config.settings_evidence_test --noinput -v 1
```

8 tests, 26.867s, OK; DB test destroyed. Tổng hai lượt cuối 38 test, không full suite.
check: no issues. makemigrations --check --dry-run: No changes detected.
Relevant changed-file diff check: exit 0.

Artifact từ lượt cuối:
`output/evidence_tests/cf8657809b53476a/forecast_run_provenance.md`.
Synthetic 60 ngày, 37 train/9 test sau lag; không validation riêng. Không phải
dữ liệu kinh doanh thật hoặc chứng nhận khả năng khái quát. Không gửi dữ liệu/API AI.

## Phạm vi và phần còn lại

Không sửa code model ngoài thêm source fingerprint; giữ thay đổi đã có trong
training/evaluation của các đợt/agent khác. Không sửa UI nên không dùng skill thiết
kế hoặc browser chỉ để tạo hình thức kiểm chứng. Không Word/push/deploy.

Các thư mục TemporaryDirectory lỗi quyền ở hai lượt đầu chưa dọn; không mở rộng
xóa dữ liệu để ép test qua. Không đụng database nghiệp vụ.
Tiếp theo: thực thi/chấm adversarial cases (40/39), dữ liệu thật/extract (83),
đối chứng nhiều ngày và phân tích lỗi (17/26). Chưa có kết luận production.
