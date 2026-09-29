# Đợt đối chiếu tài liệu, phiếu RAG và release guard — 25/09/2026

## Tiến độ và phạm vi

Đóng thêm **7, 11, 13**: từ 81 lên **84/97 (86,6%) tạm đóng**; 70 mục kế thừa
và 14 đối chiếu lại. Đây không phải chứng nhận độc lập toàn bộ 84 mục.
Còn 13: **39, 46, 56, 57, 89, 90, 91, 92, 93, 94, 95, 96, 97**.

## Việc đã thực hiện

- Đọc nội dung bản Word được duyệt teacher_review_v2, không chỉnh sửa; SHA256
  `9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816`.
  Không có kiểm chứng render Word mới trong đợt này.
- Sửa khẳng định nghiệm thu/an toàn không có bằng chứng trong hồ sơ tổng hợp,
  thuyết minh 3–5, academic-defense-notes, ai-defense-guide, project-summary,
  hướng dẫn demo và runbook. Rà thêm thuyết minh 1–2 và slide; slide chỉ đổi số
  trạng thái, không thay animation/layout. Documents/Slides giúp giữ ranh giới
  bản đã duyệt và bản nháp, không viết lại đề cương.
- Thay bảng NEXT_CLOSURE_GATES lỗi thời bằng điều kiện còn thiếu; sửa mô tả
  ContactSubmission và custom RBAC cũ trong PROJECT_CONTEXT. Biên niên Batch 50
  được ghi rõ thu hồi, lịch sử failure và metric kém baseline vẫn được giữ.
- RAG: thêm adapter từ observations sang report/phiếu chấm, ID riêng cho
  paraphrase, giữ nguồn/expected, tách hai denial. Packet có 4 câu, **0 đã chấm**;
  fingerprint bắt thay đổi nguồn. Xem RAG_REVIEW_HANDOFF_2026_09_25.md.
- Secret: scanner nguồn tracked/unignored, báo đường dẫn/dòng/loại, không in
  giá trị; hỗ trợ UTF-16 BOM, fail khi source không đọc được/quá lớn. Thêm CI
  gate và artifact; ignore env phụ, output, tmp, model artifacts chưa tracked.
  Không xóa file hay bỏ theo dõi file đã tracked, không xác nhận rotation/history.
- Nghiên cứu: bỏ suy rộng XGBoost/LSTM từ LightGBM và M4, hạn chế claim
  multi-tenancy tối ưu và cấm CV tuyệt đối; nguồn/việc chưa xác minh ghi tại
  RESEARCH_SOURCE_CHECK_2026_09_25.md. Mục 89 chưa đóng.

## Kiểm thử

```powershell
python manage.py test tests.test_academic_current_claims tests.test_rag_review_packet tests.test_rag_human_review tests.test_release_secret_scan tests.test_academic_scope_contract tests.test_academic_test_manifest_audit tests.test_production_deployment_dossier --settings=config.settings_evidence_test --noinput -v 1
```

**33 tests OK, 9.969s**, không failure/error/skipped. Log:
`output/claims_batch_focused_20260925.log`. Inventory discovery 1121 là số test
được tìm thấy, KHÔNG phải 1121 test đã chạy. Lượt 27 trước đó lỗi quyền thư mục
tạm Windows; chạy cùng assertions với quyền tạo/dọn temp thì qua; không bỏ test.
Full 1095-test run trước đây không đại diện cho phiên bản sau các thay đổi này.

Không dùng settings_evidence_test cho check/makemigrations: module này chủ động
chặn lệnh ngoài test. Lần gọi sai đã bị từ chối trước thực thi; kiểm tra lại bằng
settings bình thường với telemetry vô hiệu hóa ở môi trường tiến trình.

Kết quả chạy lại: `python manage.py check` — 0 issues;
`python manage.py makemigrations --check --dry-run` — No changes detected.

Scanner cuối: 748 source files, 17 non-source entries excluded, không phát hiện
mẫu secret đã biết; `output/release_secret_scan_claims_final_20260925.json`.
Word SHA256 đọc lại trùng bản duyệt. Guard/manifest sau cập nhật ledger:
10 tests OK, 0.856s (lượt riêng, không cộng vào 33 để suy ra test duy nhất).

## Kiểm chứng ngoài máy

- Browser không khởi tạo được: kernel assets os error 3; không có ảnh QA mới.
- Public HTTP probe lúc 2026-09-25T08:32:40Z: ReadTimeout trước khi nhận trang.
  File output/public_probe_20260925_claim_batch.json. Không gửi truy vấn địa điểm
  vì chưa có trang/CSRF; không có GPS, cookie/CSP hoặc SHA deployment được chứng minh.
- Không push/deploy toàn bộ dirty worktree, không đổi schema/dữ liệu nghiệp vụ.
- Restore vẫn HOÃN. Không giả lập sự kiện Sentry, OAuth hoặc inbox thành công.

## Cần bổ sung để đóng các cổng còn lại

1. Phiếu chấm ngữ nghĩa trên bộ độc lập và người kiểm duyệt; bộ 4 câu hiện tại
   chỉ là packet hỗ trợ, không đủ suy rộng chất lượng LLM.
2. Chính sách doanh nghiệp được người có thẩm quyền xác nhận (không phải AI recap).
3. Thiết bị thật cấp quyền GPS và deployment truy cập được để kiểm địa chỉ/CSP.
4. Release SHA cùng CI run URL/artifact, worker recovery log, Sentry event,
   OAuth/email evidence tương ứng; quyền repo không thay tài khoản/hạ tầng này.
5. Đối chiếu phần thư mục IEEE còn lại; metadata nguồn Krebs đang cần xác minh.
6. Secret rotation/provider và bảo vệ release phải kiểm riêng; scanner known-pattern
   không có cam kết phát hiện mọi bí mật. Restore chỉ tiếp tục khi user bỏ hoãn.
