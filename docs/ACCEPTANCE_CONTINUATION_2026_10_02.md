# Tiếp tục kiểm chứng — 02/10/2026

Không đổi cấu trúc, ID hoặc số tiến độ của checklist 97 mục. Các kết quả dưới đây
không tự tạo chứng nhận 97/97 hoặc production 100%.

## Quyết định trực tiếp của chủ dự án

- Hoãn off-site backup: chưa có USB/cloud ngoài máy; giữ bản mã hóa trên D.
  Không gọi backup cùng máy là phương án phục hồi khi mất máy.
- Endpoint R2 trước đây là thông tin ví dụ do agent tạo, không phải bucket thật.
  SDK và TLS trực tiếp đã thất bại handshake; chưa upload object hoặc dữ liệu.
- Chỉ nghiệm thu media/model với Local Storage cho bảo vệ đồ án đợt này.
  Runtime giữ FileSystemStorage; không bật S3, không thêm schema/migration,
  không chứng nhận lưu trữ bền vững Render Free hoặc phục hồi 3 artifact remote.
  Script check_r2_storage chỉ là công cụ chẩn đoán tùy chọn, không bằng chứng
  tích hợp storage đã hoàn thành. Không cần SDK R2 để chạy website hiện tại.

## Thực hiện và kiểm chứng

- Harden backup: chặn .env.*, tên trùng, traversal, manifest không khớp.
  9/9 guard/backup unit tests PASS (0.120s).
- Truy vết 35 use cases: không thiếu source/test file được tham chiếu;
  chưa đối chiếu test IDs của một full run mới hoàn tất. File tồn tại không
  chứng minh đúng nghiệp vụ.
- Django check: 0 issues. Migration drift: No changes detected.
- Bandit 1.9.4 quét apps/config, loại migrations: 0 findings, 0 parse errors,
  32166 LOC, nosec=0, skipped_tests=0. Không phải bảo đảm mọi lỗi bảo mật.
- Runtime Python toàn máy có 98 advisories / 7 packages theo pip-audit.
  Không suy rộng sang Render. Virtualenv .venv trước đó không có Django;
  kết quả audit không finding của virtualenv rỗng không dùng để nghiệm thu.
- Tạo .venv-acceptance riêng từ requirements.txt, không nâng package Python
  toàn máy. Dependency audit ban đầu virtualenv mới chỉ còn 4 findings ở pip;
  đã nâng pip 26.1.1 → 26.2.1. Quét lại virtualenv chứa toàn bộ dependencies
  ứng dụng trả 0 known vulnerabilities, exit 0. Không chứng nhận global Python
  đã được sửa hoặc dependency set production giống virtualenv này.
- Virtualenv mới: Django 6.1.1, Pillow 12.3.0, pypdf 6.19.0,
  sqlparse 0.6.0, urllib3 2.8.0; check 0 issues và migration drift không thay đổi.
- Secret release guard: 791 files, 0 known-pattern findings, không chứng minh
  provider rotation hoặc mọi dạng secret.
- Sửa copy service inquiry: thời gian P1/P2/countdown ghi mô phỏng, bỏ cam kết
  dưới 15 phút và tự động điều phối chưa được xác minh. Giữ wizard/animation;
  16/16 policy/public-copy tests PASS (2.046s). UI/UX skill dùng nhãn rõ ràng,
  không redesign. Browser không attach được webview; chưa visual PASS.
- Nhóm thay đổi mới nhất chạy trên .venv-acceptance: policy/public-copy/CSP/
  backup/restore-guard/R2-diagnostic, 30/30 tests OK (5.852s).
- Chat/bản tin trên .venv-acceptance: 11/11 tests OK (173.870s), database
  kiểm thử mới được test runner dọn sau khi hoàn tất. Không có reset dữ liệu
  phát triển hoặc production.
- Đồng bộ giới hạn đề cương/phụ lục và mốc khoa trong ACADEMIC_ACCEPTANCE_SCOPE;
  không sửa bản Word hoặc ledger.
- Full suite chẩn đoán trên database evidence riêng với Python toàn máy:
  1170 tests / 3229.868s, FAILED (2 failures), exit 1. Failure đầu ở
  test_bulletin_update: quyền MANAGER bị giữ bởi cache sau khi membership
  vô hiệu hóa. Failure thứ hai ở test_academic_test_manifest_audit: thiếu
  tên 8 file test trong manifest. Không xóa/nới assertion để làm xanh.
  Đã bỏ memoization quyền/vai trò, đọc membership/grants hiện hành mỗi lần;
  bổ sung tên file và giới hạn bằng chứng vào manifest. Hai regression mới
  cho membership/role cập nhật trực tiếp và permission-through deletion:
  2/2 OK (22.099s). Tái kiểm chứng bulletin update/chat, manifest, RBAC và
  authorization convergence: 36/36 OK (310.089s), exit 0.
  Các bổ sung sau khi full suite bắt đầu được ghi riêng, không coi đây là
  snapshot bất biến của release cuối hoặc full suite mới đã xanh.

