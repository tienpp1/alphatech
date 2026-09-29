# Đối chiếu nguồn chính sách trước khi công bố

Ngày 18/09/2026. Đã nhận bản tổng hợp của Gemini trong file “1. Chốt phạm vi nghiệp vụ (Phân tíc.txt”.
Đây là kết quả dò mã nguồn/SOP, không phải văn bản chính sách được duyệt hay chứng nhận.
Không suy ra chứng nhận, mức bồi hoàn hoặc SLA có hiệu lực từ bản tổng hợp đó.
Không kết luận doanh nghiệp không có chính sách; chỉ chưa có bằng chứng trong đợt rà.

| Bề mặt | Phát hiện | Xử lý / cần đối chiếu |
|---|---|---|
| Email đơn hàng | Lấy SOP từ RETAIL đầu tiên, không có quyền xuất bản tài liệu | Đã bỏ retrieval; giữ itemization/tổng tiền, hướng dẫn xác nhận bảo hành/đổi trả/hóa đơn |
| Email dịch vụ | Lấy SOP từ SERVICE đầu tiên; mặc định ISO 27001/NDA tuyệt đối và thời hạn tự gán | Đã bỏ retrieval và claim mặc định; giữ mã phiếu/dịch vụ/mức ưu tiên/thời gian |
| Email liên hệ | Hứa phản hồi trong 24 giờ làm việc | Đã đổi thành xác nhận tiếp nhận, thời gian xử lý cần xác nhận |
| Trang giới thiệu | CO/CQ toàn bộ sản phẩm, ISO 27001, SLA 15–30 phút, 99.8% | Đã bỏ cam kết mặc định; thay số liệu marketing không có nguồn bằng thông tin sử dụng hệ thống |
| Trang sản phẩm | Default description bảo hành 12–24 tháng/CO-CQ và giao hỏa tốc | Đã sửa nội dung mặc định; không sửa description trong catalog DB |
| Trang chủ | NDA bảo mật tuyệt đối, VAT tức thì | Đã chuyển sang xác nhận điều kiện theo yêu cầu/đơn hàng |
| Trang liên hệ | Phản hồi trong 24 giờ | Đã đồng bộ với email; không đổi thời hạn xác minh tài khoản |
| 24 SOP trong data/knowledge | File có quy tắc cụ thể nhưng không có bằng chứng duyệt/công khai trong lần rà | Giữ nguyên nguồn để đối chiếu; không tự xóa, ingest lại hoặc coi là hợp đồng khách hàng |

## Đối chiếu bản Gemini

- SOP_RETAIL_FINANCIAL_MARGIN_2026.md: 10% là ký quỹ mở rộng hạn mức;
  3% là đệm chi phí VAT/vận hành trong quy tắc giá sàn. Không chứng minh
  thuế suất 10%, giá đã gồm VAT hay tích hợp hóa đơn điện tử.
- SOP_SVC_CHANGE_MANAGEMENT_2026.md mô tả quy trình thay đổi/CAB/rollback;
  không phải chứng nhận ISO 27001. Câu trên template không là bằng chứng độc lập.
- SOP RMA/SLA có mốc thời gian và điều kiện demo cụ thể; sự tồn tại của file
  không xác nhận doanh nghiệp đã duyệt áp dụng/công bố cho khách hàng.
- Không sửa, ingest lại hoặc xóa SOP; không sửa snapshot email cũ.

## Điều kiện để đưa chính sách vào email

Chỉ dùng nội dung công khai đã được chủ sở hữu xác nhận, có phiên bản/ngày hiệu
lực/phạm vi sản phẩm hoặc dịch vụ. Tài liệu truy xuất đúng workspace vẫn chưa đủ
quyền công bố ra ngoài. Hiện chưa có contract xuất bản SOP nên email không gọi
retrieval nội bộ; không chữa bằng cách chỉ đổi first workspace thành order.workspace.

Không sửa các snapshot email đã tạo hoặc gửi, không thay outbox dedup/retry.
Những bản cũ có thể giữ nội dung trước bản vá; không tự rewrite dữ liệu người dùng.

## Khi nhận file

1. Đọc bản đầy đủ, phân biệt chữ ký/phê duyệt, ngày hiệu lực, đơn vị áp dụng.
2. Lập ánh xạ từng điều khoản với website/chatbot/email; hỏi điểm mâu thuẫn.
3. Chỉ công bố phần được phép công khai; không đưa thông tin nội bộ/khách hàng vào email.
4. Regression nội dung, người nhận, outbox; kiểm browser nếu sửa web và render email.

Các mục 43–46 vẫn một phần. Bản này là inventory và ranh giới công bố, không là
tư vấn pháp lý hay chứng nhận chính sách của doanh nghiệp.
