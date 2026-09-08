# QUY TRÌNH XỬ LÝ SỰ CỐ HẠ TẦNG ĐÁM MÂY KHẨN CẤP, CAM KẾT THỜI GIAN KHẮC PHỤC MTTR & PHÂN BỔ CHI PHÍ KỸ THUẬT VIÊN 2026
**Mã hiệu:** SOP-OPS-SLA-2026 | **Đơn vị ban hành:** Khối Dịch vụ Kỹ thuật Hạ tầng CNTT XYZ IT Services

---

## 1. Ma Trận Phân Cấp Mức Độ Nghiêm Trọng Của Sự Cố (Incident Severity Matrix)
Mọi phiếu yêu cầu dịch vụ kỹ thuật (`ServiceRequest`) tiếp nhận từ khách hàng hoặc hệ thống giám sát tự động phải được phân cấp theo tiêu chuẩn quốc tế ITIL:

| Cấp độ sự cố | Mô tả kỹ thuật | Cam kết Phản hồi đầu tiên (SLA Response) | Cam kết Khắc phục triệt để (MTTR) | Kỹ năng kỹ sư bắt buộc |
|---|---|---|---|---|
| **Cấp P1 (Khẩn cấp - URGENT)** | Toàn bộ hệ thống máy chủ cơ sở dữ liệu sập, mạng Core bị cô lập, tê liệt giao dịch kinh doanh diện rộng | **<= 15 phút** | **<= 02 giờ** | Chuyên viên Cao cấp / Trưởng nhóm (Senior Network / Senior DBA) |
| **Cấp P2 (Mức cao - HIGH)** | Một chi nhánh mất kết nối dự phòng, suy giảm hiệu năng cơ sở dữ liệu trên 40%, nguy cơ gián đoạn dịch vụ | **<= 30 phút** | **<= 04 giờ** | Kỹ sư Mạng có chứng chỉ CCNP hoặc Quản trị hệ thống Linux |
| **Cấp P3 (Tiêu chuẩn - STANDARD)** | Yêu cầu bảo trì phần cứng định kỳ, cài đặt phần mềm, nâng cấp máy trạm văn phòng cá nhân | **<= 02 giờ** | **Trong vòng 24 giờ** | Kỹ thuật viên phần cứng / IT Support tiêu chuẩn |

---

## 2. Nguyên Tắc Điều Phối Không Gian GIS & Cân Bằng Tải Kỹ Sư (Workload Balancing)
Để đảm bảo chất lượng can thiệp thực địa và sức khỏe lao động của kỹ sư:
1. **Tiêu chuẩn Bán kính Không gian**:
   - Sử dụng thuật toán trắc địa PostGIS (`ST_Distance`) để tính khoảng cách di chuyển thực tế từ tọa độ hiện tại của kỹ thuật viên đến địa chỉ của khách hàng.
   - Đối với sự cố Cấp P1, chỉ ưu tiên kỹ sư trong bán kính di chuyển dưới **10.0 km**.
2. **Ngưỡng Giới Hạn Tải Công Việc (Workload Threshold)**:
   - Kỹ sư đang đảm nhiệm từ **04 công việc đang hoạt động (active tasks)** trở lên hoặc có hệ số sử dụng thời gian (Utilization Rate) vượt quá **80%** được đánh dấu là **QUÁ TẢI (OVERLOADED)**.
   - Thuật toán AI tuyệt đối không tự động gán thêm sự cố mới cho kỹ sư đang quá tải trừ khi có văn bản phê duyệt ngoại lệ từ Trưởng phòng Điều hành Dịch vụ.
3. **Thuật Toán Chấm Điểm Đa Tiêu Chí (Multi-Criteria Scoring)**:
   $$\text{Điểm Tối Ưu} = 0.40 \times S_{\text{khoảng\_cách}} + 0.40 \times S_{\text{tải\_công\_việc}} + 0.20 \times S_{\text{kỹ\_năng}}$$

---

## 3. Định Mức Chi Phí Nhân Công Kỹ Thuật (Labor Cost Rate Schedule)
Chi phí nhân công được tính tự động vào hóa đơn dịch vụ theo định mức giờ công chuẩn hóa:

1. **Bậc Kỹ sư Tiêu chuẩn (Standard IT Support)**:
   - Đơn giá giờ hành chính: **250,000 VND / giờ**.
   - Phạm vi áp dụng: Bảo trì máy trạm, thay thế linh kiện văn phòng, kiểm tra cáp mạng cơ bản.
2. **Bậc Chuyên viên Cao cấp / Kỹ sư Trưởng (Senior Specialist)**:
   - Đơn giá giờ hành chính: **450,000 VND / giờ**.
   - Phạm vi áp dụng: Khắc phục sự cố mạng Core Cisco/Juniper, tối ưu hóa cơ sở dữ liệu PostgreSQL, bảo mật hệ thống.
3. **Hệ Số Khẩn Cấp & Ngoài Giờ (Urgent / After-hours Multiplier)**:
   - Đối với sự cố Cấp P1 diễn ra ngoài giờ hành chính (sau 18:00 hoặc ngày Chủ nhật/Lễ), đơn giá nhân công được nhân hệ số **1.5 lần (150%)**.

---

## 4. Chính Sách Bồi Thường Khi Vi Phạm Cam Kết SLA
1. Nếu thời gian khắc phục sự cố Cấp P1 vượt quá 02 giờ do nguyên nhân chủ quan từ phía đội ngũ kỹ thuật XYZ:
   - Khách hàng được hoàn trả **10% cước phí thuê bao dịch vụ của tháng đó**.
   - Cộng thêm **03 ngày sử dụng dịch vụ giám sát miễn phí**.
2. Toàn bộ biên bản vi phạm SLA phải được hệ thống ghi nhận vào `AuditLog` và gửi cảnh báo trực tiếp đến Giám đốc Điều hành qua Cổng Quản lý `/noibo/`.
