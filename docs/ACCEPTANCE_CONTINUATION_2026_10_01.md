# Tiếp tục nghiệm thu — 01/10/2026

Không đổi ID, tiêu chí hoặc số mục đã đóng trong checklist 97 mục.

## Quyết định của chủ dự án

- CI: nghiệm thu phần local; không yêu cầu thêm token/log GitHub. Không chuyển
  kết quả remote failure thành PASS. Workflow dùng Django test, không phải Pytest.
- Giữ Render Free, không vận hành async production. Worker chỉ kiểm thử local.
  Production mặc định từ chối enqueue async trước khi tạo config/run, trừ khi
  operator bật `FORECAST_ASYNC_ENABLED=True` với worker thật.
- Restore hoãn vô thời hạn. Không chạy restore hoặc tạo sandbox.
- Phiếu RAG cũ được chủ dự án chấm: 3/4 câu đủ tiêu chí, câu mâu thuẫn thiếu ý.
  Đây là mẫu nhỏ offline, không chứng minh chất lượng RAG tổng quát.

## Sửa mã nguồn

- Health che lỗi adapter, trả degraded/503; khôi phục nhãn local verified đúng
  hợp đồng test. Không đổi schema phản hồi.
- Worker join có timeout; lỗi start/process được sanitize và trả lease cho
  retry hiện có. Child không reap được làm supervisor dừng thay vì treo.
- RAG cảnh báo thứ tự tìm kiếm không xác định nguồn có hiệu lực; không bỏ nội
  dung khác nhau cùng tiêu đề/mục. Cảnh báo số liệu khác nhau chỉ khi câu cùng
  cách diễn đạt có đúng một số. Không tuyên bố nhận diện mọi mâu thuẫn ngữ nghĩa,
  phủ định, hiệu lực tài liệu hoặc chuyển đổi đơn vị.
- CI lưu log hai nhóm test và SHA trong artifact; pipefail giữ exit code lỗi.
  Không skip test, thêm suppression hoặc hạ coverage gate.

## Bằng chứng external read-only

- GitHub run 36538969165, SHA `27e7be7dcf497c53b64d29d66e799ae02694c737`:
  completed/failure. Hai bước lỗi: Focused regressions with coverage và HTTPS
  email and deployment regressions. Check/migrations/audit/Bandit/coverage gate
  báo success. Tải log job HTTP 403; không suy đoán traceback từ test local.
- Render deploy `dep-datmsnnlot8c7386se4g`: live, cùng SHA, Free,
  `gunicorn config.wsgi:application`. Chưa chứa sửa đổi uncommitted đợt này.
- Render env: DEBUG=False, HTTPS redirect và secure cookies=True, callback và
  PUBLIC_BASE_URL đúng domain. HSTS/CSP enforcement chưa đặt. Chỉ kiểm presence
  credential, không lưu giá trị.
- HTTP production timeout; mở/quan sát trình duyệt cũng timeout. Chưa chứng
  nhận header/CSP hoặc UI production trong đợt này.

## Test hoàn tất

Lệnh Django dùng `--settings=config.settings_evidence_test --noinput`; database
test mới ngẫu nhiên trên loopback, không reset database nghiệp vụ.

- Worker/queue/training/Command Center/adversarial RAG: 26/26 OK, 39.639s
  (trước async gate).
- Source authority/grounding/human review/generation/embedding: 27/27 OK,
  33.387s (trước cảnh báo số liệu).
- Source authority/adversarial/numeric facts/scoring: 26/26 OK, 0.918s.
  Output `output/evidence_tests/b13f16c07a1a4cd9/adversarial_rag_observations.json`
  cảnh báo mâu thuẫn 12/24, dẫn hai nguồn và yêu cầu xác nhận.
- Health/worker process/queue/training/forecasting API: 29/29 OK, 41.228s.
- Nhóm CI HTTPS/email/deployment, 7 modules: 77/77 OK, 391.495s.
- Nhóm CI focused, 14 modules: 146 tests, 870.066s; lần đầu 2 failures/1
  error, đều trong health (nhãn sai và RuntimeError không redacted). 143 case
  còn lại pass. Sau repair, toàn bộ 5 health tests nằm trong nhóm 29/29 pass
  phía trên. Chưa chạy lại cả nhóm 146 sau repair; không ghi lần đầu là PASS.
- Lần đầu test mới sai signature/vị trí async guard; đã sửa nguyên nhân và
  chạy lại. Không xóa hoặc hạ assertions.
- Source secret scan: 777 files, 0 findings theo mẫu. Git history: 32 reachable
  commits, 0 findings theo mẫu; không chứng nhận rotation provider.
- Bandit: `output/bandit_20261001_final.json`.
- Check 0 issues, drift No changes detected trước final behavioral patches;
  không thêm model hoặc migration.

Không cộng nhóm test chồng lặp thành số case duy nhất; không gọi đây là full
suite pass, inbox delivery hoặc production certification.

## Còn cần

- Người thật chấm phản hồi RAG mới và tập số liệu/hybrid độc lập; không sao chép
  điểm cũ sang output mới.
- GPS sai số lớn/position unavailable chưa được xác nhận.
- Kiểm chứng release mới sau push/deploy; chưa bật CSP khi chưa review UI.
- CI remote failure giữ nguyên; chủ dự án chấp nhận giới hạn local.
- Worker async production không sử dụng; restore không thực hiện theo yêu cầu.
  Không thể chứng nhận đủ 97/97 kiểm thử đã thực hiện.
