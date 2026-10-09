# Hướng dẫn nội bộ: tri thức, RAG và nguồn

Phạm vi: hướng dẫn nền tảng, bản 09/10/2026. Nguồn: apps/knowledge/services.py, retrieval.py, embedding.py và sop_catalog.py. Không xác nhận chính sách thương mại của một doanh nghiệp bên ngoài.

## RAG khác training mô hình như thế nào?

RAG phân tích tài liệu, chia chunk, tạo embedding rồi truy xuất đoạn phù hợp theo workspace trước khi tạo câu trả lời. Nạp tài liệu không cập nhật trọng số của Gemini. Khi không có API key hoặc provider lỗi, nền tảng có chế độ deterministic; không gọi kết quả đó là output mô hình thật. Không có ngữ cảnh đủ tin cậy thì từ chối hoặc yêu cầu bổ sung, không đoán.

## Tài liệu nào được dùng làm chính sách?

Xuất hiện trong kết quả tìm kiếm không chứng minh tài liệu được duyệt hoặc còn hiệu lực. SOP hiện có có thể chỉ phục vụ đồ án. Không biến ví dụ SLA, VAT, bảo hành, bồi hoàn hoặc chứng nhận ISO thành cam kết công khai. Cần văn bản được người có thẩm quyền xác nhận, phạm vi và thời điểm áp dụng. Hướng dẫn này cũng không thay thế văn bản chính sách đó.

## Hai tài liệu mâu thuẫn thì trả lời thế nào?

Nêu rõ thông tin của từng nguồn và trích dẫn. Ví dụ synthetic: một nguồn ghi 12 tháng, nguồn khác ghi 24 tháng; không tự chọn 24 tháng vì đứng đầu danh sách truy xuất. Nếu thiếu ngày hiệu lực hoặc phê duyệt, yêu cầu người phụ trách xác nhận. Thứ hạng similarity đo liên quan, không đo thẩm quyền hoặc độ đúng của chính sách.

## Vì sao upload tài liệu chưa trả lời được?

Kiểm tra trạng thái PENDING, PROCESSING, READY hoặc FAILED. Chỉ tài liệu READY được truy xuất. FAILED cần xem chẩn đoán an toàn và sửa định dạng/nội dung trước khi nạp lại. Embedding phải cùng không gian model/provider/dimension; vector cùng số chiều chưa chắc tương thích. Không re-ingest hàng loạt tài liệu cũ nếu chưa được phép vì có thể thay thế chunk hiện tại.

## Đánh giá AI đúng và đủ bằng cách nào?

Đối chiếu sự thật, số liệu, nguồn, phạm vi workspace và mức đầy đủ. Khớp một từ khóa không chứng minh đúng. Test do người triển khai tự tạo là regression, không phải holdout mù. Ghi cả câu sai, thiếu ý và từ chối không phù hợp. Chỉ nói đã cải thiện ở các ca được đo; không tuyên bố đáp ứng mọi nhu cầu.
