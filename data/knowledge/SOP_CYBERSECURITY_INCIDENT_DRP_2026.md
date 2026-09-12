# QUY TRÌNH ỨNG CỨU SỰ CỐ AN NINH MẠNG, CÔ LẬP RANSOMWARE & PHỤC HỒI DỮ LIỆU THẢM HỌA 2026
**Mã hiệu:** SOP-SEC-DRP-2026  
**Áp dụng:** Khối Vận hành Dịch vụ Kỹ thuật & Trung tâm Điều hành An ninh mạng SOC (`xyz-service`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Phân Cấp Mức Độ Sự Cố An Ninh Mạng Tối Khẩn Cấp (Cyber Emergency Level P0)
1. **Tiêu Chí Định Danh Sự Cố Cấp P0 (Mức Thảm Họa An Ninh Mạng):**
   - Hệ thống máy chủ phát hiện hành vi mã hóa tập tin hàng loạt của mã độc tống tiền (Ransomware).
   - Cơ sở dữ liệu khách hàng hoặc bí mật công nghệ bị xâm nhập trái phép và có dấu hiệu trích xuất dữ liệu ra máy chủ bên ngoài (Data Exfiltration).
   - Tấn công từ chối dịch vụ phân tán (DDoS) vượt ngưỡng lưu lượng băng thông **10.0 Gbps**, làm tê liệt toàn bộ cổng dịch vụ khách hàng trực tuyến.
2. **Kích Hoạt Nhóm Đặc Nhiệm Ứng Cứu Khẩn Cấp (Cyber Incident Response Team - CIRT):**
   - Đội ngũ kỹ sư trực SOC phải kích hoạt báo động đỏ trong vòng **$\le 05$ phút** kể từ thời điểm phát hiện cảnh báo SIEM.
   - Trưởng nhóm An toàn thông tin (Security Lead) tiếp quản quyền chỉ huy kỹ thuật cao nhất trên toàn hệ thống mạng.

---

## 2. Quy Trình Cô Lập Mạng 5 Phút & Nguyên Tắc Không Khởi Động Lại (No-Reboot Rule)
Để ngăn chặn mã độc lây lan sang các máy chủ trong cùng phân đoạn mạng:
1. **Hành Động Cô Lập Mạng Khẩn Cấp Trong 05 Phút:**
   - Lập tức ngắt kết nối cổng Switch vật lý (Port Shutdown) hoặc ngắt toàn bộ liên kết mạng VLAN, vô hiệu hóa card mạng ảo (vNIC) trên nền tảng ảo hóa VMware/Proxmox.
   - Ngắt đường truyền Internet Gateway và ngắt kết nối kênh truyền VPN liên chi nhánh.
2. **NGUYÊN TẮC BẮT BUỘC "TUYỆT ĐỐI KHÔNG KHỞI ĐỘNG LẠI" (Strict No-Reboot Rule):**
   - Kỹ thuật viên hiện trường và quản trị viên hệ thống **nghiêm cấm tuyệt đối hành vi ấn nút nguồn Reset hoặc câu lệnh Reboot máy chủ** khi nghi ngờ bị nhiễm Ransomware.
   - **Cơ sở khoa học và pháp lý:** Việc khởi động lại sẽ xóa sạch toàn bộ dữ liệu lưu trữ tạm thời trong bộ nhớ RAM (Volatile Memory), làm mất dấu vết khóa giải mã (Decryption Key) và bằng chứng số phục vụ công tác giám định pháp y kỹ thuật số (Digital Forensics).
   - Kỹ sư SOC thực hiện trích xuất ảnh bộ nhớ RAM (RAM dump) và bản sao lưu bit-by-bit ổ cứng trước khi thực hiện bất kỳ thao tác phân tích mã độc nào.

---

## 3. Chỉ Tiêu Khôi Phục Dữ Liệu Sau Thảm Họa (Disaster Recovery RTO & RPO Targets)
Khi kích hoạt Kế hoạch Phục hồi Thảm họa (Disaster Recovery Plan - DRP):
1. **Mục Tiêu Thời Gian Phục Hồi Dịch Vụ (RTO - Recovery Time Objective):**
   - Cam kết thời gian khôi phục đưa hệ thống máy chủ và dịch vụ CNTT cốt lõi trở lại hoạt động bình thường: **$\le 4.0$ giờ**.
2. **Mục Tiêu Điểm Phục Hồi Dữ Liệu (RPO - Recovery Point Objective):**
   - Cam kết lượng dữ liệu tối đa chấp nhận bị mất mát (khoảng cách giữa bản backup gần nhất và thời điểm xảy ra sự cố): **$\le 1.0$ giờ**.
   - Được bảo đảm nhờ cơ chế sao lưu liên tục WAL (Write-Ahead Logging) và snapshot tự động hàng giờ của cơ sở dữ liệu PostgreSQL.
3. **Môi Trường Khôi Phục Độc Lập (Air-Gapped Clean Room):**
   - Bản sao lưu phục hồi chỉ được giải nén và khởi động trong môi trường mạng cách ly hoàn toàn (Air-Gapped Clean Room), quét sạch 100% mã độc bằng chữ ký EDR mới nhất trước khi đấu nối lại vào mạng sản xuất.

---

## 4. Báo Cáo Điều Tra Nguyên Nhân Gốc Rễ (RCA) & Kế Hoạch Khắc Phục Lỗ Hổng
1. Trong vòng **48 giờ** kể từ khi khôi phục dịch vụ thành công:
   - Trưởng nhóm Kỹ thuật SOC phải hoàn thiện Báo cáo Phân tích Nguyên nhân Gốc rễ (Root Cause Analysis - RCA).
   - Báo cáo phải chỉ rõ: Vector tấn công ban đầu (Phishing mail, lỗ hổng Zero-day, mật khẩu yếu), danh sách tài khoản bị xâm phạm, mức độ ảnh hưởng dữ liệu và các biện pháp vá lỗ hổng triệt để (Patching & Hardening).
2. Gửi văn bản báo cáo chính thức có chữ ký số của Giám đốc Kỹ thuật cho khách hàng doanh nghiệp kèm kế hoạch nâng cấp an ninh mạng trong vòng 30 ngày tiếp theo.
