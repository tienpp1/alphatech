# Tiếp nối audit — kết quả ngày 12/10/2026

Tiếp nối báo cáo11/10, không thay cấu trúc/tiến độ sổ97. Giữ deterministic/no-key,
forecast lịch sử học thuật, Render Free/no worker, Local Storage và ảnh AI có nhãn.
Source/test/deploy/UAT là mức bằng chứng riêng; không chứng nhận production100%.

## Đã sửa nguồn

- Contact email malformed bị chặn trước ghi/email; form giữ dữ liệu, escape HTML,
  lỗi role=alert; không sửa User.email. Outbox/recipient policy hiện có giữ nguyên.
- Approval service chặn inactive/Google trước superuser bypass. Active non-Google
  superuser vẫn có ngoại lệ; không gọi four-eyes tuyệt đối.
- OrderUI thao tác lặp/sai/thiếu balance trả400 tiếng Việt, không500; giữ403/404,
  rollback canonical, không sửa balance thủ công.
- Reject recommendation khóa hàng, không ghi đè ACCEPTED/EXPIRED.
- Forecast thiếu/zero/invalid không bịa0%/100%; chart/monitor dùng cadence snapshot.
  Monitor không chấm ngày zero-fill/ngày hiện tại chưa xong thành actuals; weekly
  có cảnh báo completeness, số0 có record thật vẫn được giữ.
- Service rules dùng deadline SLA thật; UNKNOWN advisory, không mặc định tọa độ
  thành phố/skill-match hoặc bảo đảm SLA. Chỉ active/available, workload scope,
  expiry/dedup cho bản ghi mới, không rewrite recommendation lịch sử.
- Checkout cập nhật total từ cart API sau đổi nhận, lock submit khi pending/lỗi,
  retry và raceguard; required fields theo method ngay lần tải đầu.
- Checkout GPS finite/range/accuracy0–100m, clear dữ liệu/hint cũ, stale callback
  guard, maximumAge0 và fallback địa chỉ. Không tự lấy/lưu tọa độ.

Không model/migration/schema mới, reset database hoặc tạo giao dịch làm đẹp AI.
Các thay đổi có sẵn ngoài scope giữ nguyên, không tự stage.

## Test đã có log (không cộng các lượt chồng nhau)

| Log trong output | Kết quả |
|---|---|
| public_delivery_reliability_20261012_before.log | 6tests,2FAIL32.038s trước sửa. |
| public_delivery_reliability_20261012_after.log | 7/7OK52.576s. |
| public_contact_retention_20261012.log | 11/11OK1.804s. |
| approval_superuser_boundary_baseline_20261012.log | ConnectionTimeout trước DB test; không thực thi test, không PASS. |
| approval_and_order_ui_baseline_20261012.log | 9tests,FAILED7failures+4errors20.078s (gồm subtests). |
| approval_strict_transition_regressions_20261012.log | 96/96OK270.159s, hasher mặc định. |
| forecast_recommendation_continuation_20261012.log | 61/61OK169.107s trước follow-up service rule cuối. |
| forecast_recommendation_final_focused_20261012.log | 114/114OK43.959s, MD5 chỉ process DB test. |
| checkout_controls_baseline_20261012.log | 0/7PASS742.7013ms trước sửa. |
| checkout_controls_fixed_20261012.log | 7/7PASS519.8061ms trước reset GPS hint. |
| audit_followup_integration_20261012.log | 111/111OK157.505s; discovery1397 không nghĩa đã chạy1397. |
| audit_followup_javascript_20261012.log | 33/33PASS783.172ms trước reset GPS hint; lượt cuối ghi sau. |

DB test randomized loopback tự hủy. Không restart/reset DB để bỏ lỗi. Email/DOM/
provider trong regression là mô phỏng, không là inbox/GPS thực. Hai apply_patch
thất bại do context/emptyhunk là lỗi thao tác giữ riêng, không là test ứng dụng.

## Production trước phát hành mới

Browser chuẩn bị giỏ session đúng1 SKU44/SP-NET-006, chưa tạoOrder/giữ tồn.
Tái hiện STORE_PICKUP vẫn shipping30000,total125000 trên bản cũ; ảnh
output/audit_followup_20261012_browser/checkout-pickup-before.png.
Neon readonly baseline: giá95000, stock14/40/16 tại BR-D1/BR-D7/BR-BT; không kiểm
kê vật lý. Helper dùng readonlySQL, API scoped cho đúng TEST, không dùng SQLwrites.

