# Đợt 25 — RAG proxy nhận diện mâu thuẫn đã khai báo

## Kết quả

Bộ chấm offline tại `apps/knowledge/evaluation_scoring.py` hỗ trợ
`forbidden_keyword_groups`. Khi câu trả lời chứa cụm phủ định/mâu thuẫn đã
khai báo, `contradiction_detected=true`, ghi lại nhóm khớp và không đạt
`lexical_evidence_pass_rate`. Câu trả lời thiếu nhóm bắt buộc vẫn bị loại như
trước. Các mâu thuẫn chưa khai báo vẫn được ghi rõ là giới hạn.

## Kiểm chứng

```text
python manage.py test tests.test_rag_evaluation_scoring tests.test_rag_independent_dataset tests.test_rag_evaluation_runner --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

Kết quả: **20/20 qua**. `python manage.py check` không có lỗi; `python manage.py
makemigrations --check --dry-run` báo `No changes detected`; `git diff --check`
cho source/test của đợt trả exit 0.

## Giới hạn và tiến độ

Đây là proxy lexical/evidence, không phải semantic judge. Không chứng minh đúng
số liệu, entailment, chất lượng Gemini hay provider thật. Mục 39 vẫn **Một phần**;
không tăng số mục đóng. Không thay đổi failure AI demonstration, schema,
production hay deployment.
