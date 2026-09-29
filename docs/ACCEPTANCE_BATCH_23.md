# Đợt 23 — CSV import → mapping → dữ liệu chuẩn

## Đã thực hiện

- Chặn datasource khác workspace trước khi tạo ImportJob.
- Kiểm tra workspace của profile, job, datasource và raw records trước mapping.
- Không biến dòng parser đã đánh dấu lỗi thành dữ liệu canonical hợp lệ.
  Strict không ghi cả lô; partial chỉ ghi dòng hợp lệ.
- Sáu test mới dùng file CSV thật, không mock parser: trùng mã Customer và replay
  không nhân bản Customer; không sửa Customer cùng mã ở workspace khác; CSV thừa
  cột; thiếu tên canonical; datasource/profile/job context/raw workspace sai.
- Sửa fixture API thiếu permission và fixture xóa audit không còn hợp lệ với
  trigger append-only. Không bỏ assertion hay tắt trigger; thêm kiểm tra tăng 4 log.

## Kiểm chứng

```text
python manage.py test tests.test_import_mapping_acceptance tests.test_mapping_apply tests.test_mapping_canonical_consistency tests.test_integration_csv tests.test_mapping_security --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả cuối: **24/24 qua, 3.412 giây** (thời gian test, không gồm khởi tạo DB).
Lần đầu 20 test có 1 failure fixture ADMIN thiếu quyền; lần thứ hai 24 test có
1 error do fixture cố xóa audit. Cả hai nguyên nhân đã sửa như trên rồi chạy lại.
PostgreSQL/PostGIS test database riêng theo settings_evidence_test; không thay dữ
liệu nghiệp vụ. Email backend bộ nhớ, không có claim gửi email hoặc API AI thật.

- `python manage.py check`: no issues, 0 silenced.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `git diff --check` cho source/test tracked của đợt: exit 0.

## Phạm vi và phát hành

Đóng mục 77 theo acceptance CSV Customer + nhóm canonical/security hiện có.
Tiến độ 36 đóng / 29 một phần / 32 chưa xác nhận = 37,1% mục đóng.
Không chứng minh mọi loại nguồn, tải đồng thời hoặc exactly-once cho OrderItem,
Task, LaborEntry. Không có migration, không thay giao diện nên không dùng browser
làm bằng chứng backend. Chưa push/deploy: worktree chứa nhiều thay đổi tích lũy
ngoài nhóm này chưa được review như một release. Không đẩy gộp chúng tự động.
