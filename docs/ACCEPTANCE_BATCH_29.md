# Đợt 29 — quyền thao tác dịch vụ và kịch bản demo

Ngày 16/09/2026. Không push/deploy, không sửa database nghiệp vụ hay role grants.

## Đã làm

1. `apps/service_ops/ui_views.py`: không nuốt Http404 trong mutation detail.
   Foreign employee/task ID trả 404 thay vì redirect; lỗi permission giữ 403.
2. Tách `labor_technicians` khỏi danh sách điều phối. Người chỉ được ghi giờ cho
   mình không còn được form gợi ý chọn nhân viên khác; quản lý vẫn có lựa chọn
   theo quyền hiện có. POST giả mạo vẫn kiểm tra phía server.
3. Template ghi giờ có label liên kết ID. Dùng skill ui-ux-pro-max, hướng dẫn
   Form Labels/Submit Feedback, không đổi animation hoặc thiết kế tổng thể.
4. Sửa URL demo service/GIS/assistant/import/audit theo routes thật; bỏ form tạo
   request không tồn tại và enum URGENT/SLA gán sẵn. Có test resolve URL tài liệu.
5. Thêm full demo seed smoke test kiểm tra retail/service/documents và tenancy;
   test này chưa thực thi được vì hết dung lượng ở bước tạo test database.

## Kết quả chính xác

```powershell
python manage.py test tests.test_internal_authorization_regressions tests.test_service_labor tests.test_role_acceptance_matrix --settings=config.settings_evidence_test --keepdb --noinput -v 1
# 23 tests, 71.402s, OK
python manage.py test tests.test_demo_document_routes tests.test_full_demo_seed --settings=config.settings_evidence_test --keepdb --noinput -v 1
# FAILED during database migration/setup: PostgreSQL DiskFull, No space left on device.
# No test result from this invocation; do not count as executed seed acceptance.
python manage.py test tests.test_demo_document_routes --settings=config.settings_evidence_test --keepdb --noinput -v 1
# No database needed. 2 tests, 0.080s, OK
python manage.py check
# No issues
python manage.py makemigrations --check --dry-run
# No changes detected
```

25 distinct tests passed in this batch, not a cumulative project total. Existing
tests were not weakened/skipped. Snapshot artifacts from real template render on
synthetic fixtures: `output/evidence_tests/266b07e070b942f2/service_ui/manager.html`
and `technician.html`; stylesheet copied from repository. These are static test
responses, not a live browser/session or production acceptance.

## Blockers / chưa xác nhận

- Browser tool initialization failed twice with “failed to write kernel assets:
  The system cannot find the path specified”, including after reset. No visual QA claim.
- PostgreSQL DiskFull stops database-writing verification. Windows drive check
  showed C: 2.50 GB free, D: 332.04 GB free; this alone does not identify PostgreSQL's
  storage volume. Do not delete database files directly. A read-only data_directory
  query with the default connection was denied; no privileges were changed.
- Evidence settings use a unique database per invocation; --keepdb retains it,
  so it does not reuse prior databases. Inventory/explicit cleanup approval is needed
  before removing old test databases. No database deletion has occurred.
- Need user decision: technicians only log own labor, or may transition assigned
  tasks? Keep current privileges until policy is confirmed.
- Full seed remains unverified, including forecasting substeps whose exceptions
  are currently caught by the seed command. Do not equate its final success text
  with all modules actually ready.

Progress remains 44/97 =45.4%. Items 70/87 strengthened, not closed.
