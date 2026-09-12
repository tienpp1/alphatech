# SOP-SVC-CHANGE-MANAGEMENT-2026: QUY TRÌNH QUẢN LÝ THAY ĐỔI HỆ THỐNG CNTT (ITIL CAB & EMERGENCY CHANGE PROTOCOL 2026)

## 1. MỤC TIÊU VÀ PHẠM VI ÁP DỤNG
Quy định này áp dụng cho toàn bộ kỹ sư hệ thống, kỹ sư DevOps, quản trị cơ sở dữ liệu và quản lý kỹ thuật của **XYZ IT Technical Services**. Mục tiêu nhằm đảm bảo 100% các thay đổi trên môi trường Production (cấu hình mạng, hạ tầng đám mây, bản vá phần mềm, migration database) được kiểm soát rủi ro, không gây gián đoạn SLA của khách hàng.

## 2. PHÂN LOẠI CÁC CẤP ĐỘ THAY ĐỔI (CHANGE CLASSIFICATION)

| Loại Thay Đổi | Định Nghĩa Nghiệp Vụ | Yêu Cầu Phê Duyệt | Thời Gian Đệ Trình Trước |
| :--- | :--- | :--- | :--- |
| **Standard Change** (Thay đổi tiêu chuẩn) | Thay đổi định kỳ có rủi ro cực thấp, đã có quy trình thao tác chuẩn tự động (vd: gia hạn SSL định kỳ, xoay vòng log, cập nhật bản vá OS thứ yếu) | Tech Lead phê duyệt trước | Đệ trình trước 04 giờ |
| **Normal Change** (Thay đổi thông thường) | Thay đổi kiến trúc, nâng cấp phiên bản cơ sở dữ liệu, điều chỉnh cấu hình tường lửa Firewall, triển khai release phần mềm mới | **Hội đồng Thẩm định Thay đổi (CAB - Change Advisory Board)** họp duyệt | Đệ trình trước **48 giờ** |
| **Emergency Change** (Thay đổi khẩn cấp) | Bản vá nóng (Hotfix) khắc phục sự cố nghiêm trọng cấp độ P0/P1 hoặc lổ hổng Zero-Day đang bị tấn công | **Giám đốc Công nghệ (CTO) hoặc Chỉ huy Sự cố (Incident Commander)** phê duyệt tức thì | Kích hoạt ngay lập tức |

## 3. CÁC ĐIỀU KIỆN TIÊN QUYẾT BẮT BUỘC TRƯỚC KHI TRIỂN KHAI (CHANGE GATES)
Mọi yêu cầu thay đổi (RFC - Request for Change) dù ở cấp độ nào đều bắt buộc phải thỏa mãn 3 điều kiện tiên quyết:
1. **Kiểm thử môi trường Staging đạt 100%**: Bản cập nhật hoặc script migration đã được chạy thử nghiệm thành công hoàn toàn trên môi trường mô phỏng (Staging/Sandbox) mà không phát sinh lỗi ngoại lệ.
2. **Kế hoạch Rollback chi tiết**: Phải có kịch bản hoàn nguyên (Rollback Procedure) bằng văn bản/script rõ ràng. Thời gian thực thi Rollback tối đa không được vượt quá **15 phút**.
3. **Sao lưu dự phòng tức thời (Pre-change Snapshot)**: Bắt buộc kích hoạt tạo snapshot dữ liệu và bản sao lưu cấu hình ngay trước thời điểm tiến hành thay đổi.

## 4. KHUNG GIỜ CẤM THAY ĐỔI (CHANGE FREEZE WINDOW)
Nghiêm cấm triển khai các thay đổi thuộc nhóm Normal Change trong các khung thời gian sau (trừ trường hợp Emergency Change được phê duyệt đặc cách):
- **Chiều Thứ Sáu sau 17:00** và toàn bộ các ngày cuối tuần (Thứ Bảy, Chủ Nhật).
- Các ngày nghỉ Lễ, Tết theo quy định của Nhà nước.
- **Tuần cao điểm quyết toán tài chính & bán hàng**: 03 ngày làm việc cuối cùng của mỗi tháng và tuần lễ siêu khuyến mãi (Black Friday, Tết Nguyên Đán).
