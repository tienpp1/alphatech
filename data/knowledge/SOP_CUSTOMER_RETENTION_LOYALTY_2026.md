# QUY CHUẨN VẬN HÀNH: VÒNG ĐỜI KHÁCH HÀNG, PHÒNG NGỪA RỜI BỎ & CAM KẾT DỊCH VỤ VIP 2026
**Mã hiệu:** SOP-CRM-RET-2026  
**Áp dụng:** Hệ thống Bán lẻ & Vận hành Dịch vụ Kỹ thuật (`abc-retail`, `xyz-service`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Tiêu Chuẩn Phân Cấp Khách Hàng Doanh Nghiệp & Cá Nhân (Customer Tiering Matrix)
Hệ thống phân cấp tự động dựa trên Giá trị Trọn đời Khách hàng (Customer Lifetime Value - CLV) và Tần suất giao dịch (Recency - Frequency - Monetary):

| Phân Hạng Khách Hàng | Điều Kiện Doanh Thu Tích Lũy (CLV) | Tần Suất Giao Dịch | Chính Sách Chiết Khấu Trực Tiếp |
|---|---|---|---|
| **VIP Platinum** | Doanh số $\ge 50,000,000$ VND | $\ge 3$ đơn hàng/năm hoặc Hợp đồng bảo trì DN | Giảm trực tiếp **10.0%** phí dịch vụ kỹ thuật, 3% phụ kiện |
| **Gold / Doanh Nghiệp** | Doanh số từ $20,000,000$ đến $< 50,000,000$ VND | $\ge 2$ đơn hàng/năm | Giảm trực tiếp **5.0%** phí dịch vụ kỹ thuật |
| **Silver / Phổ Thông** | Doanh số $< 20,000,000$ VND | Khách hàng vãng lai | Áp dụng bảng giá niêm yết chuẩn |

---

## 2. Dấu Hiệu Cảnh Báo Nguy Cơ Khách Hàng Rời Bỏ (Churn Risk Triggers)
Hệ thống định kỳ quét các chỉ số rủi ro khách hàng rời bỏ để kích hoạt quy trình giữ chân kịp thời:

1. **Rủi ro Không Phát sinh Giao dịch (Inactivity Churn Risk):**
   - Khách hàng hạng VIP hoặc Gold không có bất kỳ đơn hàng mới nào trong vòng **$\ge 45$ ngày** liên tiếp.
   - Doanh thu dự kiến thất thoát được tính bằng giá trị giỏ hàng bình quân nhân với chu kỳ mua hàng chuẩn.
2. **Rủi ro Trải nghiệm Kỹ thuật Tiêu cực (Service Friction Churn Risk):**
   - Khách hàng có ít nhất 01 phiếu yêu cầu dịch vụ kỹ thuật bị trễ hạn cam kết SLA (SLA Breached).
   - Thiết bị phải bảo hành lại trên 2 lần trong vòng 30 ngày cho cùng một lỗi phần cứng.

---

## 3. Đặc Quyền Khách Hàng VIP & Cam Kết Chất Lượng Dịch Vụ (VIP Service Level Agreement)
Khách hàng đạt hạng VIP Platinum được hưởng các cam kết đặc thù cao cấp:

1. **Luồng Tiếp Nhận Ưu Tiên 1 (Priority Queue 1):**
   - Mọi cuộc gọi hoặc yêu cầu bảo hành được tiếp nhận và xử lý trong vòng **$\le 15$ phút**.
   - Kỹ thuật viên hiện trường có mặt tại trụ sở doanh nghiệp trong vòng **$\le 60$ phút** kể từ khi mở phiếu P1/P2.
2. **Chính Sách Cho Mượn Thiết Bị Thay Thế Miễn Phí (Free Loaner Equipment Policy):**
   - Trong thời gian máy tính xách tay hoặc máy chủ của khách hàng VIP được tiếp nhận sửa chữa hoặc chờ linh kiện thay thế (kéo dài trên 24 giờ), hệ thống tự động cung cấp **01 Laptop/Thiết bị dự phòng tương đương hoàn toàn miễn phí** để khách hàng không bị gián đoạn công việc kinh doanh.
3. **Người Quản Lý Tài Khoản Riêng (Dedicated Account Manager):**
   - Hỗ trợ tư vấn kỹ thuật và báo giá 24/7.

---

## 4. Quy Trình Khắc Phục Sự Cố & Giữ Chân Khách Hàng VIP (Service Recovery SOP)
Khi phát hiện vi phạm SLA hoặc khách hàng VIP có phản hồi không hài lòng, bộ phận CSKH thực hiện quy trình khắc phục trong vòng 24 giờ:
- **Bước 1:** Gửi thư xin lỗi chính thức ký bởi Giám đốc Vận hành Dịch vụ.
- **Bước 2:** Cấp tự động **01 Voucher dịch vụ kỹ thuật trị giá 500,000 VND** (có hiệu lực 180 ngày).
- **Bước 3:** Tặng thêm **03 tháng bảo hành mở rộng** cho toàn bộ thiết bị đang bảo trì tại hệ thống.
- **Đề xuất chiến dịch giữ chân (Retention Campaign Proposal):** Trợ lý AI lập đề xuất gửi voucher kích hoạt cho nhóm khách hàng VIP at-risk chờ phê duyệt trước khi gửi hàng loạt.
