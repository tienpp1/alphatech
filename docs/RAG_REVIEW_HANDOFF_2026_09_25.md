# Phiếu đánh giá RAG cần đối chiếu — mục 39

Gói `output/rag_human_review_20260925/` gồm report.json, review.json và
initial_summary.json. Nguồn là các câu trả lời đã ghi ở replay offline 25/09,
không phải kết quả Google/Gemini API thật và không phải chính sách kinh doanh.

Có 4 câu trả lời được đưa vào phiếu; 2 ca từ chối truy cập được giữ ở
excluded_cases, không đưa vào mẫu số chất lượng trả lời. Các câu diễn đạt lại
cùng fixture được gắn ID riêng để tránh ghi đè. Điểm ban đầu đều null: 0/4 đã chấm.

Người chấm đọc question, answer, reference_documents, sources và expected.
Chỉ điền bốn trường facts_correct, numbers_correct, complete,
citations_support_claims bằng true/false sau khi đối chiếu; không lấy keyword
hoặc kết quả test để tự điền. Ghi reviewer, reviewed_at (ISO có múi giờ),
reference_evidence và notes cụ thể. Không sửa report.json hoặc đáp án gốc.

Đặc biệt ca ADV-CONFLICT-01 có hai nguồn 12/24 tháng; cần đánh giá việc giải thích
mâu thuẫn và yêu cầu xác nhận, không chỉ thấy cả hai con số là coi đúng/đủ.
Không gán thông tin chính sách demo thành cam kết thực tế.

Sau khi người chấm hoàn tất, dùng lệnh dưới (file summary mới chưa tồn tại):

```powershell
python manage.py review_rag_evidence --report output/rag_human_review_20260925/report.json --review output/rag_human_review_20260925/review.json --output output/rag_human_review_20260925/summary_reviewed.json
```

Fingerprint ràng buộc phiếu với câu trả lời/nguồn gốc. Công cụ không xác minh
danh tính người chấm, không tự chứng nhận độ tin cậy của người chấm. Bộ nhỏ này
không đủ kết luận chất lượng LLM tổng quát hoặc đóng toàn bộ mục 39; cần bộ độc lập
bao phủ các câu số liệu/hybrid và đối chiếu giao thức đánh giá trước nghiệm thu.
