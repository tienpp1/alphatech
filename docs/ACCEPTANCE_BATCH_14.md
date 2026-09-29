# Đợt 14 — Bộ câu hỏi RAG độc lập

Ngày đối chiếu: 15/09/2026.

## Mục tiêu

Tách một bộ câu hỏi human-authored khỏi bộ benchmark được dùng khi sửa
router/prompt. Bộ mới có paraphrase, hybrid và câu hỏi ngoài phạm vi/thiếu dữ
liệu. Runner nhận dataset qua tham số `cases`, nhưng semantic correctness vẫn
chưa đo.

## Thay đổi

- Thêm `apps/knowledge/independent_benchmark.py` với 5 case có ID `IND-*`.
- Mở rộng `run_benchmark_evaluation(..., cases=...)` để chạy bộ độc lập mà
  không thay đổi bộ primary mặc định.
- Thêm regression kiểm tra ID không trùng, câu hỏi không sao chép primary,
  có hybrid và fallback có kiểm soát.

## Validation

```powershell
python manage.py test tests.test_rag_independent_dataset --keepdb --noinput -v 1
```

Đây chỉ là bằng chứng dataset/runner contract, không phải kết quả chất lượng
LLM. Các ca mâu thuẫn tài liệu, sai quyền theo từng vai trò và semantic human
review vẫn phải bổ sung.