Nominatim tìm đúng Bưu điện Trung tâm Sài Gòn. OSRM trả đường ô tô ba chi nhánh
1,1/7,5/5,3km, chọn Quận1; origin công khai, không vị trí riêng tư/GPS. Không
chứng nhận đường ngắn nhất tuyệt đối hoặc traffic trực tiếp. Browser input ẩn
timeout trước dispatch; hiển thị rồi re-observe để tương tác, không replay submit.

## Các cổng tiếp theo

Fullindex/check/drift/security, CI/deploy đúngSHA mới; sau đó TEST strict→approval
→notice→cancel/replay/audit, recipient từng inbox, GPS thiết bị và responsive.
Chủ dự án đồng ý kiểm hai inbox và GPS; chưa tự gán kết quả người dùng.
Không gọi tool→approval là recommendation tự sinh; không ép stale/advisory thành
mutation. Recommendation TEST contract chỉ chứng minh workflow, không chất lượng AI.

XGBoost chưa cải thiện: revenue audit lịch sử MAE28.117.861,47 so naive27.712.533,33
/MA7 19.676.314,29, R²−1,5019 vẫn giữ. Không training/replay synthetic rồi gọi là
chứng cứ dữ liệu thật mới. Muốn vận hành cần completeness và dữ liệu mới/đầy đủ,
đánh giá ngoài mẫu; không mở Gemini/S3/worker trái phạm vi đã chốt.

## Cổng nguồn phát hành

Export Gitindex credential-free đạt1385/1385OK292.829s, DBtest riêng tự hủy;
MD5 chỉ process test, compatibilitylegacy chỉ process (stricttest override),
không hasher/policy runtime. Result repair_release_snapshot_result_followup_20261012.json
ghi tree/index_unchanged;12test untracked có sẵn không đưa vào release này.
Lượt cuối JavaScript33/33OK657.2144ms sau resetGPS hint. Compileall đạt,
Bandit scopeCI0findings/0errors, scan843files0knownsecrets (không chứng minh rotate).
Sau fulltest chỉ bổ sung receipt và bỏ blanklineEOF ở2testfile, không đổi
runtime/testassertions. diffcheck lỗi whitespace trước sửa được giữ, không skip.
CI/deploy/UAT của source mới còn chờ và sẽ ghi riêng bên dưới.

## Phát hành và browser production

Source c6ef58cfc5cf8ec297097972874513027a20b0a1 đã push main. GitHub Actions
38196214508/job114639316420 completed/success, 36 bước thành công (receipt
audit_followup_ci_20261012.json, 02:41:43 UTC). Render Free deploy
dep-db64ecp42hec73as5770 LIVE đúng SHA, không mở dịch vụ trả phí.
Đây là CI các nhóm được workflow chọn, không gọi là full-suite trên GitHub.

Browser sau reload production: HOME_DELIVERY tổng125000; STORE_PICKUP phí0,
tổng95000, address không required và branch required. Đổi lại HOME_DELIVERY
phí30000, tổng125000. Có ảnh checkout-pickup-after.png, checkout-test-ready.png
trong output/audit_followup_20261012_browser. Form TEST chưa submit khi ghi
đoạn này; không suy ra stock/email/approval từ việc chuẩn bị form.

Radius trên origin công khai: 1km thấy1/3, 10km thấy3/3; tuyến OSRM tới Quận1
1,1km và bước tiếng Việt, không traffic/GPS thật. Mobile375 không tràn ngang
control nhưng phát hiện title header chồng cart (title.right232,75 > cart.left
155,31). Sửa tối thiểu text min-width0/logo flex-shrink0, thêm1 regression;
layout/policy13/13OK0.630s không tạoDB. Chưa coi source regression là đo hình
học sau deploy; full1385 nêu trên thuộc source trước follow-up CSS/test này.

Chủ dự án trả lời GPS thiết bị **chưa thử**, xin hỏi lại khi rảnh. Giữ cổng này
mở, không gán PASS hoặc yêu cầu tọa độ riêng tư. Email2inbox/TESTapproval cũng
chưa có kết quả mới; checkout cuối cần người dùng xác nhận điều khoản tại thời
điểm đặt. Không thay đổi sổ97.

## TEST nghiệp vụ live — 12/10/2026

