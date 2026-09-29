# Đối chiếu khoảng cách GIS

Ngày kiểm tra nguồn: 16/09/2026. Test: `tests/test_gis_reference_distances.py`.

## Nguồn và phép đối chiếu

1. GeographicLib, “Examples”, ví dụ WGS84 inverse Wellington–Salamanca:
   https://geographiclib.sourceforge.io/html/python/examples.html
   Tọa độ lat/lon (-41.32, 174.81) → (40.96, -5.50), khoảng cách
   19,959,679.26735382 m. Khi tạo Point của GeoDjango phải đổi sang thứ tự lon/lat.
2. PostGIS, “ST_DistanceSphere”:
   https://www.postgis.net/docs/manual-3.5/en/ST_DistanceSphere.html
   Tài liệu phân biệt phép tính trên mặt cầu với ellipsoid. Các service hiện
   dùng `Distance(..., spheroid=True)` cho cả khoảng cách và bán kính.
3. Hai phép đối chiếu giải tích trên xích đạo WGS84: s = a × góc (radian),
   a = 6,378,137 m. Cung (0°,0°)→(1°,0°) dài 111,319.490793 m; cung qua đường
   đổi ngày (179°,0°)→(-179°,0°) dài 222,638.981587 m. Công thức không gọi hàm
   khoảng cách của ứng dụng để tạo expected value.

## Kết quả và giới hạn

3 test nguồn tham chiếu và 7 test GIS hiện có đạt (10/10, 0.520s).
Sai số cho ba khoảng cách tham chiếu là 0.01 m; test bán kính xích đạo còn đối
chiếu ±1 m. Bộ test chạy truy vấn PostGIS thật trong DB test riêng.

Đây là đối chiếu hữu hạn trên WGS84, không kết luận “PostGIS đúng 100%”.
GeographicLib cũng có thể là thư viện nền của PostGIS: ví dụ công bố độc lập
với code ứng dụng không đồng nghĩa hai thuật toán nền hoàn toàn độc lập.
Không đo quãng đường lái xe, chất lượng GPS hay độ chính xác mọi CRS/hình học.
Haversine của tính năng khác vẫn có thể dùng mặt cầu; không so số đó với
ellipsoid ở tolerance centimet hoặc suy ra chúng phải bằng nhau.
