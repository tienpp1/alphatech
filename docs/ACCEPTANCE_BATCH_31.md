# Đợt 31 — quyền API thống kê và tính đầy đủ của tổng hợp

Ngày 17/09/2026. Giữ toàn bộ thay đổi sẵn có; không thay quyền role, không push/deploy.

## Kết quả

1. Ba API analytics overview/workload/SLA trước đây chỉ kiểm tra membership.
   Nay dùng require_permission("service.view_analytics") trước khi gọi selector.
   Từ chối nhân viên thiếu quyền, khách public và người có quyền ở workspace khác.
2. Bỏ hai giới hạn [:200] ở tổng hợp SLA và thời gian xử lý. Dùng iterator theo
   chunk 500, chỉ lấy trường cần thiết cho tính thời gian. Không đổi route/schema.
3. Sửa hướng dẫn trong evidence settings để không khuyến nghị --keepdb vốn giữ
   lại database tên ngẫu nhiên sau mỗi lượt chạy. Không xóa database cũ.

## Bằng chứng

```powershell
python manage.py test tests.test_internal_authorization_regressions tests.test_service_workload tests.test_service_sla --settings=config.settings_evidence_test --noinput -v 1
```

23 tests, 54.049s, OK. Test database riêng đã bị Django thu hồi sau lượt chạy.
Ba test mới kiểm tra: denied request không gọi selector; admin/manager fixture
chỉ xem dữ liệu workspace được chọn; tổng hợp 201 ticket và thời gian trung bình
đúng 2 giờ (có một ticket 202 giờ, 200 ticket một giờ).

`python manage.py check`: no issues.
`python manage.py makemigrations --check --dry-run`: No changes detected.
`git diff --check`: exit 0; chỉ có cảnh báo chuẩn hóa LF/CRLF của working copy.

Không có thay đổi giao diện nên không mở browser hoặc áp dụng skill thiết kế
không liên quan. Bằng chứng là Django API/selector tests, không phải production.

## Chưa hoàn tất

- Engine vẫn coi thiếu deadline là ON_TIME; mẫu rỗng trả 100%. Cần hợp đồng trạng
  thái không đủ dữ liệu và cập nhật đồng bộ dashboard, danh sách, API, kiểm thử.
- API service đọc khác chưa được chứng nhận có RBAC đầy đủ trong đợt này.
- Không tự nâng quyền kỹ thuật viên; quyết định lifecycle vẫn chưa có xác nhận.
- Không cập nhật bản Word, không full suite, không deploy, không production gate.

44/97 =45.4% vẫn là số mục đóng có bằng chứng; ba regression mới không được quy
đổi thành ba mục checklist hoàn thành.
