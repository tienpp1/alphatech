# QUY CHUẨN ĐIỀU PHỐI TỒN KHO LIÊN CHI NHÁNH, ĐÀM PHÁN NHÀ CUNG CẤP & DỰ BÁO ĐỨT HÀNG 2026
**Mã hiệu:** SOP-RET-SC-2026 | **Đơn vị ban hành:** Ban Quản trị Vận hành Chuỗi Bán lẻ ABC Tech Store

---

## 1. Định Mức Tồn Kho An Toàn (Safety Stock Thresholds)
Để đảm bảo trải nghiệm khách hàng và ngăn ngừa triệt để sự cố đứt gãy chuỗi cung ứng, mọi chi nhánh bán lẻ trực thuộc hệ thống bắt buộc phải duy trì mức tồn kho khả dụng tối thiểu như sau:

| Danh mục sản phẩm | Tồn kho tối thiểu / Chi nhánh | Ngưỡng cảnh báo nguy cơ cao (High Risk) | Ngưỡng cảnh báo cháy hàng (Stockout) |
|---|---|---|---|
| **Laptop & Máy tính xách tay** | **05 chiếc** / model kinh doanh | Dưới 03 chiếc (thời gian cạn kiệt < 3 ngày) | = 0 chiếc (Hết hàng toàn diện) |
| **Máy chủ & Trạm xử lý (Server/Workstation)** | **02 chiếc** / cấu hình chuẩn | Dưới 02 chiếc | = 0 chiếc |
| **Thiết bị mạng & Router công nghiệp** | **10 thiết bị** | Dưới 05 thiết bị | = 0 thiết bị |
| **Linh kiện, Bàn phím & Chuột văn phòng** | **20 sản phẩm** | Dưới 08 sản phẩm | = 0 sản phẩm |

---

## 2. Thông Số Nhà Cung Cấp & Thời Gian Nhập Hàng (Lead Time)
Hệ thống AI Assistant khi lập kế hoạch bù hàng cần đối chiếu với các cam kết SLA của nhà cung cấp chính hãng:

1. **Nhà Cung Cấp Dell Vietnam Distribution**:
   - Thời gian giao hàng tiêu chuẩn (Lead Time): **3 đến 5 ngày làm việc**.
   - Chính sách chiết khấu mua buôn số lượng lớn: Đơn đặt hàng từ **20 chiếc Laptop trở lên** được áp dụng chiết khấu thương mại **8%** trực tiếp trên giá nhập gốc.
   - Hạn mức thanh toán: Công nợ 30 ngày đối với đối tác chiến lược cấp Tier-1.

2. **Nhà Cung Cấp Asus / HP Authorized**:
   - Thời gian giao hàng tiêu chuẩn (Lead Time): **4 đến 6 ngày làm việc**.
   - Chính sách chiết khấu: Đơn đặt hàng trên 50 triệu VND được chiết khấu 5%.

3. **Nhà Cung Cấp Thiết Bị Mạng Cisco Systems**:
   - Thời gian giao hàng tiêu chuẩn (Lead Time): **7 đến 10 ngày làm việc**.
   - Điều kiện nhập khẩn cấp: Giao hàng hỏa tốc trong 48 giờ với phụ phí logistics 12%.

---

## 3. Quy Trình Điều Chuyển Hàng Khẩn Cấp Giữa Các Chi Nhánh (Inter-branch Transfer)
1. Khi Chi nhánh Quận 1 (Mã: `CN-Q1`) hoặc Chi nhánh Bình Thạnh (Mã: `CN-BT`) phát sinh nguy cơ cháy hàng (< 3 ngày):
   - Hệ thống quét tồn kho của chi nhánh còn lại.
   - Nếu chi nhánh nguồn có mức tồn kho đạt trên **150% định mức an toàn**, AI được phép đề xuất lệnh điều chuyển nội bộ thay vì chờ nhập mới từ nhà cung cấp.
2. Thời gian vận chuyển liên chi nhánh nội thành TP.HCM: Tối đa **2 giờ làm việc**.
3. Chi phí vận chuyển liên chi nhánh được hạch toán vào chi phí vận hành chung của công ty mẹ.

---

## 4. Cơ Chế Phê Duyệt Lệnh Mua Hàng & Nhập Kho (HITL Control)
1. Tuyệt đối nghiêm cấm AI tự ý phát hành Đơn đặt hàng (Purchase Order - PO) thanh toán cho nhà cung cấp bên ngoài.
2. Khi phát hiện sản phẩm có nguy cơ đứt hàng, AI có trách nhiệm:
   - Tổng hợp số lượng tồn hiện tại, tốc độ tiêu thụ dự báo (Daily Demand), và số lượng cần nhập bù (Suggested Reorder Quantity).
   - Khởi tạo một bản ghi **Yêu cầu Phê duyệt Nhập kho** (`GoodsReceiptApprovalRequest`) ở trạng thái **CHỜ PHÊ DUYỆT (PENDING)**.
   - Đơn hàng chỉ được chuyển đến nhà cung cấp sau khi Giám đốc Chuỗi cung ứng hoặc Quản lý chi nhánh ký duyệt điện tử trên hệ thống nội bộ `/noibo/`.
