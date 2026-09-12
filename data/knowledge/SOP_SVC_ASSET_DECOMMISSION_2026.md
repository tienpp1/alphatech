# SOP-SVC-ASSET-DECOMMISSION-2026: QUY TRÌNH TIÊU HỦY DỮ LIỆU SỐ VÀ THANH LÝ THIẾT BỊ LƯU TRỮ THEO CHUẨN NIST SP 800-88 2026

## 1. MỤC TIÊU VÀ PHẠM VI ÁP DỤNG
Quy định này áp dụng cho toàn bộ thiết bị phần cứng lưu trữ dữ liệu (Ổ cứng cơ HDD, ổ cứng thể rắn SSD NVMe/SATA, băng từ Tape, thẻ nhớ máy chủ) hết vòng đời sử dụng (End-of-Life) hoặc bàn giao thanh lý tại **XYZ IT Technical Services**. Mục tiêu nhằm ngăn ngừa 100% nguy cơ rò rỉ dữ liệu mật của khách hàng và doanh nghiệp theo tiêu chuẩn quốc tế **NIST SP 800-88 Rev. 1**.

## 2. BA PHƯƠNG PHÁP XÓA DỮ LIỆU THEO TIÊU CHUẨN NIST SP 800-88
Tùy thuộc vào cấp độ nhạy cảm của dữ liệu lưu trữ, kỹ sư an ninh thông tin áp dụng một trong ba cấp độ xử lý:

| Cấp Độ Xử Lý | Định Nghĩa Kỹ Thuật | Phương Pháp Thực Hiện Cho HDD | Phương Pháp Thực Hiện Cho SSD |
| :--- | :--- | :--- | :--- |
| **Cấp 1: Clear (Xóa logic)** | Ghi đè toàn bộ vùng nhớ bằng phần mềm, bảo đảm không thể khôi phục bằng công cụ thông thường | Ghi đè 1 lượt bằng ký tự số 0 (Zero-fill) | Lệnh ATA Secure Erase toàn bộ block |
| **Cấp 2: Purge (Khử từ / Tẩy sạch)** | Dữ liệu không thể phục hồi ngay cả khi sử dụng kỹ thuật phòng thí nghiệm tiên tiến | Khử từ bằng máy Degausser với cường độ từ trường **≥ 10,000 Gauss** | Kích hoạt Cryptographic Erase (tiêu hủy khóa mã hóa phần cứng AES-256) |
| **Cấp 3: Destroy (Phá hủy vật lý)** | Phá hủy cấu trúc cơ học của phương tiện lưu trữ hoàn toàn | Khoan thủng đĩa từ (Drilling) hoặc uốn cong phiến đĩa | **Nghiền nát vật lý (Physical Shredding) thành hạt vụn kích thước < 2mm** |

## 3. QUY TRÌNH TIÊU HỦY VÀ GIÁM SÁT HIỆN TRƯỜNG
1. **Kiểm kê đối soát Serial Number**: Trước khi đưa vào khu vực tiêu hủy, quét mã vạch đối soát Serial/Asset Tag từng ổ cứng khớp 100% với danh mục phê duyệt thanh lý.
2. **Khu vực an ninh có camera giám sát**: Quá trình khử từ và nghiền nát vật lý bắt buộc thực hiện trong phòng an ninh có camera ghi hình độ phân giải cao lưu trữ tối thiểu **90 ngày**.
3. **Sự hiện diện của các bên giám sát**: Quá trình tiêu hủy bắt buộc có mặt của 03 bên:
   - Kỹ sư phụ trách bảo mật hệ thống thông tin.
   - Đại diện Ban Giám đốc An toàn Thông tin (CISO Office).
   - Đại diện hợp pháp của Khách hàng sở hữu dữ liệu (nếu có yêu cầu trong hợp đồng SLA).

## 4. CHỨNG CHỈ TIÊU HỦY DỮ LIỆU (CERTIFICATE OF DATA DESTRUCTION)
Sau khi hoàn tất quy trình phá hủy dữ liệu:
- Đơn vị kỹ thuật xuất bản **Chứng chỉ Tiêu hủy Dữ liệu Số (Certificate of Data Destruction)** ghi rõ danh sách Serial thiết bị, phương pháp tiêu hủy đã áp dụng, ngày giờ và chữ ký số của CISO.
- Thiết bị sau khi nghiền nát được bàn giao cho đơn vị tái chế rác thải điện tử có thẩm quyền.
