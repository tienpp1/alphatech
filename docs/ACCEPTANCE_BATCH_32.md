# Đợt 32 — SLA thiếu dữ liệu: engine, API, giao diện và kiểm thử

Ngày 17/09/2026. Không sửa dữ liệu nghiệp vụ, migration, quyền role hay deploy.

## Công việc hoàn thành

1. Deadline thiếu không còn là ON_TIME: trạng thái UNKNOWN, thời gian còn lại null.
2. Nếu một hạn đã vi phạm, tổng thể vẫn BREACHED dù hạn kia thiếu. Nếu chưa có
   vi phạm nhưng thiếu hạn, tổng thể UNKNOWN; trạng thái riêng từng hạn vẫn giữ.
3. Tổng hợp loại UNKNOWN khỏi mẫu số và trả null khi mẫu số bằng 0. Bổ sung
   unknown_sla_count/evaluated_sla_count ở overview, unknown_count/evaluated_count
   ở SLA API. compliance_rate nay nullable; consumer không được ép null thành 100.
4. Dashboard giải thích tỷ lệ tại thời điểm xem; biểu đồ có nhóm chưa đủ dữ liệu,
   chú giải bằng chữ và trạng thái rỗng. Danh sách ticket không tô thiếu dữ liệu
   thành vi phạm hay đúng hạn. Detail đã có nhãn thiếu dữ liệu từ đợt 30.
5. Regression cho thiếu một/hai hạn, vi phạm trên hạn còn lại, mẫu rỗng, mẫu hỗn
   hợp 50%, JSON null/counts, render UI. Giữ test 201 ticket và RBAC đã có.

## Xác minh

```powershell
python manage.py test tests.test_internal_authorization_regressions tests.test_service_workload tests.test_service_sla --settings=config.settings_evidence_test --noinput -v 1
# 27 tests in 68.526s, OK; new test database destroyed
python manage.py check
# System check identified no issues
python manage.py makemigrations --check --dry-run
# No changes detected
```

ui-ux-pro-max: tìm kiếm lần đầu không đúng ngữ cảnh; lần hai Empty States phù hợp,
áp dụng thông báo rỗng và nhãn bằng chữ, không chỉ màu. Không thay thiết kế tổng thể.
Browser mở HTML thực do Django render bằng fixture giả tại
output/evidence_tests/4ec1a5a07d2b4784/service_ui/sla_dashboard.html:
KPI chưa đủ dữ liệu, 0 phiếu có kết luận/1 phiếu thiếu và nhãn ticket đúng.
Snapshot không phải phiên auth/POST thật. Screenshot hẹp vẫn thấy nav overflow;
không chứng nhận responsive hoặc mọi chart pixel. Preview chỉ bind loopback.

Global git diff --check có whitespace trong static/css/public_pages.css đang
được sửa ngoài phạm vi; không sửa đè. Các file của đợt này được check riêng.

## Giới hạn và việc tiếp

- Chưa có final-compliance metric theo kỳ/đóng ticket; giữ nguyên cách xử lý
  CANCELLED/CLOSED của engine. Không gọi tỷ lệ hiện tại là SLA chứng nhận.
- Chưa audit hết quyền đọc các API Service khác.
- Chưa sửa navigation responsive; không chạm CSS public đang có thay đổi riêng.
- Còn quyết định tác vụ kỹ thuật viên trong đề cương; không tự nâng quyền.
- Không full suite/push/deploy/production acceptance. Checklist 44/97 =45.4%.
