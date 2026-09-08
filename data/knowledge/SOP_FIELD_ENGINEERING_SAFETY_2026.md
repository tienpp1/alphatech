# QUY CHUẨN VẬN HÀNH: AN TOÀN KỸ THUẬT HIỆN TRƯỜNG, CHỨNG CHỈ NGHỀ & BẢO MẬT THÔNG TIN 2026
**Mã hiệu:** SOP-OPS-ENG-2026  
**Áp dụng:** Đội ngũ Kỹ sư Hiện trường & Điều phối Dịch vụ Kỹ thuật (`xyz-service`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Ma Trận Kỹ Năng & Chứng Chỉ Kỹ Thuật Bắt Buộc (Technician Certification Matrix)
Kỹ thuật viên chỉ được phép nhận phiếu phân công (Dispatch) khi có chứng chỉ phù hợp với phân loại sự cố:

| Lĩnh Vực Kỹ Thuật | Yêu Cầu Chứng Chỉ Bắt Buộc | Cấp Độ Sự Cố Cho Phép Đảm Nhiệm |
|---|---|---|
| **Hệ Thống Mạng Doanh Nghiệp & Định Tuyến** | `CCNA` (Cisco Certified) hoặc `JNCIA` | P1 (Khẩn cấp), P2 (Cao), P3 (Tiêu chuẩn) |
| **Máy Chủ Doanh Nghiệp & Trung Tâm Dữ Liệu (Server / Datacenter)** | `CompTIA Server+`, `RedHat RHCSA` hoặc `MCSE` | P1, P2 |
| **Cáp Quang & Hạ Tầng Viễn Thông Tốc Độ Cao** | Chứng chỉ `FOA (Fiber Optic Association)` | P1, P2 |
| **Sửa Chữa Phần Cứng / Hàn Vi Mạch Phòng Sạch** | `IPC-A-610` hoặc Chứng chỉ Hãng (Apple ACMT / Dell DCSE) | P2, P3 |
| **Bảo Trì Máy Tính Văn Phòng & Thiết Bị Ngoại Vi** | `CompTIA A+` hoặc Tốt nghiệp Cao đẳng CNTT | P3, P4 |

---

## 2. Định Mức Tải Công Việc & Tuân Thủ Giới Hạn Giờ Làm Thêm (Labor & Overtime Compliance)
Để đảm bảo an toàn lao động và chất lượng dịch vụ:
1. **Giới hạn Phiếu Công Việc Đồng Thời (Concurrent Active Tickets):**
   - Mỗi kỹ thuật viên không được phân công quá **03 phiếu sự cố đang xử lý đồng thời** (`active_tasks <= 3`). Nếu vượt quá, hệ thống đánh dấu kỹ thuật viên ở trạng thái quá tải (Overloaded) và loại trừ khỏi thuật toán tự động điều phối.
2. **Hạn Mức Giờ Làm Thêm (Overtime Cap) Theo Luật Lao Động:**
   - Số giờ làm thêm không được vượt quá **4.0 giờ / ngày** và không quá **40.0 giờ / tháng**.
3. **Phụ Cấp Sự Cố Khẩn Cấp Ban Đêm & Môi Trường Nguy Hiểm:**
   - **Hệ số ca đêm / ngày nghỉ (22:00 - 06:00):** Nhân **1.5 lần** so với đơn giá giờ công tiêu chuẩn (ví dụ: Kỹ sư bậc tiêu chuẩn 250,000 VND/giờ $\rightarrow$ 375,000 VND/giờ).
   - **Phụ cấp rủi ro phòng máy chủ / điện áp cao / môi trường nguy hiểm:** Cộng thêm **200,000 VND / ca xử lý**.

---

## 3. Quy Trình Bảo Mật Thông Tin & Toàn Vẹn Dữ Liệu Khách Hàng (ISO 27001 Compliance)
Khi thực hiện can thiệp kỹ thuật tại hiện trường hoặc tiếp nhận thiết bị lưu trữ của khách hàng:
1. **Thỏa Thuận Bảo Mật Thông Tin (Non-Disclosure Agreement - NDA):**
   - Kỹ thuật viên bắt buộc phải yêu cầu khách hàng đại diện ký biên bản cam kết bảo mật trước khi mở vỏ máy chủ hoặc truy cập quyền quản trị hệ điều hành.
2. **Quy Tắc Giám Sát Kép (Double-Custody Sign-Off):**
   - Mọi thao tác tháo dỡ ổ cứng (HDD, SSD), thiết bị lưu trữ SAN/NAS hoặc sao lưu dữ liệu máy chủ bắt buộc phải có sự chứng kiến và ký xác nhận của 02 người: Kỹ thuật viên phụ trách và Cán bộ chuyên trách CNTT của khách hàng.
   - Nghiêm cấm tuyệt đối việc cắm thiết bị lưu trữ ngoài cá nhân (USB, ổ cứng di động chưa kiểm dịch) vào hệ thống máy chủ khách hàng.
