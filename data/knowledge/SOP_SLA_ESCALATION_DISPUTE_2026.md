# QUY CHUẨN VẬN HÀNH: MA TRẬN LEO THANG SỰ CỐ SLA & HÒA GIẢI TRANH CHẤP KỸ THUẬT 2026
**Mã hiệu:** SOP-OPS-ESC-2026  
**Áp dụng:** Khối Vận hành Dịch vụ Kỹ thuật & Quản lý Khách hàng Doanh nghiệp (`xyz-service`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Ma Trận Báo Động & Leo Thang 3 Cấp Độ Chủ Động (3-Tier Proactive SLA Escalation)
Để triệt tiêu hoàn toàn nguy cơ vi phạm cam kết thời gian phục hồi dịch vụ (MTTR) đối với các phiếu yêu cầu kỹ thuật (`ServiceRequest`):
1. **Leo Thang Cấp Độ 1 (Tier 1 Escalation - Khi Trôi Qua 50% Thời Hạn SLA):**
   - Kích hoạt khi: Thời gian xử lý thực tế chạm ngưỡng **50% thời hạn cam kết SLA** (ví dụ: Sự cố P1 hạn 2 giờ $\rightarrow$ sau 60 phút chưa có dấu hiệu nghiệm thu).
   - Hành động tự động: Hệ thống AI gửi tin nhắn thông báo cảnh báo màu vàng đến Trưởng nhóm Kỹ thuật (Technical Lead). Tech Lead lập tức can thiệp hỗ trợ kỹ thuật viên gỡ rối cấu hình từ xa (Remote Troubleshooting).
2. **Leo Thang Cấp Độ 2 (Tier 2 Escalation - Khi Trôi Qua 75% Thời Hạn SLA):**
   - Kích hoạt khi: Thời gian xử lý chạm ngưỡng **75% thời hạn SLA** (sau 90 phút đối với sự cố P1).
   - Hành động tự động: Báo động màu cam gửi tới Trưởng phòng Điều hành Dịch vụ (Service Operations Manager). Thuật toán GIS tự động rà soát và đề xuất **điều động thêm 01 kỹ sư cao cấp đang ở bán kính gần nhất $\le 10$ km** đến chi viện trực tiếp tại hiện trường.
3. **Leo Thang Cấp Độ 3 (Tier 3 Escalation - Khi Chạm Ngưỡng 100% Vi Phạm SLA):**
   - Kích hoạt khi: Thời gian xử lý vượt quá **100% thời hạn cam kết SLA**.
   - Hành động tự động: Báo động đỏ (Critical Incident Breach) gửi trực tiếp đến Giám đốc Công nghệ (CTO) và Giám đốc Chăm sóc Khách hàng. Hệ thống tự động khóa trạng thái phiếu, ghi nhận vi phạm vào `AuditLog`, đồng thời kích hoạt chính sách bồi thường hợp đồng (hoàn trả 10% cước phí tháng và tặng voucher dịch vụ).

---

## 2. Quy Trình Hòa Giải & Thẩm Định Tranh Chấp Kỹ Thuật (Technical Dispute Arbitration)
Khi phát sinh mâu thuẫn giữa khách hàng doanh nghiệp và kỹ thuật viên về chất lượng nghiệm thu hoặc nguyên nhân gây lỗi thiết bị:
1. **Thành Lập Hội Đồng Thẩm Định Kỹ Thuật Độc Lập (Independent Technical Review Board):**
   - Trong vòng **24 giờ** kể từ khi tiếp nhận khiếu nại của khách hàng, phòng Quản lý chất lượng thành lập Hội đồng gồm 02 thành viên:
   - 01 Kỹ sư Trưởng chuyên ngành độc lập (không tham gia xử lý phiếu ban đầu).
   - 01 Cán bộ đại diện Bộ phận Pháp chế & Chăm sóc Khách hàng.
2. **Quy Trình Kiểm Tra Lại Hiện Trường (Joint On-Site Re-inspection):**
   - Tiến hành kiểm tra và đo đạc trực tiếp các thông số kỹ thuật trước sự chứng kiến của đại diện khách hàng: Kiểm tra thông mạch cáp mạng bằng máy đo Fluke, đo suy hao tín hiệu quang OTDR, kiểm tra log hệ thống kernel máy chủ.
   - Lập "Biên Bản Thẩm Định Kỹ Thuật Liên Tịch" ghi nhận nguyên nhân khách quan/chủ quan.
3. **Nguyên Tắc Xử Lý Có Lợi Nhất Cho Khách Hàng (Customer-Centric Resolution):**
   - Nếu kết quả thẩm định kỹ thuật cho thấy sự cố nằm ở vùng giáp ranh không thể phân định rõ ràng giữa lỗi phần mềm của khách hàng và lỗi hạ tầng của XYZ:
   - Áp dụng nguyên tắc ưu tiên giải quyết có lợi cho khách hàng: Miễn phí toàn bộ chi phí nhân công can thiệp và cung cấp gói bảo hành theo dõi đặc biệt trong 30 ngày tiếp theo.

---

## 3. Kiểm Soát Phê Duyệt Lệnh Điều Động Chi Viện Hiện Trường (HITL Dispatch Approval)
1. Khi thuật toán phát hiện sự cố chạm mốc Tier 2 Escalation (75% SLA), Trợ lý AI tạo bản ghi Yêu cầu Phê duyệt (`ApprovalRequest`) với mã hành động `dispatch_backup_engineer`, chỉ rõ danh tính kỹ sư chi viện, khoảng cách GIS và chi phí phát sinh.
2. Trưởng phòng Dịch vụ ký duyệt điện tử trên cổng `/noibo/approvals/` để xuất lệnh điều động chính thức.
