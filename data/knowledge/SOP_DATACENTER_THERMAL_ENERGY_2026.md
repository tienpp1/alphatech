# QUY CHUẨN VẬN HÀNH: MÔI TRƯỜNG NHIỆT ĐỘ PHÒNG SERVER, TIÊU CHUẨN XANH & DỰ PHÒNG NGUỒN ĐIỆN 2026
**Mã hiệu:** SOP-OPS-DC-2026  
**Áp dụng:** Khối Quản trị Trung tâm Dữ liệu Datacenter & Cơ sở Hạ tầng IT (`xyz-service`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Tiêu Chuẩn Môi Trường Nhiệt Độ & Độ Ẩm Hành Lang Lạnh (Cold Aisle Thermal Guidelines)
Tuân thủ nghiêm ngặt tiêu chuẩn quốc tế ASHRAE TC 9.9 về vận hành phòng máy chủ doanh nghiệp:
1. **Dải Nhiệt Độ & Độ Ẩm Tiêu Chuẩn:**
   - **Nhiệt độ cửa gió hành lang lạnh (Cold Aisle Air Temp):** Duy trì ổn định từ **18.0°C đến 24.0°C**.
   - **Độ ẩm tương đối (Relative Humidity):** Duy trì từ **45.0% đến 55.0%** (ngăn chặn tĩnh điện khi độ ẩm quá thấp và ngăn đọng sương rỉ sét khi độ ẩm quá cao).
2. **Các Ngưỡng Cảnh Báo Nhiệt Độ Quá Tải:**
   - **Ngưỡng Cảnh báo Cấp 1 (Warning):** Khi nhiệt độ tại bất kỳ điểm cảm biến nào vượt quá **27.0°C** trong 05 phút liên tục. Kỹ sư trực ca phải kiểm tra dàn lạnh điều hòa chính xác CRAC.
   - **Ngưỡng Báo động Khẩn cấp Cấp 2 (Critical Overheat):** Khi nhiệt độ vượt quá **30.0°C**. Tự động khởi động hệ thống điều hòa dự phòng N+1 ở công suất 100%.
   - **Ngưỡng Ngắt Điện Tự Động Khẩn Cấp (Emergency Power Off - EPO Threshold):** Khi nhiệt độ chạm ngưỡng **35.0°C** và hệ thống làm mát mất kiểm soát. Hệ thống tự động gửi lệnh ngắt điện khẩn cấp đến các tủ rack máy chủ thứ cấp nhằm ngăn chặn nguy cơ cháy nổ linh kiện bán dẫn và nguy cơ chập cháy hỏa hoạn.

---

## 2. Tiêu Chuẩn Dự Phòng Nguồn Điện N+1 & Máy Phát Điện Diesel Khẩn Cấp
Để cam kết chỉ số sẵn sàng Uptime dịch vụ máy chủ đạt mức **99.98% (Chuẩn Tier III Datacenter)**:
1. **Kiến Trúc Hai Nguồn Điện Song Song Độc Lập (Dual-Feed Power Distribution):**
   - Mỗi tủ rack máy chủ bắt buộc phải đấu nối song song 2 đường nguồn cấp PDU độc lập:
   - **Nguồn A (Source A):** Điện lưới quốc gia EVN thông qua hệ thống bộ lưu điện UPS công nghiệp online double-conversion.
   - **Nguồn B (Source B):** Điện cấp từ hệ thống UPS dự phòng thứ hai chạy song song độc lập.
   - Máy chủ sử dụng nguồn cấp kép (Redundant Power Supply - RPS), đảm bảo nếu một nguồn bị ngắt đột ngột, nguồn còn lại gánh 100% tải mà không làm sập hệ thống (Zero Downtime).
2. **Quy Chuẩn Chuyển Đổi Nguồn Máy Phát Điện Diesel Khẩn Cấp (ATS Generator Transfer):**
   - Khi mất điện lưới diện rộng: Hệ thống tủ chuyển nguồn tự động (Automatic Transfer Switch - ATS) lập tức kích hoạt máy phát điện Diesel công nghiệp.
   - **Cam kết thời gian hòa điện:** Máy phát điện phải khởi động, ổn định tần số điện áp và hòa điện hoàn tất trong vòng **$\le 15$ giây**.
   - Hệ thống UPS chịu tải liên tục trong 15 giây chuyển mạch này, đảm bảo không có bất kỳ xung điện hay gián đoạn vi mô nào xảy ra.
   - Dự trữ nhiên liệu dầu Diesel tại chỗ đảm bảo máy phát chạy liên tục tối thiểu **72 giờ** không cần tiếp nhiên liệu.

---

## 3. Quy Trình Bảo Trì & Thử Tải Máy Phát Định Kỳ Hàng Tháng (Blackout Generator Drill)
1. Vào ngày Chủ nhật đầu tiên của mỗi tháng từ 02:00 đến 04:00 sáng:
   - Đội ngũ kỹ sư cơ điện tiến hành diễn tập cúp điện lưới giả lập (Simulated Blackout Drill) để kiểm tra độ nhạy của bộ chuyển nguồn ATS và tải máy phát điện.
   - Kết quả diễn tập được số hóa và lưu trữ tại nhật ký vận hành Datacenter trên cổng `/noibo/telemetry/`.
