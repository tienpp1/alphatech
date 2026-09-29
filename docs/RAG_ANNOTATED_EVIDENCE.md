# Đo đoạn nguồn và số liệu có chú giải — scorer 2.2

Phép đo hiện hành, không thay kết quả lịch sử. Không phải đánh giá LLM trực tiếp.

## Đo truy xuất

Rubric có thể khai báo `expected_chunk_ids` là các ID của đoạn chứa bằng chứng
trên cùng snapshot dữ liệu. Phải chọn trước khi xem response, không chép ID
trả về làm đáp án chuẩn. Bộ test adversarial chọn ID từ tài liệu fixture trước
khi gọi pipeline. ID không có ý nghĩa xuyên database: khi tái lập phải ánh xạ
từ tài liệu/đoạn của snapshot mới và lưu ánh xạ cùng artifact.

- Recall = số ID chuẩn truy xuất được / số ID chuẩn.
- Precision = số ID chuẩn truy xuất được / số ID truy xuất duy nhất cộng số
  citation thiếu ID. Citation lặp không làm tăng điểm; thiếu ID không bị bỏ qua.
- Không khai báo gold: null/chưa đo. Gold rỗng/sai kiểu: lỗi cấu hình.
- Aggregate là macro-average trên câu được chú giải, công bố số câu có/không
  có chú giải. Không dùng mẫu số toàn bộ để che thiếu coverage.
- `source_presence_rate` chỉ đo nguồn/tool mong đợi có xuất hiện.
  `retrieval_relevance_rate` giữ làm alias cũ đã deprecated, không phải đúng chunk.
- Có đúng ID chưa chứng minh citation hỗ trợ mọi ý hoặc văn bản đúng ngữ nghĩa.

## Kiểm số liệu

`required_numeric_facts` khai báo id, expected hữu hạn và regex do tác giả
benchmark kiểm soát, có nhóm `value`. Pattern cần gồm nhãn đại lượng và đơn vị,
không tìm một con số đứng riêng trong toàn câu. Không nhận regex từ người dùng web.
Các giá trị trích xuất đều phải bằng giá trị chuẩn; thiếu, sai, hay hai giá trị
mâu thuẫn cùng nhãn đều không qua. Phân cách hàng nghìn/định dạng số theo vùng
không tự suy đoán; đáp án và pattern phải thống nhất và được kiểm thử riêng.

Giới hạn: “không bảo hành 24 tháng” vẫn chứa đại lượng 24 tháng. Phép đo này
không phân tích phủ định, ngoại lệ, hiệu lực văn bản hay sự đúng đắn toàn câu.
`semantic_correctness` giữ null; vẫn cần chấm độc lập và kiểm chứng nguồn.

## Tương thích và phạm vi

Scorer 2.2 chỉ yêu cầu các kiểm tra mới khi rubric có chú giải; báo cáo cũ không
được bổ sung điểm giả. Benchmark 16 câu và bộ độc lập chưa có gold chunk chuẩn
được thẩm định toàn bộ. Không tự suy ra số liệu doanh thu/ticket từ câu trả lời.
Không thay router, quyền, retrieval production hay prompt để học thuộc câu test.
