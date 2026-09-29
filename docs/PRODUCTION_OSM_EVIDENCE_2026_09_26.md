# Bằng chứng tìm địa chỉ OSM trên production — 26/09/2026

## Phạm vi

- Deployment: `https://alphatech-26uv.onrender.com`
- Render deploy đang live tại thời điểm kiểm tra: `dep-daib93fqj5pc739cq1n0`
- Commit deployment do Render công bố: `4fd8ee47417a87d2a449ef0f5e3198b8977a6840`
- Bề mặt: trang `/chi-nhanh/` và POST CSRF-protected tới `/chi-nhanh/tim-dia-diem/`.

## Kết quả thực tế

Truy vấn địa điểm công khai `Chợ Bến Thành, Thành phố Hồ Chí Minh` trả HTTP
200 và hai kết quả OSM/Nominatim, trong đó có các tọa độ:

- `10.7725301, 106.6980365`
- `10.7726204, 106.6992917`

Payload có attribution của OpenStreetMap/Nominatim. Kiểm tra này chứng minh
đường tìm địa chỉ trên deployment đã gọi được provider và trả kết quả thật;
không chứng minh SLA/uptime của dịch vụ công cộng, độ chính xác mọi địa chỉ,
GPS thiết bị hay tuyến đường có giao thông trực tiếp.

## Ranh giới

- Không gửi dữ liệu cá nhân; chỉ dùng tên địa điểm công khai.
- Không lưu hoặc công bố token/secret.
- GPS thiết bị thuộc Browser Geolocation và vẫn cần người dùng cấp quyền trên
  thiết bị thật; OSM không thể thay thế phép thử đó.
