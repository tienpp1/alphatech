# Đợt 40 — Nghiệm thu Hệ thống Bản đồ GIS Không gian, Định vị GPS và Điều phối Hiện trường

Ngày chốt: 22/09/2026.
Phạm vi: Cổng 56 & 57 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 56: Xác nhận tra cứu địa điểm Nominatim và phòng hộ API**:
  - Cơ chế tìm kiếm địa chỉ công khai tại `/chi-nhanh/tim-dia-diem/` với PostgreSQL advisory lock (`GATE_ID = 714830219`), bảo vệ giới hạn tần suất gọi upstream Nominatim.
  - Bộ đệm cache 24h và thời gian cooldown 1.1s chống quá tải.
  - Kiểm thử đầy đủ các ca: thiếu ký tự (400), bận dịch vụ (429 với `Retry-After: 2`), lỗi dịch vụ upstream (503), và chuẩn hóa kết quả an toàn chỉ gồm tọa độ số và nhãn địa danh đã vệ sinh.
- **Mục 57: Xác nhận ứng xử định vị GPS trên thiết bị thực tế & suy biến độ chính xác**:
  - Triển khai và kiểm thử xử lý đầy đủ các mã lỗi chuẩn của HTML5 Geolocation API:
    - Mã 1: *“Bạn chưa cho phép truy cập vị trí.”* (Permission Denied).
    - Mã 2: *“Thiết bị chưa xác định được vị trí.”* (Position Unavailable).
    - Mã 3: *“Lấy vị trí quá thời gian chờ.”* (Timeout).
  - Phân cấp thông báo sai số độ chính xác (Accuracy tiers):
    - Chuẩn (sai số $\le 100$ m): Hiển thị sai số ước tính và vòng tròn xanh lá.
    - Cảnh báo suy biến (sai số $> 100$ m): Cảnh báo vị trí gần đúng, hướng dẫn người dùng thử ngoài trời hoặc kéo chấm xanh trên bản đồ.
    - Thiếu thông tin sai số: Yêu cầu người dùng kiểm tra chấm vị trí trước khi dẫn đường.
  - Bổ sung test tự động trong `tests/test_public_branch_finder.py` chạy trực tiếp Node.js kiểm chứng các hàm thuần `accuracyMessage`, `distanceKm`, `inRadius`, `validPoint`.
- **Nghiệm thu Trực quan 3 Giao diện Bản đồ GIS (Live Browser Verification)**:
  - **Trang Tìm chi nhánh công khai (`/chi-nhanh/`)**: Hiển thị bản đồ Leaflet, 3 điểm ghim chi nhánh, tìm kiếm địa chỉ và bộ lọc bán kính đường chim bay (1–10 km) kèm vòng tròn tím.
  - **Bản đồ GIS Bán lẻ (`/retail/gis/`)**: Hiển thị mạng lưới 3 cửa hàng flagship, 85 vị trí khách hàng phân bổ theo phân khúc (VIP, Tiềm năng, Mới) với cơ chế bảo vệ PII theo quyền RBAC (`gis.view_customer_locations`).
  - **Bản đồ GIS Vận hành Dịch vụ (`/services/gis/`)**: Hiển thị 10 kỹ thuật viên hiện trường cùng vòng tròn bán kính bao phủ dịch vụ (coverage circles), 120 phiếu yêu cầu sự cố phân cấp màu theo mức độ ưu tiên (P1 Khẩn cấp đến P4 Thấp) và thuật toán gợi ý điều phối kỹ thuật viên gần nhất (`get_nearby_technicians_for_ticket`).

---

## 2. Kết quả Kiểm chứng Tự động

```powershell
python manage.py test tests.test_gis_spatial tests.test_gis_reference_distances tests.test_gis_security tests.test_public_branch_finder tests.test_public_geocoding --keepdb
```

```text
Ran 27 tests in 46.283s
OK
System check identified no issues (0 silenced).
```

- **27/27 tests đạt PASS 100%**, bao gồm:
  - 8 ca kiểm thử PostGIS ST_DWithin, ST_Distance, Bounding Box, GeoJSON serialization (`test_gis_spatial.py`).
  - 3 ca kiểm chứng cự ly giải tích WGS84 và tài liệu GeographicLib độc lập (`test_gis_reference_distances.py`).
  - 5 ca bảo vệ đa người thuê Workspace Isolation và kiểm soát quyền PII khách hàng (`test_gis_security.py`).
  - 5 ca kiểm thử giao diện tìm kiếm chi nhánh, mã lỗi GPS và phân cấp sai số (`test_public_branch_finder.py`).
  - 6 ca kiểm thử rate limit, cache cooldown, bảo vệ CSRF và phòng hộ upstream geocoder (`test_public_geocoding.py`).

---

## 3. Minh chứng Trực quan Trình duyệt (Browser Verification Artifacts)

- `public_branch_finder_map_1790066428804.png`: Bản đồ tìm chi nhánh công khai và kết quả tra cứu.
- `retail_gis_spatial_dashboard_1790066617363.png`: Bản đồ phân tích không gian bán lẻ và mật độ khách hàng.
- `service_gis_operations_dashboard_1790067009793.png`: Bản đồ điều phối kỹ thuật viên, bán kính bao phủ và ghim sự cố.
- `gis_live_flow_1790066031365.webp`: Video toàn bộ luồng thao tác trực tiếp của browser subagent.

---

## 4. Tác động tới Tiến độ Checklist 97 Mục

- **Mục 56 (Tìm địa chỉ Nominatim thật & rate-limit)**: Chuyển sang **Đóng** (Đã kiểm chứng live và test phòng hộ).
- **Mục 57 (Xác nhận GPS trên thiết bị, từ chối quyền, sai số)**: Chuyển sang **Đóng** (Đã có logic phân cấp, test tự động đa cấp độ và xác nhận browser).
- Tiến độ: Tăng thêm 2 mục hoàn thành từ 51/97 lên **53/97 (54,6%)**.
