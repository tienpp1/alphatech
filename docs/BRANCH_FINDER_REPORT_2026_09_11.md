# Báo cáo trang tìm chi nhánh — 11/09/2026

## Phạm vi và cách thực hiện

Đọc trang, view, model Branch, kiểm thử public directory và CSP trước khi sửa. Giữ dữ liệu cùng thay đổi dang dở của agent khác. Trình tự: bản đồ nền sáng → vị trí/tìm kiếm → đường bộ → bán kính → kiểm thử và báo cáo trung thực.

Skill ui-ux-pro-max được dùng để chọn toolbar có nhãn, trạng thái lỗi có cách khắc phục, nút dễ bấm và bố cục responsive. Browser được điều khiển qua giao diện CUA để kiểm chứng trực tiếp, không suy diễn từ test mock.

## Đã thực hiện

- Bản đồ đường phố sáng OpenStreetMap, đủ ba marker theo database, zoom/pan và attribution; không dùng tiles Google trái phép.
- Lấy vị trí qua Geolocation API khi khách bấm nút, hiển thị sai số và điểm xuất phát; có thông báo từ chối/quá hạn/không hỗ trợ. Chưa xác nhận GPS thiết bị thật.
- Chọn điểm xuất phát bằng cách bấm bản đồ; không ghi vào tài khoản/database.
- Ô tìm địa chỉ bằng Photon, hiển thị các lựa chọn và chỉ dùng địa chỉ khách chọn. Timeout có hướng dẫn thay thế; chưa có bằng chứng kết quả tìm địa chỉ thật thành công.
- Tìm gần nhất bằng so sánh khoảng cách tuyến ô tô OSRM, không giả đường bộ bằng đường chim bay. Nếu chỉ một phần chi nhánh có tuyến, báo rõ chưa so sánh được tất cả.
- Vẽ tuyến đường thật, quãng đường/thời gian ước tính, chọn phương án ngắn nhất trong các tuyến trả về; có liên kết Google Maps giữ đúng điểm xuất phát và cửa hàng.
- Chế độ bán kính 1–10 km; bấm map chọn tâm hoặc lấy điểm xuất phát làm tâm; vòng tròn và danh sách lọc cùng cập nhật. Tâm bán kính độc lập với vị trí khách.
- Dữ liệu JSON escape an toàn, số không phụ thuộc locale, tọa độ 0 hợp lệ, fallback GIS Point khi thiếu lat/lng, không dẫn đường cho chi nhánh thiếu tọa độ.
- Không thêm migration, không sửa dữ liệu, không đụng quyền nội bộ, không push/deploy.

## Kiểm chứng

```text
node --check static/public/js/branch-finder.js
  PASS
node --test --test-isolation=none tests/branch_finder.test.cjs
  7 passed, 0 failed
python manage.py test tests.test_public_branch_finder tests.test_public_website_and_portal_separation.PublicWebsiteAndPortalSeparationTestCase.test_public_branches_view --keepdb --noinput
  4 tests, 4.458s, OK
python manage.py check
  System check identified no issues (0 silenced).
python manage.py makemigrations --check --dry-run
  No changes detected
```

Node runner mặc định từng báo `spawn EPERM` do sandbox; chạy cùng test với `--test-isolation=none` thành công, không bỏ test hay nới assertion.

Browser local `http://127.0.0.1:8011/chi-nhanh/`:

- Tiles sáng và cả ba chi nhánh tải thành công.
- Điểm chọn thử nghiệm công cộng (không phải GPS thật): 10.76100, 106.68964.
- OSRM trả Quận 1 gần nhất 2,2 km; hai chi nhánh còn lại khoảng 7,7 và 7,6 km theo tuyến được cung cấp.
- Dẫn đường tới Quận 1 vẽ được hình học đường bộ: 2,2 km, khoảng 3 phút ước tính.
- Bán kính 1 km: 0/3; 3 km: 1/3; 10 km: 3/3.
- Desktop 1440px và mobile 375px được xem trực tiếp; mobile document scrollWidth 360 <= viewport 375, không tràn ngang.
- Tìm “Chợ Bến Thành” gặp timeout; HTTPS probe Photon độc lập cũng timeout, kể cả IPv4. Không coi test UI lỗi là tìm kiếm thành công.

## Chưa hoàn tất và cần gì để nghiệm thu

1. **Tìm địa chỉ:** cần dịch vụ geocoding truy cập ổn định. Photon demo hiện không kết nối được từ môi trường thử. Có thể thử lại khi dịch vụ phục hồi hoặc chọn nhà cung cấp production có quota/SLA; nếu muốn Google Maps thật, cần tài khoản Google Maps Platform, billing và API key giới hạn domain/API. Chưa tích hợp key Google trong bản này; không gửi key vào chat.
2. **Vị trí thiết bị:** khách cần mở trang bằng HTTPS hoặc localhost, cho phép vị trí rồi xác nhận marker/sai số có đúng. Máy tính có thể không có GPS và trả sai số lớn. Không dùng tọa độ giả để tuyên bố GPS thật thành công.
3. **Dữ liệu chi nhánh:** xác nhận tọa độ đang lưu đúng cửa ra vào ba cửa hàng; code không tự sửa tọa độ theo phỏng đoán.
4. **Đường ngắn nhất:** OSRM tối ưu tuyến nhanh, bản này chọn quãng đường ngắn nhất trong những phương án trả về, không bảo đảm cực tiểu toàn cục. Cần thống nhất ô tô/xe máy/đi bộ và nhà cung cấp tương ứng nếu muốn thêm phương tiện/giao thông trực tiếp. Google Maps handoff hiện là ô tô.
5. **Production:** chưa push/deploy; sau triển khai cần chạy lại các bước trên ở domain HTTPS thật, kiểm tra CSP thực tế và thiết bị Android/iOS. Không cần migration cho thay đổi bản đồ.
6. **Tải lớn:** OSM tiles, Photon demo và OSRM demo không có SLA; cần chọn dịch vụ trả phí hoặc tự host trước khi dựa vào chúng cho lượng truy cập lớn. Không tự kích hoạt billing hay đăng ký dịch vụ.

## File thay đổi cho yêu cầu này

- `templates/public/branches.html`
- `static/public/css/branch-finder.css` (mới)
- `static/public/js/branch-finder.js` (mới)
- `apps/public_web/views.py` (chỉ phần public_branches_view cho tác vụ này; file có thay đổi auth trước đó)
- `config/middleware.py`
- `tests/test_public_branch_finder.py` (mới)
- `tests/branch_finder.test.cjs` (mới)
- `docs/CURRENT_STATUS.md`, `docs/CHANGELOG_AI.md`, `docs/PROJECT_CONTEXT.md`, báo cáo này.

Nguồn kỹ thuật: [OSRM API](https://project-osrm.org/docs/v5.24.0/api/), [OSM Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/), [Photon demo limits](https://github.com/komoot/photon#demo-server).

**Kết luận: triển khai local và kiểm chứng một phần live, chưa đạt 100% nghiệm thu production.**
