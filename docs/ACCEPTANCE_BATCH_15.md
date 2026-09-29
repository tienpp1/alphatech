# Đợt 15 — RAG workspace và role acceptance

Ngày đối chiếu: 15/09/2026.

## Mục tiêu

Kiểm tra assistant bằng user thường, user thiếu quyền và workspace khác; không
dùng superuser làm bằng chứng duy nhất.

## Bằng chứng

```powershell
python manage.py test tests.test_rag_security_rbac tests.test_rag_grounding_assistant tests.test_rag_independent_dataset --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **14 test passed, 45.160 giây**.

Phạm vi đã kiểm chứng gồm: AI chat cần `ai.chat`, user không có quyền bị từ
chối, tài liệu workspace khác trả 404, dữ liệu structured/query có scope,
grounded document/hybrid/fallback chạy bằng user workspace member và dataset
độc lập không dùng superuser làm rubric duy nhất.

Giới hạn: đây là acceptance local trên fixture; chưa phải benchmark semantic
độc lập đầy đủ, chưa có live LLM provenance và chưa có production certification.