Sau xác nhận tại thời điểm đặt của chủ dự án, browser gửi đúng1 cáp Cat6
SP-NET-006, không giao/không thu tiền. Đơn ORD-20261012-B8277C (ID162 trên Neon
hiện tại, không đồng nhất bản ghi ID162 trong database cũ) tổng125000, PENDING,
reserved=True; BR-D1 giảm14→13, BR-D7/BR-BT vẫn40/16. Customer/User ownership
giữ nguyên; OrderDeliveryAddress lưu riêng thông tin người nhận, không sửa hồ sơ.

MANAGER2 tạo ApprovalRequest3 bằng tool update_order_status: HTTP200
APPROVAL_REQUIRED, đơn vẫnPENDING. Tự review HTTP400 có APPROVAL_PERMISSION_DENIED;
ADMIN1 là người khác review HTTP200 EXECUTED, đơnCONFIRMED, audit ORDER_CONFIRMED
và MUTATION_EXECUTED. ReplayHTTP200 idempotent_replay=True, không thêm thực thi
hoặc trừ tồn. Đây là tool→approval thật, không gán là recommendation tự sinh.

Trong lúc notice24 vẫn chưa đọc: phiên MANAGER không sở hữu đơn không thấy notice,
ack404, trang success/detail404; anonymous feed401. Đây là live kiểm một danh tính
nội bộ không sở hữu, không gọi là UAT khách hàng thường thứ hai. Test tự động có
khách hàng khác; quyền cấp vai trò không làm bỏ ownership ở public endpoint.
Đúng chủ đơn Google Minh mở tài khoản thấy dialog đúng mã TEST và22 confetti;
bấm xem thành công, DBread_at ghi03:05:08 UTC, reload dialog đóng/không lặp.
Ảnh owner-celebration.png lưu riêng, không chỉ suy ra từ trạng thái database.

