# Đợt 33 — quyền đọc API dịch vụ và đối chiếu tiến độ

## Đã thực hiện

- Rà source views, routes, serializer, seed quyền và test hiện hành.
- Thêm kiểm tra trước handler cho GET/HEAD của 14 endpoint qua require_permission
  hiện có, không tạo role hoặc hệ quyền song song.
- Catalog: view_service; employees: view_employee; SLA: view_sla; tickets:
  view_request; tasks và task-labor: view_task; schedules: view_schedule;
  ticket-cost và global labor: view_analytics. Analytics đã bảo vệ ở đợt 31.
- POST/PATCH/DELETE giữ kiểm tra cũ; không vô tình yêu cầu thêm view cho mutation.
- Ma trận 14 endpoint kiểm tra thiếu quyền GET/HEAD bị 403, đúng quyền đọc 200,
  workspace khác bị 403. Test người chỉ xem không tạo được dịch vụ.
- Mục 73 được sửa mô tả: strict home-delivery allocation và reservation đã được
  viết/test trong đợt 19–20; vẫn thiếu concurrency/triển khai thật, giữ Một phần.

## Kiểm chứng

```powershell
python manage.py test tests.test_internal_authorization_regressions tests.test_service_isolation tests.test_service_rbac tests.test_service_catalog tests.test_service_employees tests.test_service_requests tests.test_service_tasks tests.test_service_labor --settings=config.settings_evidence_test --noinput -v 1
```

45 tests, 144.003s, OK. Database riêng của lượt chạy được Django thu hồi.
`python manage.py check`: no issues.
`python manage.py makemigrations --check --dry-run`: No changes detected.
Changed-file `git diff --check`: exit 0.
Không sửa/skip assertions cũ để qua test. Không chạy full suite.

## Giới hạn cần rõ

Đây là RBAC theo endpoint, không phải theo từng trường. Ticket/task hiện trả
employee và labor/cost lồng nhau; view_request/view_task vẫn đọc được phần đó.
Muốn hạn chế chi phí theo role cần chốt policy và cập nhật cả serializer/UI/test,
không được coi chặn endpoint báo cáo riêng là đã che mọi chi phí.

Không thay UI nên không dùng skill thiết kế/browser cho một lượt backend.
Không push/deploy hoặc sửa database nghiệp vụ. Tiến độ 44/97 (45.4%).
