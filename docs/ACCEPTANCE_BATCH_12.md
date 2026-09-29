# Đợt 12 — Lifecycle, vai trò và ledger đánh giá RAG

Ngày đối chiếu: 15/09/2026.

## Mục tiêu

Đóng các mục checklist đã có bằng chứng chạy lại, đồng thời làm cho benchmark
RAG lưu được thời điểm, thời lượng và mã lỗi an toàn của từng ca. Không coi lỗi
provider là ca đạt và không thay đổi dữ liệu nghiệp vụ/production.

## Thay đổi

- `apps/knowledge/evaluation.py` hỗ trợ `capture_errors=True` cho lần xuất bằng
  chứng. Mỗi ca có `status`, `evaluated_at`, `duration_ms` và `error_code` đã
  chuẩn hóa; mặc định vẫn fail-fast để không che giấu lỗi.
- `apps/knowledge/evaluation_scoring.py` tách `scored_cases` và `error_cases`;
  các ca lỗi không được đưa vào tỷ lệ proxy.
- `tests/test_role_acceptance_matrix.py` kiểm tra ranh giới quyền đại diện của
  ADMIN, MANAGER, EMPLOYEE và VIEWER trên cùng một workspace.
- `tests/test_rag_evaluation_runner.py` kiểm tra timeout được ghi thành
  `PROVIDER_TIMEOUT`, có thời lượng và không lộ exception thô.

## Bằng chứng

```powershell
python manage.py test tests.test_retail_orders tests.test_service_requests tests.test_service_tasks tests.test_rbac tests.test_phase11_security_hardening --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **31 test passed, 388.479 giây**. Bao phủ tạo/duyệt/hủy đơn, trạng
thái kết thúc, tạo/giao/chuyển trạng thái yêu cầu dịch vụ, chuyển trạng thái
không hợp lệ, workspace isolation và các vai trò trong hardening suite.

```powershell
python manage.py test tests.test_rag_evaluation_scoring tests.test_rag_evaluation_runner tests.test_role_acceptance_matrix --keepdb --noinput -v 1
```

Kết quả: **17 test passed, 21.737 giây**.

Kiểm tra bổ sung: `python manage.py check` không có lỗi; migration drift không
được tạo. Không chạy browser/production; không push/deploy.

## Checklist được đóng trong đợt này

- **38**: mỗi ca benchmark giữ câu trả lời/nguồn/tool và metadata thời điểm,
  thời lượng, mã lỗi; lỗi provider không được tính là pass.
- **69**: có ma trận acceptance đại diện cho đủ ADMIN/MANAGER/EMPLOYEE/VIEWER,
  kết hợp với các endpoint/module RBAC hiện có.
- **71**: nhóm test lifecycle xuyên suốt đơn hàng và dịch vụ có cả chuyển trạng
  thái hợp lệ và không hợp lệ.

Các giới hạn vẫn giữ nguyên: semantic correctness của RAG chưa đo; ma trận vai
trò là acceptance đại diện, không phải tải production; chưa có live provider,
browser hoặc production certification.