Hủy đúng TEST HTTP200 CANCELLED, release timestamp có, stock13→14 và40/16
không đổi. Audit104 ORDER_FULFILLMENT_STOCK_RELEASED ghi before13/after14/qty1,
audit105 ORDER_CANCELLED. Hủy lặpHTTP400, không thêm release/tăng tồn. Giữ bản ghi
TEST/audit để truy vết; không xóa, giao hàng, thanh toán hoặc sửa balance SQL.
Receipts từng pha: output/strict_uat_20261012/*.json (SQL readonly; API scoped).

Hai outbox ORDER độc lập SENT/attempt1 lúc02:55 UTC. Chủ dự án xác nhận rõ
**cả hai inbox đã nhận** ở lượt hỏi đối chiếu; ghi là human Inbox/Spam confirmation,
không tự đọc nội dung hộp thư và không suy ra các sự kiện khác từ đơn này.

## Follow-up kiểm chứng và nguồn đọc

Header commit d5dab699368c667171d6bae42678f32851b9ddfc: CI38197498719 success36steps,
RenderFree dep-db64np942hec73at69c0 LIVE. Browser375: title.right170,08 < cart.left
182,07, docwidth360 <=375; landscape812: title.right275,99 < cart.left418,33,
docwidth797 <=812. Ảnh branch-mobile-375-after.png/branch-landscape-812.png;
override viewport đã reset. Không coi kích thước browser là GPS điện thoại thật.

UAT phát hiện xác nhận/chi tiết đơn dùng Customer.phone trống và email hồ sơ cũ,
mặc dù có OrderDeliveryAddress. Sửa2readviews/templates đọc snapshot hiện có,
chỉ fallback Customer cho đơn không có snapshot; blank snapshot không fallback.
Không parse notes/rewrite dữ liệu. Snapshot/ownership/guest/escape/read-only cùng
identity/policy25/25OK5.302s. Nhãn chờ telemetry đổi thành HTTP health, không
gọi request health là benchmark AI/GIS; tăng assertion, không bỏ test cũ.

F18 bổ sung test thật generate rule/PostGIS→accept→approval→reviewer khác→dispatch
task/audit→replay. 36/36OK10.856s, DB test riêng tự hủy; không mock generator,
Recommendation thủ công hoặc execute_tool rời. Dữ liệu fixture synthetic và test
chỉ chứng minh workflow local, chưa chứng minh chất lượng quyết định hoặc UAT
production recommendation tự sinh. Chưa chạy evaluate toàn production để tạo
TEST vì sẽ ghi khuyến nghị cho nghiệp vụ không nằm trong TEST.

## Cổng full-suite follow-up cuối

Export Git index mới: **1394/1394 OK, 281.556s**, không skip, test database
test_alphatech_evidence_c94a1cf08b6f47aa tự hủy. Receipt
output/repair_release_snapshot_result_final_followup_20261012.json ghi tree
9d342f082fb3fc542f104f290b90b0e3853c1452 và index_unchanged=True. Đây là toàn
bộ source test tracked chuẩn bị phát hành, không12test untracked có sẵn; không
lấy count discovery worktree làm count test release. MD5 và legacy compatibility
chỉ process disposable test, runtime strict/no-key không đổi. Snapshot đọc,
generated recommendation chain và telemetry loading assertions đều trong lượt.
Sau lượt chỉ thêm receipt tài liệu; không đổi runtime/test assertions.

## Dịch vụ/liên hệ và lỗi mức ưu tiên phát hiện qua UAT

Commit1bb025c810c421a1e77643b9698f776f6886da62: CI38199450934 success36steps,
RenderFree dep-db654sg473hc73d5jrr0 LIVE. Browser chi tiết TEST sau reload đã
hiển thị phone/email/address snapshot đúng, không còn dùng hồ sơ trống cũ.
JS trước bổ sung priority là33/33OK286.932ms; không đổi nhãn thành GPS thật.

Browser gửi SERVICE TEST122 và CONTACT TEST2; mỗi sự kiện có2outbox độc lập
SENT/attempt1 cho account/form. Chủ dự án trả lời “có cả2” khi được hỏi riêng
hai loại thư ở hai inbox; ghi là phản hồi human theo nội dung câu hỏi, không tự
truy cập hộp thư. SQL snapshots dùng readonly và guard user5/workspace/TEST.
Ticket122 thuộc xyz-service, Customer90 cùng workspace; chưa assigned/task,
SLA/deadlineNULL (UNKNOWN). Đã hủy ticket122 qua API; audit106 ghi OPEN→CANCELLED,
closed_at có, hủy lặp200 không thêm audit/task. CONTACT TEST giữ lịch sử, không xóa.
Browser timeout trước lần gửi SERVICE đầu: query readonly xác nhận chưa có row
trước khôi phục browser visibility/re-observe và gửi1lần; không replay mù.

UAT chọn P3 nhưng ticket122 vẫnMEDIUM. Đã ghi nhận lỗi thật, không sửa hàng cũ:
UI gửi HIGH/MEDIUM/LOW qua field priority, P1/HIGH,P2/MEDIUM,P3/LOW, mặc địnhP2.
Server validate trước ghi/email; thiếu field từ client cũ vẫnMEDIUM. Fingerprint
MEDIUM giữ byte-for-byte kể cả nonce, nonMEDIUM thêm marker riêng. REQUEST_CREATED
dùng audit convention hiện có, atomic/new-only, chỉID/status/priority/origin,
không nội dung liên hệ và không tạo SLA/deadline/task/điều phối tự động.
Sửa2caption còn sót: tiếp nhận trực tuyến thay hỗ trợ24/7; giới thiệu dịch vụ cần
nhân viên xác nhận thay tuyên bố điều phối tự động. Không đổi animation/style.

Priority focused53/53OK43.055s; log public_service_priority_20261012_retry.log.
Lượt trước53FAILED1/45.087s: test mới kỳ vọng1email trong khi policy đúng là2;
đã sửa test mới thành2 và assert đúng tập account/form, không nới/xóa test cũ.
ActualinlineJS2/2OK386.7449ms; publicpolicycopy11/11OK0.669s không tạoDB.
CI thêm testJS mới. Full1394 của1bb phía trên không gán cho nguồn priority/copy
này; sẽ có fullindex/CI/SHA và P3→LOW live receipt riêng sau freeze.

Nguồn priority cuối đã freeze và đạt **1402/1402 OK337.335s**, khôngskip;
test_alphatech_evidence_0a216da4b1184591 tự hủy. Index tree
0f3bc668ad92bcc7063932ff90773601484ecda5 không đổi trong lượt; receipt
repair_release_snapshot_result_priority_final_20261012.json. Sau full chỉ thêm
receipt tài liệu, không đổi code/testassertions. JavaScript cuối35/35OK913.5612ms.
Không cộng các lượt1402/1394/1385 có phần chồng lặp thành tổng test khác nhau.
