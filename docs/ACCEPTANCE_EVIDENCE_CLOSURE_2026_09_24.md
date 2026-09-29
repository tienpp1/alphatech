# Chốt nhóm bằng chứng — 24/09/2026

## Ba mục đủ điều kiện đóng

- **14:** Không cộng test chồng lặp. Bỏ các bảng tổng/phan bổ số test không có log; mỗi run và rerun được giữ riêng. Inventory file không phải pass hay coverage.
- **80:** Khoảng trống ứng dụng được diễn giải từ nhu cầu kịch bản đồ án, gắn source/test và giới hạn; không giả định RAG numeric checker chạy runtime hoặc tuyên bố tính mới thuật toán.
- **86:** Ghi đầy đủ failure/error/skipped/unrun từ log thật, không thay bằng tuyên bố trong tài liệu. Log và SHA256 được lưu tại TEST_EXECUTION_EVIDENCE.md.

Checklist thành **75/97 (77,3%)**: 70 mục kế thừa và 5 mục đối chiếu lại, 22 mở.
Không chứng nhận độc lập 75 mục và không thay đổi mẫu số/tiêu chí để tăng phần trăm.

## Kết quả và giới hạn cụ thể

Log full suite cũ: 1.067 tests, 2.032,520s, FAILED, 8 failures + 8 errors, 0 skipped.
16 incident entries ứng với 14 test ID duy nhất (có cleanup lặp). Trích xuất dòng
verbose được 1.066 ID, nên không coi đó là danh sách đầy đủ 1.067 ca. Không lấy
1.067 trừ 16 để công bố pass. Chưa full-suite rerun sau các bản sửa.

Lệnh kiểm chứng công cụ/tài liệu:

`python manage.py test tests.test_acceptance_log_summary tests.test_academic_test_manifest_audit --settings=config.settings_evidence_test --noinput -v 1`

**12 tests OK, 0.572s** (lần trước 2.350s cũng 12 tests, không cộng). Discovery của
manifest thấy 1.092 tests; đây không phải kết quả chạy 1.092 tests.

Parser kiểm tra run hoàn tất duy nhất, từ chối log bị cắt hoặc ghép nhiều run,
kiểm đủ incident, giữ số skip và không suy pass từ lỗi cleanup. Một lỗi parser
ban đầu do dấu cách trước `errors` đã được sửa bằng strip và test hồi quy riêng.

## Đồng bộ thêm nhưng chưa đóng toàn bộ mục rộng

- Sơ đồ RAG trong hồ sơ nghiệm thu đã tách runtime, retrieval/tools và evaluation.
- Slide bỏ recall 94,6%, anti-hallucination 100%, coverage 66,7% chưa xác minh và
  các ngưỡng SOP demo bị trình bày như chính sách đã duyệt. Giữ bố cục hiện có.
- Skill slides được dùng để giữ thông điệp bằng chứng/giới hạn nhất quán. Chưa
  visual QA browser cho slide; không gọi bản thảo là bản nộp đã hoàn thiện.
- Mục 7/11/13/26/82/89 vẫn mở vì còn phạm vi tài liệu, nguồn hoặc đối chiếu rộng hơn.
- Không sửa Word đã duyệt, không push/deploy, không reset hay sửa dữ liệu nghiệp vụ.

## Phần còn cần làm

Local: rà toàn bộ sơ đồ/ma trận, provenance dataset/model/run, chấm semantic RAG
độc lập và đồng bộ bản nộp. External: bằng chứng CI đúng SHA, Sentry, worker,
HTTPS/cookie/CSP và từng sự kiện email; restore tiếp tục hoãn theo user.
Chính sách thương mại cần văn bản được duyệt, không dùng bản tóm tắt source của AI.
