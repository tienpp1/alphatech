# Kế hoạch sửa phát hiện kiểm thử ngày 11/10/2026

Phạm vi: 36 phát hiện F01–F36 trong `output/live_audit_20261011/BAO_CAO_KIEM_THU.md`.
Không thay đổi cấu trúc hoặc tiến độ sổ 97 mục. Không reset database, sửa lịch sử
migration, tự hợp nhất dữ liệu local vào Neon hoặc ghi đè thay đổi có sẵn.

## Thứ tự thực hiện

1. Nghiệp vụ và bảo mật: F01, F04, F05, F14, F27–F29, F32–F33, F35.
   Phê duyệt phải dùng cùng dịch vụ chuyển trạng thái/hoàn kho; dữ liệu đầu vào
   không hợp lệ không được gây 500; chỉ nhân sự hợp lệ xuất hiện trong chat.
2. Sự thật của AI: F02–F03, F06–F09, F15–F17. Không thay kết quả đo yếu bằng
   số giả; phân biệt ước tính, nguồn chưa duyệt và dữ liệu đã ghi nhận.
3. Forecast/recommendation: F10–F13, F18, F20–F24. Hiển thị đúng thời gian,
   baseline, freshness và phạm vi action; không che run kém hoặc phát minh SLA.
4. Trải nghiệm: F19, F25–F26, F30–F31, F34. Lịch sử hội thoại phải thật sự
   tải nội dung; form không nhân đôi nghiệp vụ; lỗi GPS không dùng tọa độ kém.
5. Tồn kho F36: chủ dự án đã đồng ý bật strict. Đã đối chiếu read-only 44
   sản phẩm × 3 chi nhánh trên Neon, không thiếu cặp hoặc số dư âm. Chỉ thay
   cấu hình fulfillment; không sửa tồn kho production để làm test xanh.

## Kiểm chứng

- Regression mới cho từng lỗi, sau đó chạy các nhóm hiện có bị ảnh hưởng trên
  PostgreSQL/PostGIS test riêng bằng `config.settings_evidence_test`.
- Kiểm tra Django và migration drift; không dùng database nghiệp vụ làm test.
- Kiểm tra JavaScript và browser với dữ liệu test, không gọi đó là UAT
  production nếu source chưa phát hành.
- Giữ log lỗi đầu tiên và nguyên nhân sửa trước khi chạy lại.

## Cổng cần bên ngoài

F02: chủ dự án chọn DETERMINISTIC / NO_API_KEY, không bật Gemini live hoặc
semantic embedding trả phí. F10–F11: giữ dữ liệu lịch sử học thuật, công khai
R² âm/kém baseline; không tạo giao dịch giả để nâng điểm. F25: chủ dự án cho
phép ảnh AI; dùng một minh họa nhóm thiết bị có disclosure, không giả làm ảnh
chụp thật cho 44 SKU. F36: strict đã được lưu trên Render, release898e0fb đã LIVE
ngày11/10; chưa có UAT đặt/hủy đơn strict trên bản mới. Test tự động/browser local
không thay thế UAT trên thiết bị production.

Kết quả và giới hạn: AUDIT_REPAIR_RESULTS_2026_10_11.md. Không sửa sổ 97.
