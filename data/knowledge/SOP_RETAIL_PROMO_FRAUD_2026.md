# SOP-RET-PROMO-FRAUD-2026: QUY TRÌNH KIỂM SOÁT GIAN LẬN KHUYẾN MÃI, CHỐNG LẠM DỤNG VOUCHER VÀ CHÍNH SÁCH ƯU ĐÃI NHÂN VIÊN 2026

## 1. MỤC TIÊU VÀ PHẠM VI ÁP DỤNG
Quy định này áp dụng cho toàn thể nhân viên kinh doanh, thu ngân, quản lý chi nhánh và hệ thống bán lẻ đa kênh trực thuộc **ABC Tech Store**. Mục tiêu nhằm ngăn chặn triệt để hành vi đầu cơ trục lợi mã giảm giá, gom hàng bán lẻ để bán buôn, lạm dụng mã ưu đãi nội bộ và gian lận chương trình tích điểm.

## 2. PHÂN LOẠI HÀNH VI GIAN LẬN VÀ NGUYÊN TẮC NHẬN DIỆN HỆ THỐNG
Hệ thống AI và POS tự động kích hoạt trạng thái **Fraud Hold** (Tạm giữ xác minh gian lận) khi phát hiện một trong các dấu hiệu sau:

| Dấu Hiệu Gian Lận | Ngưỡng Kích Hoạt Hệ Thống | Biện Pháp Xử Lý Tức Thì | Thẩm Quyền Giải Tỏa |
| :--- | :--- | :--- | :--- |
| **Gom Đơn Tự Động / Đầu Cơ** | Cùng 1 địa chỉ giao hàng hoặc 1 số điện thoại đặt > 3 đơn cùng SKU trong 15 phút | Tự động tạm giữ toàn bộ đơn, khóa voucher đã áp dụng | Trưởng phòng Kinh Doanh |
| **Tạo Tài Khoản Clone (Voucher New User)** | Cùng Device ID, IMEI thiết bị hoặc dải IP đặt > 2 đơn trong 24 giờ nhận mã chào mừng | Hủy mã giảm giá, chuyển đơn hàng về giá niêm yết | Quản lý Chi nhánh / POS Lead |
| **Gian Lận Tích Điểm Thành Viên** | Tích điểm cho khách hàng vắng mặt, dùng số điện thoại cá nhân của nhân viên quét mã | Tạm đình chỉ tài khoản thành viên, phong tỏa toàn bộ điểm thưởng | Ban Kiểm Soát Nội Bộ (Internal Audit) |
| **Lạm Dụng Chiết Khấu Nhân Viên (Staff Discount)** | Nhân viên mua vượt định ngạch năm hoặc bán lại cho bên thứ ba trong 90 ngày | Thu hồi quyền ưu đãi, yêu cầu bồi hoàn chênh lệch giá | Trưởng phòng Nhân sự & Cố vấn Pháp chế |

## 3. CHÍNH SÁCH CHIẾT KHẤU NỘI BỘ DÀNH CHO NHÂN VIÊN (STAFF DISCOUNT)
Nhân viên chính thức vượt qua thử việc được hưởng chính sách ưu đãi mua sắm thiết bị công nghệ với các điều kiện ràng buộc nghiêm ngặt:
1. **Mức chiết khấu**: Tối đa 15% trên giá niêm yết đối với Phụ kiện và 8% đối với Thiết bị số (Laptop, Điện thoại, Tablet).
2. **Hạn mức số lượng**: Mỗi nhân viên chỉ được mua tối đa **02 thiết bị số và 05 phụ kiện trong một năm dương lịch**.
3. **Quy tắc 90 ngày (90-Day Retention Rule)**:
   - Thiết bị mua bằng ưu đãi nhân viên bắt buộc phải kích hoạt và gắn với tài khoản cá nhân của nhân viên trong tối thiểu **90 ngày kể từ ngày xuất hóa đơn**.
   - Nghiêm cấm mọi hành vi chuyển nhượng, rao bán trên mạng xã hội hoặc giao máy nguyên seal cho bên thứ ba.
   - Nếu phát hiện thiết bị kích hoạt tại địa chỉ ngoài vùng cư trú hoặc bị chuyển nhượng trong vòng 90 ngày, nhân viên sẽ bị **xử lý kỷ luật mức sa thải** và bồi hoàn 100% giá trị ưu đãi đã nhận.

## 4. QUY TRÌNH XỬ LÝ ĐƠN HÀNG BỊ TẠM GIỮ (FRAUD HOLD RELEASE WORKFLOW)
Khi một đơn hàng bị hệ thống đưa vào trạng thái Fraud Hold:
1. **Bước 1**: Nhân viên CSKH/Thu ngân không tự ý hủy đơn hoặc khiếu nại khách hàng gay gắt. Giải thích theo kịch bản: *"Đơn hàng đang trong quy trình đối soát bảo mật tự động nhằm bảo vệ quyền lợi giao dịch an toàn của Quý khách"*.
2. **Bước 2**: Xác minh danh tính khách hàng bằng cuộc gọi video call hoặc yêu cầu chụp mặt trước CCCD/hóa đơn tiện ích nếu đơn hàng thanh toán trước giá trị > 20,000,000 VNĐ.
3. **Bước 3**: Nếu xác nhận là khách hàng thật có nhu cầu hợp lệ, Quản lý chi nhánh tạo phiếu yêu cầu giải tỏa trên hệ thống quản trị với ghi chú minh chứng.
4. **Bước 4**: Thời gian giải tỏa hoặc quyết định hủy đơn gian lận không quá **04 giờ làm việc**.
