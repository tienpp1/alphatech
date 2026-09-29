# Đợt 26 — Phiếu chấm RAG có đối chiếu đúng bản kết quả

Ngày: 16/09/2026.

## Kết quả triển khai

- Thêm lệnh `review_rag_evidence` xuất phiếu chấm JSON và tổng hợp phiếu đã điền.
- Phiếu mang SHA-256 của toàn bộ report đầu vào; report thay đổi thì phiếu cũ bị
  từ chối. ID trùng, không tồn tại hoặc ca thực thi lỗi không được chấm.
- Phiếu hiển thị câu hỏi, toàn văn trả lời, nguồn và tool; các report mới của
  scorer lưu thêm câu hỏi và nhóm từ khóa bắt buộc.
- Bốn tiêu chí độc lập: đúng sự kiện, đúng số liệu, đủ ý, trích dẫn hỗ trợ kết luận.
  Chỉ nhận boolean true/false; null nghĩa là chưa chấm. Không tự suy ra từ proxy.
- Phiếu hoàn chỉnh yêu cầu người chấm, thời gian có timezone, căn cứ và nhận xét.
- Báo cáo tổng hợp ghi số ca chấm/chưa chấm/lỗi, coverage và tỷ lệ đạt trên số ca
  đã chấm. File đích phải chưa tồn tại để giữ bản cũ.

## Cách sử dụng

Đầu vào là JSON nguyên bản do `run_benchmark_evaluation` trả về, có `details`.
Không dùng bảng số liệu tổng hợp thiếu câu trả lời. Lưu report trong thư mục
nội bộ vì có thể chứa thông tin kinh doanh. Không đưa report lên static/public.

```powershell
python manage.py review_rag_evidence --report output/rag-report.json --output output/rag-review.json
```

Trong `reviews`, đối chiếu từng câu với snapshot tài liệu/số liệu tương ứng rồi
điền `reviewer`, `reviewed_at` (ví dụ `2026-09-16T10:00:00+07:00`),
`reference_evidence`, `notes` và bốn tiêu chí. Để null nếu chưa có đủ căn cứ.
Với câu không có số liệu, ghi rõ không có phát biểu định lượng trong notes trước
khi đánh dấu `numbers_correct=true`. Với từ chối đúng, nhận xét cần giải thích
vì sao thiếu nguồn/quyền; không coi thiếu trích dẫn tự động là một lỗi.

```powershell
python manage.py review_rag_evidence --report output/rag-report.json --review output/rag-review.json --output output/rag-human-results.json
```

Các tên file trên là ví dụ sử dụng, chưa phải artifact đã chấm thật.

## Kiểm chứng

```text
python manage.py test tests.test_rag_human_review tests.test_rag_evaluation_scoring tests.test_rag_evaluation_runner --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

24/24 qua trong 0.228 giây, gồm 6 test mới. Kiểm chứng ca đúng từ khóa nhưng sai
số liệu bị người chấm đánh trượt, thiếu chấm không được tính đạt, file report
đổi làm phiếu hết hiệu lực, và command không ghi đè file hiện có.
Lần đầu sandbox chặn file tạm Windows; chạy lại cùng nhóm ngoài sandbox đạt.

## Còn cần nghiệm thu

Cần snapshot đáp án/nguồn và người đánh giá chấm các kết quả benchmark thật.
Công cụ ghi nhận đánh giá do người nhập, không xác thực danh tính hoặc tính đúng
của căn cứ được nhập. Tỷ lệ đạt trên câu đã chấm không đại diện toàn bộ tập khi
coverage chưa đủ. Chưa đánh giá LLM thật; không push/deploy trong đợt này.
Mục 39 vẫn một phần; tổng đóng vẫn 37/97 (38,1%).
