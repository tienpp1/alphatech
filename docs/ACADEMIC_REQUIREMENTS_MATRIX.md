# Yêu cầu → mã nguồn → kiểm thử → bằng chứng

Đối chiếu hiện hành 09/10: biên bản FINAL_97_CLOSURE_2026_10_09.md chốt công
việc theo phạm vi đã điều chỉnh. Audit 35 UC với log full 1207 mới không thiếu
source/test hoặc observed test file. Các batch dưới đây vẫn là hồ sơ có ngày
riêng, không cộng test trùng hoặc coi Human Evaluation là quan sát của agent.

Đối chiếu ngày 18/09/2026, theo ACADEMIC_ACCEPTANCE_SCOPE.md. Đường dẫn dưới đây
tính từ root repository. Có test không có nghĩa test đã chạy ở commit production.
Batch là hồ sơ kết quả lịch sử có phạm vi, không cộng tổng test giữa các batch.

Cập nhật đối chiếu 04/10: các thiếu sót lịch sử trong bảng dưới đây phải đọc cùng
`RELEASE_ACCEPTANCE_2026_10_04.md`. UAT retail đúng người/ack/reload và restore
độc lập đã có bằng chứng; RAG conflict, GPS, email và xác minh khác thiết bị có
Human Evaluation của chủ dự án. Không biến các xác nhận theo mẫu thành độ chính
xác toàn hệ thống. Mỗi release có test/CI riêng; giữ phạm vi local storage và
worker production tắt theo lựa chọn đồ án.

| Mã | Mã nguồn | Kiểm thử đại diện | Bằng chứng / thiếu |
|---|---|---|---|
| AUTH | `apps/public_web/registration.py` | `tests/test_registration_codes.py` | Replay/trùng/xác minh có test; inbox và cross-device theo Human Evaluation, HTTPS theo release; Google chỉ public |
| TENANCY | `apps/workspaces/middleware.py` | `tests/test_internal_authorization_regressions.py` | Role/membership theo seed và entry policy; kỹ thuật viên là hồ sơ nghiệp vụ, không thêm role mới |
| RETAIL | `apps/public_web/fulfillment.py`, `apps/retail/services.py` | `tests/test_checkout_concurrency.py` | Batch 36: PostgreSQL race/rollback; strict production chưa xác nhận |
| SERVICE | `apps/service_ops/services.py`, `apps/service_ops/sla_engine.py` | `tests/test_service_requests.py`, `tests/test_service_sla.py` | Batch 29–33: lifecycle/SLA/read RBAC; field-level cost policy còn mở |
| GIS | `apps/gis/services.py`, `apps/public_web/geocoding.py` | `tests/test_gis_reference_distances.py`, `tests/test_public_branch_finder.py` | Reference tests và live Nominatim có hồ sơ; GPS deny/unavailable/low accuracy theo xác nhận người dùng |
| DATA | `apps/integration/services.py`, `apps/mapping/services.py` | `tests/test_import_mapping_acceptance.py` | Batch 23: CSV Customer end-to-end; không suy rộng mọi entity |
| RAG | `apps/knowledge/services.py`, `apps/knowledge/retrieval.py` | `tests/test_adversarial_rag_execution.py`, `tests/test_embedding_space_isolation.py` | Conflict đã repair và chấm lại; 5 IND được người dùng chấm PASS, phạm vi offline và không holdout mù |
| FORECAST | `apps/forecasting/training.py`, `apps/forecasting/academic_reporting.py` | `tests/test_forecasting_training.py`, `tests/test_academic_reporting.py` | Batch 34: run provenance/protocol; thực nghiệm sâu và recursive calibration chưa đủ |
| APPROVAL | `apps/approvals/executor.py`, `apps/approvals/registry.py` | `tests/test_approval_concurrency_evidence.py` | Batch 05/09: representative concurrency/action/audit; không chứng nhận mọi handler |
| NOTIFY | `apps/notifications/models.py`, `apps/public_web/email_service.py` | `tests/test_customer_approval_notices.py`, `tests/test_service_email_commit.py` | Inbox bốn event theo xác nhận người dùng; UAT retail owner/nonowner/ack/reload trực tiếp và đơn TEST đã hủy |
| TEAM_CHAT | `apps/notifications/models.py`, `apps/notifications/chat_service.py` | `tests/test_bulletin_and_team_chat.py` | Hoàn thành: Tin nhắn cô lập theo workspace, polling gia tăng since_id, phân quyền nhân viên nội bộ, chặn tài khoản khách hàng vãng lai |
| BULLETIN | `apps/notifications/models.py`, `apps/notifications/bulletin_service.py`, `apps/notifications/bulletin_edit_views.py` | `tests/test_bulletin_and_team_chat.py`, `tests/test_bulletin_update.py` | UAT 05/10: MANAGER đăng, EMPLOYEE đọc/không có nút sửa, edit GET 403; workspace khác không hiện TEST. Hai role kiểm lần lượt |

## Không suy diễn bằng chứng

- Nhận xét từ agent khác trong file Downloads là đầu vào rà soát, không phải
  log kiểm chứng độc lập. Bản file đang có ngày 17/09 là báo cáo UI, không còn là
  cùng nội dung chốt nghiệp vụ ngày 15/09 dù trùng tên file.
- Ma trận nhóm này được bổ sung bằng 35 ca sử dụng đối chiếu bản Word được duyệt
  tại ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md và audit thực thi v3.
  Mục 81 đóng phần hồ sơ truy vết, không biến test đã chạy thành visual/live QA.
- Chat realtime/bản tin không có số mục riêng trong danh sách 97 gốc. Theo dõi
  dưới phạm vi mục 2/81/87, không lặng lẽ đổi mẫu số hoặc bỏ yêu cầu.
