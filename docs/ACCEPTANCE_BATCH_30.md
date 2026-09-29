# Đợt 30 — hoàn tất test bị chặn và sửa nhãn kết quả không có căn cứ

Ngày 17/09/2026. Không push/deploy, không sửa database nghiệp vụ hay quyền role.

## Đã làm liên tiếp

1. Kiểm tra C: còn 11.48 GB; chạy lại full demo seed trong evidence database mới.
   Bỏ keepdb để Django thu hồi đúng database của lượt chạy; không dọn 53 DB cũ.
2. Siết smoke test: 4 user, 2 workspace, có retail/service data, Customer và Service
   cùng workspace ticket, mọi Document READY, đủ 3 ForecastRun COMPLETED, không
   gọi urllib provider. Chỉ seed mô phỏng/offline, không đo chất lượng dự báo/RAG.
3. Sửa seed: caught failures trong forecast/recommendation hoặc Document chưa READY
   dẫn tới DEMO PARTIAL và tên bước. Không in raw exception cho các bước đã sửa.
   DEMO COMPLETE chỉ nghĩa các bước seed được cấu hình xong, không là production gate.
4. Phát hiện qua browser ticket không có SLA vẫn hiện ĐÚNG HẠN và chính sách tự đặt.
   Sửa ticket-detail template: thiếu deadline hiện CHƯA ĐỦ DỮ LIỆU ĐÁNH GIÁ SLA;
   thiếu policy/hạn có nhãn rõ. Nếu một hạn đã vi phạm, vẫn hiển thị Vi phạm cho hạn
   đó. Không thay đổi engine, API hoặc các dashboard SLA khác trong đợt này.

## Kiểm thử

```powershell
python manage.py test tests.test_full_demo_seed tests.test_demo_document_routes --settings=config.settings_evidence_test --noinput -v 1
# 3 tests, 34.978s, OK; fresh test DB destroyed
python manage.py test tests.test_full_demo_seed tests.test_seed_demo_reporting tests.test_internal_authorization_regressions tests.test_service_sla --settings=config.settings_evidence_test --noinput -v 1
# 21 tests, 144.927s, OK; fresh test DB destroyed
python manage.py check
# No issues
python manage.py makemigrations --check --dry-run
# No changes detected
```

24 lượt thực thi, 23 test khác nhau (full seed chạy lại sau khi siết assertion).
Không có failure/skipped trong hai lượt này. Không chạy full suite.

## Browser và skill

Dùng ui-ux-pro-max cho kiểm tra form/nhãn; browser đã phục hồi sau lỗi khởi tạo
đợt 29. Mở snapshot HTML thật do Django test client render bằng dữ liệu giả:
`output/evidence_tests/eddcb95da76b4ce2/service_ui/manager.html`, `technician.html`.
Server chỉ bind loopback; không kết nối business DB. Manager có lựa chọn hai kỹ thuật
viên và mutation controls; technician chỉ có chính mình, không có quản lý trạng thái.
Reload snapshot mới xác nhận nhãn thiếu SLA đã thay thế nhãn đạt không có dữ liệu.

Giới hạn: snapshot không xử lý POST/authentication; endpoint notification trả 404
trên static preview là dự kiến. Screenshot khung hẹp khoảng 304 px cho thấy thanh
điều hướng tràn ngang/chiếm màn hình; chưa sửa hoặc nghiệm thu responsive toàn trang.
Không tuyên bố browser production hay phiên đăng nhập thật đã qua.

## Tiến độ / phần cần quyết định

44/97 =45.4%, không tăng vì 70/87 còn thiếu chốt quyền kỹ thuật viên và walkthrough
đầy đủ. Cần quyết định nhân viên chỉ ghi giờ chính mình, hay được chuyển trạng thái
task được giao. Không tự mở rộng quyền. Các bản Word chưa cập nhật trong đợt này.

Cần rà tiếp các surface SLA khác có thể còn coi deadline thiếu là ON_TIME; sửa
ticket-detail không đồng nghĩa metric toàn hệ thống đã đúng. Seed smoke không đo
failure propagation của mọi substep hoặc độ đầy đủ toàn bộ UI demo.
