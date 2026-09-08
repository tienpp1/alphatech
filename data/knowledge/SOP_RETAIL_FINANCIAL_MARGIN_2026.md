# QUY CHUẨN VẬN HÀNH: QUẢN TRỊ BIÊN LỢI NHUẬN & CHÍNH SÁCH TÍN DỤNG NHÀ CUNG CẤP 2026
**Mã hiệu:** SOP-FIN-RET-2026  
**Áp dụng:** Toàn bộ hệ thống bán lẻ (Workspace `abc-retail`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Định Mức Tỷ Suất Lợi Nhuận Gộp Theo Danh Mục Sản Phẩm (Gross Margin Policy)
Mỗi danh mục sản phẩm công nghệ kinh doanh trên hệ thống phải tuân thủ nghiêm ngặt biên độ lợi nhuận gộp mục tiêu (Target Gross Margin = (Doanh thu - Giá vốn) / Doanh thu):

| Danh Mục Sản Phẩm | Tỷ Suất Biên Mục Tiêu (Target) | Ngưỡng Cảnh Báo Rủi Ro (Threshold) | Hành Động Bắt Buộc Khi Dưới Ngưỡng |
|---|---|---|---|
| **Laptop & Máy Tính Bảng** | $\ge 12.0\%$ | Dưới $8.0\%$ | Kiểm tra lại giá nhập nhà phân phối, tạm dừng chương trình khuyến mãi tự động. |
| **Linh Kiện Máy Tính (CPU, RAM, SSD, VGA)** | $\ge 22.0\%$ | Dưới $15.0\%$ | Đàm phán lại chiết khấu lô lớn hoặc điều chỉnh đơn giá niêm yết. |
| **Thiết Bị Mạng & Viễn Thông (Router, Switch)** | $\ge 35.0\%$ | Dưới $25.0\%$ | Rà soát chi phí lưu kho và giá bán lẻ cạnh tranh trên thị trường. |
| **Phụ Kiện Máy Tính (Chuột, Bàn phím, Tai nghe)** | $\ge 40.0\%$ | Dưới $30.0\%$ | Đóng gói combo sản phẩm để kích thích tăng giỏ hàng trung bình. |

---

## 2. Điều Khoản Tín Dụng & Chiết Khấu Thanh Toán Sớm Từ Nhà Cung Cấp (Supplier Credit Terms)
Phòng Thu mua & Kế toán dòng tiền áp dụng các điều khoản thanh toán đối với các đối tác cung ứng chiến lược:

### 2.1. Nhà phân phối Viễn Sơn (Phân phối Kingston, Asus, Gigabyte)
- **Hạn mức công nợ (Credit Limit):** 500,000,000 VND.
- **Thời hạn công nợ chuẩn (Standard Terms):** Net 30 (Thanh toán đủ trong vòng 30 ngày kể từ ngày nhận hóa đơn).
- **Chính sách Chiết khấu Thanh toán Sớm (Cash Discount):** Điều khoản **`2/10 Net 30`** (Được chiết khấu ngay **2.0%** trên tổng giá trị đơn hàng nếu doanh nghiệp hoàn tất chuyển khoản thanh toán trong vòng **10 ngày** kể từ ngày giao hàng).
- **Khuyến nghị tài chính:** Luôn ưu tiên thanh toán trong vòng 10 ngày cho các hóa đơn trên 100 triệu để hưởng chiết khấu 2%, tương đương tỷ suất sinh lời vốn lưu động hàng năm đạt trên 36%.

### 2.2. Nhà phân phối Synnex FPT (Phân phối Dell, HP, Cisco)
- **Hạn mức công nợ:** 1,000,000,000 VND.
- **Thời hạn thanh toán:** Net 45.
- **Chính sách Thưởng Sản Lượng Quý (Quarterly Volume Rebate):** Hoàn lại **3.0%** bằng tiền mặt hoặc cấn trừ công nợ nếu tổng doanh số nhập khẩu trong quý đạt từ **500,000,000 VND** trở lên.

### 2.3. Nhà phân phối Digiworld - DGW
- **Hạn mức công nợ:** 300,000,000 VND.
- **Thời hạn thanh toán:** Net 15.
- **Điều kiện mở rộng hạn mức:** Ký quỹ bảo lãnh 10% giá trị hợp đồng mở rộng.

---

## 3. Quy Tắc Điều Chỉnh Giá & Hạ Giá Xả Kho Tồn Chậm (Dynamic Markdown Policy)
Khi phát hiện sản phẩm có tốc độ tiêu thụ chậm hoặc nguy cơ ứ đọng vốn, Trợ lý AI và Giám đốc bán lẻ áp dụng chính sách xả kho theo các mốc:

1. **Hàng Tồn Kho Lưu Kho Chậm (Slow-Moving Stock) từ 45 đến 60 ngày:**
   - Được phép đề xuất hạ giá tối đa **5.0%** so với giá niêm yết hiện tại.
   - Ưu tiên hiển thị trên banner trang chủ khuyến mãi hoặc gửi email ưu đãi cho khách hàng thân thiết.
2. **Hàng Tồn Kho Chết (Dead Stock / Stagnant) trên 90 ngày:**
   - Được phép đề xuất thanh lý xả kho với mức giảm tối đa **15.0%**.
   - **RÀNG BUỘC PHÁP LÝ & TÀI CHÍNH BẮT BUỘC (Floor Cost Protection):** Đơn giá bán thanh lý sau khi giảm tuyệt đối **không được thấp hơn** Đơn giá vốn nhập kho (`cost_price`) cộng thêm **3.0%** chi phí đệm thuế VAT và vận hành.
3. **Quy trình Phê duyệt Thay đổi Đơn giá (Human-In-The-Loop Approval):**
   - Mọi thao tác thay đổi đơn giá bán lẻ trên hệ thống không được thực thi trực tiếp bởi AI.
   - Trợ lý AI phải lập bản ghi Yêu cầu Phê duyệt (`ApprovalRequest`) với mã hành động `adjust_product_price`, kèm lý do, tỷ lệ giảm và đối chiếu giá vốn, chờ Quản lý chi nhánh hoặc Kế toán trưởng phê duyệt tại Trung tâm Quản trị `/noibo/approvals/`.