## UAT do chủ dự án xác nhận ngày 02/10/2026

- 08:30: đăng ký trên Windows 11/Chrome, xác minh email trên iPhone 14
  (Gmail/Safari), máy tính tự chuyển sang đăng nhập không cần F5: PASS theo
  xác nhận trực tiếp của chủ dự án. Không phải browser test độc lập của agent.
- 08:40: admin Windows 11/Chrome duyệt yêu cầu dịch vụ; đúng khách hàng trên
  iPhone 14/Safari thấy animation cảm ơn: PASS theo xác nhận của chủ dự án.
- Riêng đơn mua sản phẩm bán lẻ: chủ dự án xác nhận chưa kiểm chứng animation,
  chống lặp và cách ly khách hàng trên production; giữ CHƯA NGHIỆM THU.
  Source có signal Order PENDING → CONFIRMED, feed theo recipient/ownership
  và POST xác nhận đã xem; sự tồn tại của mã nguồn không thay thế UAT.
- Nhóm authorization/approval concurrency/registration code trên virtualenv
  acceptance: 35/35 tests OK (229.113s). Không sửa mẫu số hoặc trạng thái ledger.
- Nhóm notification customer ban đầu: 6/6 OK (6.273s), kiểm tra phát sinh sau
  phê duyệt, quyền recipient, CSRF và rollback. Browser đã mở được production;
  chủ dự án đăng nhập tài khoản có quyền nội bộ nhưng chưa có đơn. Chưa duyệt
  đơn thật hoặc tạo đơn TEST; đang chờ xác nhận phạm vi thao tác production.
- Bổ sung test xác nhận đơn qua transition_order_status, recipient không bị đổi
  sang admin và trạng thái đã xem giữ qua browser session mới: nhóm customer
  approval notices 7/7 OK (16.939s). Check 0 issues; migration drift không đổi.

## Browser UAT bán lẻ tiếp nối ngày 02/10/2026

Sau xác nhận cho phép cụ thể của chủ dự án, agent tạo duy nhất đơn
ORD-20261002-9733DF (ID 161), lúc 09:06 theo trang thành công production.
Một cáp SP-NET-006, nhận tại cửa hàng, giá trị 95.000 VND; ghi rõ TEST,
KHÔNG GIAO HÀNG/KHÔNG THU TIỀN, không thanh toán trực tuyến. Không đổi hồ sơ
email/điện thoại của khách hàng; dữ liệu TEST nằm trong snapshot đơn.

Tab nội bộ xác nhận đúng ID 161: trạng thái Đã xác nhận. Tab public giữ nguyên
hiển thị dialog “Đơn hàng của bạn đã được duyệt!” và lời cảm ơn chứa đúng
ORD-20261002-9733DF. Đã chụp screenshot output/uat_20261002/retail-celebration.jpg.
Bấm “Tuyệt vời, cảm ơn!”, reload: dialog không mở; sau chu kỳ polling tiếp
theo vẫn không mở. Đây là browser evidence cho hiện thông báo/ack/chống lặp
trong phạm vi thử nghiệm, không chứng minh mọi browser/device/network failure.

Đã hủy chính đơn TEST bằng UI nghiệp vụ và xác minh trạng thái “Đã hủy”,
không hoàn thành bán hàng, không xóa record/audit. Screenshot:
output/uat_20261002/retail-test-cancelled.jpg. Không đo tồn kho trước/sau nên
không tuyên bố độc lập stock reconciliation PASS từ thử nghiệm này.

Hai tab dùng cùng tài khoản Minh có quyền nội bộ (chủ đơn). Chưa có phiên
tài khoản thứ hai để kiểm chứng live chống lộ thông báo; phần cross-user được
kiểm tra tự động, không gán thành bằng chứng browser production. Không sửa
tiến độ/structure checklist theo Rule 12.

## Giới hạn xuất bản

Mọi patch trong đợt này còn local; chưa commit/push/deploy hoặc có CI riêng.
CI f2a831c đã xanh trước đây không chứng nhận dirty source hiện tại.
Không tự đóng các cổng đã hoãn hoặc thay đổi mẫu số để gọi 100%.
Bandit quét lại apps/config sau patch RBAC: exit 0, results rỗng; artifact
output/bandit_acceptance_post_rbac_20261002.json. git diff --check exit 0.
