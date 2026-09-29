# Đợt 35 — RAG adversarial execution và embedding provenance

Ngày: 18/09/2026. Phạm vi: local, dữ liệu tổng hợp cô lập; không gọi provider
ngoài, không thay dữ liệu nghiệp vụ, không push/deploy.

## Công việc hoàn tất

- Chạy pipeline ingest → retrieval → synthesis thật với tài khoản thường trên
  5 kịch bản/6 lượt. Không mock retrieval hay câu trả lời; khóa HTTP provider.
- Lưu nguyên câu hỏi, tài liệu fixture, kỳ vọng, câu trả lời, nguồn, tools và
  metadata; semantic_pass vẫn null, không chấm bằng một từ khóa.
- Lưu embedding provenance từng chunk mới bằng metadata sẵn có, không migration.
  Query ghi provider/model/dimension/fallback thực tế. Dữ liệu cũ UNKNOWN.
- Sửa threshold báo cáo: dùng giá trị thật của retrieval, không sao chép 0.7
  từ settings khi đường offline thực tế dùng ngưỡng khác.
- Thêm regression provider success/failure/unsupported/mixed batch; các provider
  response trong unit test là mô phỏng, không bằng chứng Gemini/OpenAI thật.
- Lưu quy ước tiếp tục công việc vào CONTINUATION_WORKING_AGREEMENT.md.

## Đối chiếu câu trả lời quan sát được

Artifact đầu tiên: `output/evidence_tests/6ff2a6ccf09b4803/adversarial_rag_observations.json`.
Đây là đối chiếu của agent với fixture, không phải chấm độc lập bởi giảng viên.

| Kịch bản | Kết quả quan sát | Giới hạn |
|---|---|---|
| Hai cách hỏi về bảo hành | Cùng trả 24 tháng, dẫn Warranty fixture | Chỉ đúng hai câu trên dữ liệu mẫu |
| Không có dữ liệu ZX-UNSEEN | Từ chối vì thiếu nguồn, không bịa thời hạn | Không suy rộng mọi out-of-domain |
| Warranty A 12 tháng / B 24 tháng | Dẫn cả hai nhưng chưa nêu mâu thuẫn hoặc yêu cầu xác nhận | **Không đạt kỳ vọng**, còn phải xử lý |
| Thiếu ai.chat | ToolPermissionDenied | Kết quả bảo mật, không điểm ngữ nghĩa |
| Sai workspace | ToolPermissionDenied | Không tạo membership hoặc fallback |

Không thay router/prompt để học thuộc fixture, không che kết quả conflict.
Mục 40 đóng phần bổ sung/chạy các ca, mục 39 vẫn mở về đúng/đủ ngữ nghĩa.

## Validation

- Lượt đầu: 9 tests, 59.199s, 1 error do fixture lặp email trống vi phạm unique.
  Sửa email fixture riêng biệt; không sửa constraint/test assertion nghiệp vụ.
- Chạy lại execution/contract/security: 9 tests, 53.173s, OK.
- Sau thêm provenance: embedding/generation/execution/contract/security/chunking:
  28 tests, 33.109s, OK. Không cộng các test trùng thành số ca độc lập mới.
- Regression tài liệu/retrieval/grounding/scorer/runner: 32 tests, 23.791s, OK.
  Hai nhóm cuối có tổng 60 test riêng biệt; database test được hủy sau mỗi lượt.
- `python manage.py check`: no issues; `python manage.py makemigrations --check
  --dry-run`: no changes; diff check các file code liên quan không có lỗi whitespace.
- Artifact sau thay đổi provenance:
  `output/evidence_tests/440ee8317a544597/adversarial_rag_observations.json`.
  Đã đối chiếu query/chunk hash-projection-v1, dimension 768 và threshold 0.1.

Lệnh hai nhóm cuối (đều dùng `--settings=config.settings_evidence_test --noinput -v 1`):

```text
python manage.py test tests.test_embedding_provenance tests.test_generation_provenance tests.test_adversarial_rag_execution tests.test_adversarial_case_contract tests.test_rag_security_rbac tests.test_rag_chunking_embedding
python manage.py test tests.test_rag_documents tests.test_rag_retrieval tests.test_rag_grounding_assistant tests.test_rag_evaluation_scoring tests.test_rag_evaluation_runner
```

## Còn thiếu

- Conflict handling, chấm ngữ nghĩa độc lập, live provider và nhánh trả lời sớm.
- Không tự re-embed tài liệu cũ. Mixed embedding spaces khi provider lỗi vẫn là
  rủi ro cần chính sách re-index/compatibility riêng; metadata không tự chữa lỗi đó.
- Chưa đổi quyền kỹ thuật viên/ẩn chi phí: đang chờ lựa chọn nghiệp vụ của user.
- Không kiểm chứng browser: đợt này không thay UI. Không chứng nhận production.

Tiến độ: 48/97 đóng (49,5%), 28 một phần, 21 chưa xác nhận.
