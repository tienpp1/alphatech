# Diễn tập pg_dump → pg_restore thật — 02/10/2026

## Phạm vi

Chủ dự án cho phép thực hiện dump/restore ngày 02/10, thay quyết định hoãn trước đây cho diễn tập an toàn này. Không reset/ghi đè database hiện hành, không sửa cấu trúc hoặc tự cập nhật số tiến độ checklist 97 mục.

Nguồn: `alphatech_db`, xác định trực tiếp từ env dịch vụ Render srv-dafrcr5g1s2s73frbl1g. Khác staging trong .env. TLS, transaction REPEATABLE READ READ ONLY, pg_export_snapshot truyền vào pg_dump; dữ liệu đối chiếu cùng snapshot.

Đích mới local: `alphatech_restore_20261002_398b4903fc`, tạo từ template0 rỗng, không clone TEMPLATE staging. Không --clean/--create/--disable-triggers, không xóa DB. CONNECT cho PUBLIC tại đích đã thu hồi; không đổi quyền nguồn.

## Kết quả thực thi

- pg_dump/pg_restore client 18.3; nguồn PostgreSQL 18.6; PostGIS hai phía 3.6.2.
- Custom dump exit 0, 64.704s, 633369 bytes, stderr không cảnh báo.
- Restore exit 0, 10.575s; --single-transaction --exit-on-error --no-owner --no-privileges; stderr không cảnh báo.
- Archive SHA-256: `6e27c866cff055ab519372c234046be9de5b41e168a8a97fbfc65dd64fba0d37`.
- Checksum sau restore khớp; 60 bảng/10576 dòng khớp count và hash, gồm cả dữ liệu mở rộng PostGIS, không phải 10576 giao dịch nghiệp vụ.
- Constraints/audit triggers khớp; 0 invalid indexes, 0 unvalidated constraints. 53 sequences hợp lệ so với ID dữ liệu.
- Django check trên đích: 0 issues; 0 pending migrations. Không migrate/seed hoặc gửi email từ đích.
- ORM đọc được 7 users, 2 workspaces, 44 products, 160 orders.
- Unit guard tests: `python -m unittest tests.test_restore_drill_safety -v`, 3/3 PASS, 0.004s.

Hash lần đầu báo false do timestamp JSON local Asia/Bangkok và nguồn UTC, không phải mất dữ liệu. Sau chuẩn hóa UTC, toàn bộ bảng khớp. Giữ nguyên evidence.json ban đầu và thêm verification_utc.json PASS, không ghi đè lỗi đầu. Hàm fingerprint đã sửa chuẩn hóa timezone cho lần sau.

## Artifacts riêng tư

`D:/ai_business_platform/output/restore_drill/alphatech_restore_20261002_398b4903fc/` chứa production.dump, archive-toc.txt, stderr logs, evidence.json và verification_utc.json.

Dump chứa dữ liệu thật, có thể gồm password hashes/session/token. ACL thư mục giới hạn tài khoản Windows hiện tại và SYSTEM. output/ và *.dump bị Git ignore. Không upload hoặc gửi dump công khai. Đích restore giữ lại cho chủ dự án kiểm tra; website vẫn dùng DB production cũ.

Kiểm tra lại chỉ đọc, từ terminal repository:

```powershell
python scripts/verify_restore_drill.py output/restore_drill/alphatech_restore_20261002_398b4903fc
```

Tạo diễn tập mới khi được cho phép:

```powershell
python scripts/production_restore_drill.py --execute
```

Lệnh tạo đích local mới, không reuse/reset DB. Cần PostgreSQL 18 tại đường dẫn hiện tại và .env local/Render đã có. Không đổi DATABASE_URL website sang bản restore.

## Giới hạn

Đã chứng minh khôi phục schema/data production từ file dump độc lập sang local. Không chứng nhận cloud failover/PITR/RTO/RPO hoặc ứng dụng live trên đích. Ownership/grants bị bỏ qua có chủ đích, chưa diễn tập tái tạo quyền production hoặc whole-cluster roles.

Media, file tài liệu RAG, model artifacts và secrets không nằm trong pg_dump. Cần backup riêng; hiện chưa có bản mã hóa off-site hoặc lịch backup tự động. Chủ dự án cần chọn nơi lưu an toàn nếu muốn thực hiện tiếp; không gửi secrets/dump công khai.
