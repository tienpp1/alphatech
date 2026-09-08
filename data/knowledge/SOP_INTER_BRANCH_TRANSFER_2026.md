# QUY CHUẨN VẬN HÀNH: CÂN ĐỐI TỒN KHO ĐA CHI NHÁNH & TỐI ƯU HẬU CẦN ĐIỀU CHUYỂN NỘI BỘ 2026
**Mã hiệu:** SOP-LOG-TRF-2026  
**Áp dụng:** Quản lý Chuỗi Cung ứng & Hệ thống Kho Vận (`abc-retail`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Nguyên Tắc Kích Hoạt Điều Chuyển Tồn Kho Giữa Các Chi Nhánh (Rebalancing Trigger Rules)
Quy trình điều chuyển hàng hóa nội bộ giữa các chi nhánh (ví dụ: Chi nhánh Quận 1 `CN-Q1`, Chi nhánh Bình Thạnh `CN-BT`, Chi nhánh Tân Phú `CN-TP`) được kích hoạt khi thỏa mãn đồng thời hai điều kiện:

1. **Chi Nhánh Nguồn (Source Branch - Xuất kho điều chuyển):**
   - Lượng tồn kho hiện tại của sản phẩm vượt quá **45 ngày tiêu thụ** (tính theo tốc độ bán bình quân của 30 ngày gần nhất).
   - Tồn kho khả dụng sau khi trừ số lượng điều chuyển vẫn phải đảm bảo mức an toàn tối thiểu $\ge 14$ ngày bán.
2. **Chi Nhánh Đích (Destination Branch - Tiếp nhận điều chuyển):**
   - Lượng hàng tồn kho hiện tại còn dưới mức bảo vệ cấp bách: **$\le 7$ ngày tiêu thụ**.
   - Có lịch sử đơn hàng hoặc nhu cầu khách hàng đang tăng trưởng trong 7 ngày gần nhất.

---

## 2. Bảng Giá Cước Vận Chuyển Nội Bộ & Cam Kết Thời Gian (Logistics SLA & Costing)
Hệ thống vận tải nội bộ liên kết với các đơn vị giao vận hỏa tốc với định mức chi phí và thời gian giao nhận rõ ràng:

| Tuyến Đường Điều Chuyển | Khoảng Cách Ước Tính | Cam Kết Thời Gian (SLA) | Định Mức Chi Phí Vận Chuyển | Quy Định Trọng Lượng Chuẩn |
|---|---|---|---|---|
| **Nội Thành Hỏa Tốc (`CN-Q1` $\leftrightarrow$ `CN-BT`)** | Dưới 8 km | **$\le 2.0$ giờ** | **80,000 VND / chuyến** | Tối đa 30 kg / chuyến |
| **Liên Quận Mở Rộng (`CN-Q1` $\leftrightarrow$ `CN-TP` / `CN-Q7`)** | Từ 8 km đến 18 km | **$\le 4.0$ giờ** | **150,000 VND / chuyến** | Tối đa 50 kg / chuyến |
| **Ngoại Vi / Vệ Tinh (`CN-Q1` $\leftrightarrow$ `CN-ThuDuc`)** | Trên 18 km | **$\le 6.0$ giờ** | **220,000 VND / chuyến** | Tối đa 70 kg / chuyến |

---

## 3. Quy Định Quy Mô Lô Hàng Tối Thiểu (Minimum Transfer Lot Size)
Để tránh lãng phí chi phí vận tải và thủ tục chứng từ nhập/xuất kho, mọi lệnh điều chuyển phải đạt quy mô tối thiểu:
- **Đối với Laptop, Máy tính đồng bộ, Màn hình lớn:** Tối thiểu **$\ge 2$ chiếc** / chuyến điều chuyển.
- **Đối với Linh kiện (RAM, SSD, CPU, Ổ cứng):** Tối thiểu **$\ge 5$ chiếc** / chuyến.
- **Đối với Phụ kiện nhỏ (Chuột, Bàn phím, Dây cáp):** Tối thiểu **$\ge 10$ sản phẩm** / chuyến.

---

## 4. Quy Trình Phê Duyệt Lệnh Điều Chuyển Hàng Hóa (Controlled Transfer Approval)
- Trợ lý AI khi phát hiện tình trạng mất cân đối tồn kho giữa các chi nhánh sẽ đưa ra đề xuất số lượng điều chuyển kinh tế, chi phí vận tải ước tính và chi nhánh xuất/nhập tối ưu.
- Việc thực thi tạo phiếu xuất - nhập kho điều chuyển đòi hỏi bản ghi Yêu cầu Phê duyệt (`ApprovalRequest`) với mã hành động `create_stock_transfer` (hoặc `transfer_stock`), trạng thái `PENDING`, chờ Thủ kho trưởng và Giám đốc chi nhánh nguồn phê duyệt để đảm bảo tính minh bạch và tránh sai lệch số liệu kho.
