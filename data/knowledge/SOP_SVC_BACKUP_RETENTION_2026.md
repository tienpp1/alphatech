# SOP-SVC-BACKUP-RETENTION-2026: QUY CHUẨN CHIẾN LƯỢC SAO LƯU 3-2-1-1, LƯU TRỮ BẤT BIẾN WORM VÀ DIỄN TẬP PHỤC HỒI ĐỊNH KỲ 2026

## 1. MỤC TIÊU VÀ PHẠM VI ÁP DỤNG
Quy định này áp dụng cho toàn bộ các cụm cơ sở dữ liệu khách hàng, máy chủ ứng dụng và hạ tầng lưu trữ doanh nghiệp do **XYZ IT Technical Services** vận hành và bảo trì. Mục tiêu là đảm bảo dữ liệu luôn toàn vẹn, khả dụng và có khả năng phục hồi hoàn toàn trước các cuộc tấn công mã độc tống tiền (Ransomware) hoặc thảm họa thiên tai.

## 2. CHIẾN LƯỢC SAO LƯU TIÊU CHUẨN 3-2-1-1
Hệ thống sao lưu bắt buộc tuân thủ mô hình dự phòng 3-2-1-1 nâng cao:
1. **3 Bản Sao Dữ Liệu**: Gồm 01 bản dữ liệu chính (Primary Production) và tối thiểu 02 bản sao lưu dự phòng (Backup Copies).
2. **2 Loại Phương Tiện Khác Nhau**: Sử dụng tối thiểu 02 loại công nghệ lưu trữ vật lý tách biệt (vd: Ổ đĩa SAN tốc độ cao và Đám mây Object Storage S3).
3. **1 Bản Sao Lưu Ngoại Vi (Offsite / Different Region)**: Đặt tại trung tâm dữ liệu thứ hai cách xa trung tâm chính tối thiểu **50 km** để phòng ngừa thảm họa diện rộng.
4. **1 Bản Sao Lưu Bất Biến (Immutable Storage - WORM)**:
   - Áp dụng cơ chế **Write Once, Read Many (WORM)** với chính sách khóa Object Lock không thể sửa đổi hoặc xóa bỏ trước hạn, kể cả bởi tài khoản Super Admin/Root.
   - Ngăn chặn triệt để trường hợp mã độc Ransomware xâm nhập chiếm quyền quản trị và mã hóa luôn cả file backup.

## 3. LỊCH TRÌNH SAO LƯU VÀ VÒNG ĐỜI LƯU TRỮ (RETENTION POLICY)

| Tần Suất Sao Lưu | Loại Sao Lưu | Thời Gian Lưu Trữ (Retention Period) | Mục Tiêu RPO Cam Kết |
| :--- | :--- | :--- | :--- |
| **Hàng Giờ (Hourly)** | Incremental Snapshot | Lưu trữ trong **24 giờ gần nhất** | RPO ≤ 1.0 giờ |
| **Hàng Ngày (Daily)** | Differential / Synthetic Full | Lưu trữ trong **30 ngày** | RPO ≤ 24 giờ |
| **Hàng Tháng (Monthly)** | Full Backup Archive | Lưu trữ trong **12 tháng** | Bản sao lưu đối soát cuối tháng |
| **Hàng Năm (Yearly)** | Immutable Deep Cold Archive | Lưu trữ tối thiểu **05 năm** | Phục vụ kiểm toán tài chính và pháp lý |

## 4. QUY TRÌNH DIỄN TẬP PHỤC HỒI DỮ LIỆU ĐỊNH KỲ (DISASTER RECOVERY DRILL)
Một bản sao lưu không có giá trị nếu chưa được kiểm chứng khả năng phục hồi:
1. **Tần suất diễn tập**: Định kỳ **mỗi tháng một lần (Monthly Recovery Drill)** vào tuần đầu tiên của tháng.
2. **Môi trường diễn tập biệt lập**: Thực hiện phục hồi toàn diện trên môi trường Sandbox hoàn toàn cách ly mạng với Production để đo lường chính xác thời gian khôi phục (Recovery Time).
3. **Tiêu chuẩn nghiệm thu diễn tập**:
   - Dữ liệu phục hồi thành công 100% không bị lỗi checksum (Hash verification SHA-256).
   - Thời gian phục hồi thực tế không được vượt quá **RTO cam kết (≤ 4.0 giờ đối với hệ thống trọng yếu)**.
   - Báo cáo kết quả diễn tập gửi cho Giám đốc Dịch vụ và Khách hàng trong vòng **24 giờ** sau khi hoàn thành.
