# Đợt đối chiếu mã nguồn, hồ sơ và replay — 25/09/2026

## Kết quả kiểm thử toàn bộ trước bản vá cộng tác

`python scripts/run_acceptance_verification.py` chạy suite `tests` trên PostgreSQL/
PostGIS local với settings riêng, test DB ngẫu nhiên; không reset DB nghiệp vụ.

- **1.095 tests, OK, 3037.883s; 0 failure, 0 error, 0 skipped.**
- Nguồn: `output/acceptance_verification/20260925T012747Z/`.
- Fingerprint apps/config/tests Python không đổi trong lần chạy. Worktree dirty,
  nên đây là phiên bản source theo SHA256, **không phải Git release đã push/deploy**.
- Log SHA256: `dde7012ed012a929afc62408edd9b060d9326e970bc1d768fec7304deb6f1e1b`.
- Tài liệu được chỉnh trong lúc suite chạy; fingerprint runner không bao gồm
  docs/template/static. Kiểm tra tài liệu cần chạy lại sau cập nhật cuối.
- Parser ban đầu bỏ sót ID đầu do stdout migration ghép dòng với stderr test;
  bản sửa nhận cả header có docstring xuống dòng, trích được 1.095 ID duy nhất.
  Không sửa log gốc. Gói replay giữ bản summary ban đầu 1.094 ID; tổng runner
  vẫn 1.095 và OK ở cả hai bản. Các file audit v1/v2 không đủ; v3 đã đủ ID.
  Bản `use_case_traceability_final_20260925.json` xác minh lại hash ma trận cuối.

## Ma trận và sơ đồ

- Đối chiếu đề cương đã duyệt teacher_review_v2, giữ nguyên Word gốc.
- 35 ca sử dụng ánh xạ source/test/giới hạn tại
  `ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md`.
- `output/use_case_traceability_final_20260925.json`: 35 dòng,
  không thiếu file và không thiếu bản ghi thực thi ở các file test dẫn chiếu.
  Không suy ra mọi yêu cầu đã được kiểm đủ từ việc file test có chạy.
- 48 model được xuất field, FK/M2M, constraint và hashes; routes trích từ URL
  resolver tại `output/model_contract_20260925_v2/`.
- Sửa ERD và bốn sequence theo checkout strict, service assignment, RAG và
  chat/bản tin. Không còn field reservation tưởng tượng, Numeric FactGuard
  runtime hay tự tăng bulletin views khi đọc. ORM không chứng minh DB deploy
  đã migrate. Sơ đồ kiến trúc là phân nhóm trách nhiệm, không mô tả mọi HTTP
  request đều dùng cùng đường RBAC; cổng public và internal vẫn tách biệt.

## Dataset và thực nghiệm

Xem `ACADEMIC_REPLAY_CATALOG_2026_09_25.md`: forecast có snapshot/model/results;
RAG/approval có source+fixtures+log và replay **17 tests OK** từ snapshot độc lập.
Không ghi điểm semantic thay người chấm và không giấu baseline tốt hơn XGBoost.

## Bản vá sau full suite

Chat/bản tin UI trước đây chọn workspace mặc định khi query tường minh sai;
UUID sai có thể gây lỗi 500. API cũng chưa thống nhất xử lý UUID/rỗng.
Đã dùng một resolver chia sẻ trên tập workspace active được cấp quyền,
tôn trọng header đã kiểm bởi middleware và từ chối selector xung đột.
Không đổi routes/schema, không cấp quyền mới, không tạo migration.

Nhánh chat không bắt PermissionDenied trong `except Exception` hoặc trả nguyên
exception cho API client. Bổ sung 12 test về UI/API read/write, blank/foreign/
invalid selector, membership/workspace inactive, superuser, headers và no-write.
Nhóm focused **52 tests OK, 224.808s**, gồm collaboration selection, bulletin
update/chat, workspaces, log parser và audit manifest. Lần khởi động đầu bị
PostgreSQL connection timeout trước chạy test; đã xác nhận kết nối local hồi
phục rồi chạy lại. Không gán full-suite trước bản vá cho source sau bản vá.

`python manage.py check`: no issues. `python manage.py makemigrations --check
--dry-run`: No changes detected. Parser có thêm một regression docstring sau
lúc nhóm 52 được discovery; nhóm parser/manifest cuối đã chạy riêng:
**14 tests OK, 2.936s**. Discovery 1.109 là kiểm kê sau bản vá, không phải full
suite 1.109 đã chạy. Không cộng 52/14/17 vào 1.095.

Rerun sau cập nhật ledger cuối: **14 tests OK, 6.320s**. Kiểm ledger bằng script:
97 ID duy nhất, 81 đóng, 16 mở, không đổi mẫu số. `git diff --check` trên các
file tracked đã sửa trong đợt không báo lỗi whitespace (có cảnh báo LF/CRLF).

## Tiến độ

Đóng thêm mục **81, 82, 83, 84, 85** theo tiêu chí hồ sơ/bằng chứng: từ 76 lên
**81/97 (83,5%)**, gồm 70 kế thừa và 11 đối chiếu lại. Không tự tăng độ tin cậy
của 70 mục kế thừa thành chứng nhận độc lập. 16 mục còn mở: **7, 11, 13, 39,
46, 56, 57, 89, 90–97**. Rà tài liệu còn có thể tiếp tục local; phần live cần
đúng môi trường và chứng cứ, không chỉ cấu hình tồn tại.

## Giới hạn thật

- Trình duyệt không khởi tạo được: kernel assets, os error 3. Không có visual QA mới.
- HTTPS public probe tại `output/public_probe_20260925.json` bị ReadTimeout;
  chưa gửi truy vấn Nominatim vì chưa lấy được trang/CSRF. Không kết luận website
  hỏng chỉ từ timeout của môi trường này. GPS thật chưa kiểm.
- Không push/deploy dirty worktree hàng trăm file để lấy phần trăm tiến độ.
- Chính sách được duyệt, semantic RAG review, IEEE toàn bộ bản nộp và bằng chứng
  production vẫn cần hoàn thiện. pg_dump→pg_restore tiếp tục hoãn theo yêu cầu.
