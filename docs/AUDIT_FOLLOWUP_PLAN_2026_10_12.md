# Kế hoạch đóng phần còn lại của live audit — 12/10/2026

Tiếp nối F01–F36; không sửa cấu trúc hoặc tiến độ sổ97, không reset database.
Các quyết định deterministic/no-key, forecast học thuật lịch sử, Render Free,
không worker trả phí, Local Storage và ảnh AI có disclosure vẫn được giữ.

## Các nhóm thực hiện

1. Tái hiện và sửa lỗi nguồn còn sót: email liên hệ sai phải bị chặn trước ghi;
   quyền dịch vụ approval phải chặn inactive/Google-linked cả ở tầng service;
   chuyển trạng thái đơn không hợp lệ phải có lỗi an toàn thay500; recommendation
   reject không ghi đè ACCEPTED/EXPIRED; monitor forecast không gọi gap-filled
   zero là quan sát thật hoặc dùng cadence mutable thay provenance của run.
2. Checkout: đổi cách nhận phải cập nhật tổng từ cart API server-side, chặn gửi
   khi tổng chưa xác nhận và có cách thử lại; GPS phải kiểm tọa độ/sai số, không
   dùng giá trị cũ sau lỗi hoặc callback hết hiệu lực. Không đổi giá/tồn kho thật.
3. Kiểm thử regression độc lập trên DB test disposable; giữ các lỗi trước sửa,
   chạy nhóm ảnh hưởng, check/drift/security/CI theo rủi ro. Không nới/skip test.
4. Push/deploy bản sửa sau kiểm chứng; đối chiếu đúng SHA với CI và Render Free.
5. UAT có kiểm soát: đơn TEST không giao/không thu tiền → reservation → approval
   → thông báo đúng khách → cancellation trả reservation đúng một lần; email
   riêng tới account/form và người dùng xác nhận hai inbox. Không sửa đơn thật.
6. Browser responsive và branch finder với vị trí chọn công khai; GPS thật cần
   người dùng thao tác trên thiết bị và xác nhận, không mô phỏng rồi gọi là UAT.

## Điều kiện và giới hạn

Chủ dự án đồng ý kiểm hai inbox TEST và GPS điện thoại trong lượt này. Tác động
production phải gắn đúng mãTEST, lưu snapshot/audit và khôi phục reservation;
đơn TEST giữ lịch sử CANCELLED, không xóa lịch sử audit. Bấm checkout có chấp nhận
điều khoản cần xác nhận ở thời điểm hành động. Không gửi khóa/mật khẩu vào chat.

Nếu thiếu bằng chứng inbox/thiết bị hoặc môi trường test không hoạt động, ghi
đúng phần bị chặn và tiếp tục các nhóm độc lập. Không gọi chứng chỉ/SLA/COGS,
chất lượng XGBoost hoặc năng lực Gemini live đã đạt chỉ vì regression xanh.
