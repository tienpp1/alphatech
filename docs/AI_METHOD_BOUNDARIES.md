# Nạp tri thức, viết công cụ và huấn luyện là ba việc khác nhau

Đối chiếu mã nguồn ngày 16/09/2026. Dùng phần này khi giải thích phương pháp
trong báo cáo/bảo vệ; không dùng cụm “huấn luyện Gemini bằng SOP” cho pipeline hiện có.

| Hoạt động | Đường thực thi hiện có | Kết quả, không được suy diễn |
|---|---|---|
| Nạp SOP/tài liệu | `apps/knowledge/services.py:ingest_document`: parse, chunk, embed, lưu DocumentChunk | Tạo chỉ mục tri thức, không cập nhật trọng số Gemini |
| Sinh embedding | `apps/knowledge/embedding.py:get_embedding` | Gọi API provider nếu có cấu hình và thành công; nếu không dùng hash projection deterministic. Đây không phải huấn luyện embedding mới |
| Viết handler/công cụ | `apps/knowledge/tools.py`, `apps/approvals/registry.py` | Lập trình phép tính/truy vấn/action, không huấn luyện LLM; cần RBAC và contract riêng |
| Sinh câu trả lời | `apps/knowledge/services.py:generate_grounded_answer` | Suy luận qua provider hoặc nhánh deterministic; metadata generation cho biết nhánh đã dùng ở normal synthesis, các đường chưa ghi metadata là UNKNOWN |
| Huấn luyện dự báo | `apps/forecasting/training.py`: XGBRegressor, model.fit | Fit mô hình XGBoost trên dữ liệu đặc trưng; không huấn luyện lại Gemini |

Chưa có bằng chứng fine-tuning Gemini trong các pipeline được đối chiếu trên.
Thêm tài liệu có thể thay đổi ngữ cảnh truy xuất và câu trả lời mà không đổi trọng
số mô hình. Thêm handler có thể tăng phạm vi nghiệp vụ mà không cải thiện mô hình
ngôn ngữ. Metric dự báo chỉ đánh giá mô hình/target/run tương ứng, không đo RAG.

Một API key không chứng minh lần gọi thành công. Generation metadata không thay
thế provenance của embedding: từ đợt 35, chunk mới ghi mode/model/provider từng
vector; chunk cũ vẫn UNKNOWN. Đợt 36 loại vector biết chắc khác không gian embedding,
không tự tái lập chỉ mục hoặc giả định model cho dữ liệu cũ. Mục 35/36 vẫn một phần;
không nhận tất cả kết quả offline là semantic
embedding hoặc câu trả lời LLM. Đánh giá lexical cũng không thay thế chấm nội dung
và nguồn độc lập bởi người đánh giá.
