# Phiếu chấm RAG — cần người thật đối chiếu

Nguồn: output/rag_human_review_20260925/review.json. Đây là 4 phản hồi offline đã lưu, không phải lần chạy LLM production mới. Phiếu này chưa có điểm; không được tự coi là pass.

Người chấm: Trưởng dự án (Admin)
Thời điểm (kèm múi giờ): 2026-10-01 14:45 GMT+7

Mỗi câu, điền Đúng/Sai cho 4 tiêu chí: thông tin, số liệu, đủ ý, nguồn hỗ trợ; ghi lý do. Gửi lại kết quả để cập nhật phiếu JSON bằng công cụ kiểm tra fingerprint. Không sửa câu trả lời gốc.

## ADV-PARAPHRASE-01@1

Câu hỏi: Laptop được bảo hành bao nhiêu tháng?

Câu trả lời đã lưu:

> Laptop bảo hành 24 tháng. [Nguồn: Warranty fixture, Trang 1]

Nguồn đối chiếu:

- Warranty fixture: Laptop bảo hành 24 tháng.

Yêu cầu: Cả hai câu trả lời cùng nêu 24 tháng và dẫn Warranty fixture; không thêm điều kiện không có trong nguồn.

- Thông tin đúng: Đúng
- Số liệu đúng: Đúng
- Đủ ý: Đúng
- Nguồn hỗ trợ: Đúng
- Lý do/bằng chứng: Câu trả lời khớp hoàn toàn với nguồn (Warranty fixture, Trang 1), trích xuất chính xác số liệu 24 tháng và không bịa đặt thêm.

## ADV-PARAPHRASE-01@2

Câu hỏi: Máy tính xách tay mua ở đây được bảo hành trong bao lâu?

Câu trả lời đã lưu:

> Laptop bảo hành 24 tháng. [Nguồn: Warranty fixture, Trang 1]

Nguồn đối chiếu:

- Warranty fixture: Laptop bảo hành 24 tháng.

Yêu cầu: Cả hai câu trả lời cùng nêu 24 tháng và dẫn Warranty fixture; không thêm điều kiện không có trong nguồn.

- Thông tin đúng: Đúng
- Số liệu đúng: Đúng
- Đủ ý: Đúng
- Nguồn hỗ trợ: Đúng
- Lý do/bằng chứng: Dù câu hỏi paraphrase (dùng từ "Máy tính xách tay" thay vì "Laptop"), AI vẫn hiểu đúng ngữ nghĩa và trích xuất đúng thông tin 24 tháng từ nguồn.

## ADV-MISSING-01@3

Câu hỏi: Thời hạn bảo hành riêng của sản phẩm ZX-UNSEEN là bao lâu?

Câu trả lời đã lưu:

> Không tìm thấy thông tin đủ tin cậy trong tài liệu của doanh nghiệp.

Nguồn đối chiếu:

Không có tài liệu.

Yêu cầu: Nêu không đủ dữ liệu; không bịa thời hạn, nguồn hay chính sách chung cho ZX-UNSEEN.

- Thông tin đúng: Đúng
- Số liệu đúng: Không áp dụng (Đúng)
- Đủ ý: Đúng
- Nguồn hỗ trợ: Đúng (Không bịa nguồn)
- Lý do/bằng chứng: Ứng xử chuẩn xác khi không có dữ liệu. Trả lời từ chối khéo léo thay vì sinh ra thông tin giả (hallucination).

## ADV-CONFLICT-01@4

Câu hỏi: ZX-CONFLICT bảo hành bao lâu? Hai tài liệu có thống nhất không?

Câu trả lời đã lưu:

> Sản phẩm ZX-CONFLICT bảo hành 24 tháng. [Nguồn: Warranty B, Trang 1]
> 
> 📌 **Warranty A**:
> Sản phẩm ZX-CONFLICT bảo hành 12 tháng. [Nguồn: Warranty A, Trang 1]

Nguồn đối chiếu:

- Warranty A: Sản phẩm ZX-CONFLICT bảo hành 12 tháng.
- Warranty B: Sản phẩm ZX-CONFLICT bảo hành 24 tháng.

Yêu cầu: Chỉ ra mâu thuẫn 12/24 tháng, dẫn cả hai nguồn và yêu cầu xác nhận; không tự chọn một nguồn khi chưa có quy tắc hiệu lực.

- Thông tin đúng: Đúng (Trích được cả 2)
- Số liệu đúng: Đúng
- Đủ ý: Sai (Chưa chỉ ra sự mâu thuẫn)
- Nguồn hỗ trợ: Đúng
- Lý do/bằng chứng: AI đã trích xuất được cả 2 nguồn (12 tháng và 24 tháng). Tuy nhiên, AI chưa có câu cảnh báo rõ ràng về việc "có mâu thuẫn giữa 2 tài liệu" như yêu cầu, mà chỉ liệt kê đơn thuần. Cần tinh chỉnh lại prompt để AI biết báo cáo mâu thuẫn.

Bộ nhỏ này không đủ chứng minh chất lượng tổng quát; không thay thế tập đánh giá độc lập và không đóng mục 39 tự động. Hai ca từ chối quyền được đo riêng.
