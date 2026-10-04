# Đối chiếu bản phát hành và nghiệm thu — 04/10/2026

Tài liệu này bổ sung bằng chứng hiện hành, giữ nguyên 97 ID và số tiến độ của
`CHECKLIST_97_PROGRESS.md` theo AGENTS.md. Header 96/97 và các tham chiếu
f2a831c/restore hoãn trong ledger là ghi nhận lịch sử; không dùng chúng làm
kết luận cho bản phát hành ngày 04/10. Không công bố 97/97 chỉ từ số test xanh.

## Phần đã đối chiếu trước phát hành

- Google-linked identity chỉ dùng cổng khách hàng, kể cả quyền superuser hoặc
  password/token cũ. Bản eef9150 đã live trên Render; GitHub run 37174258042
  completed/success cùng SHA. Quyền ADMIN/MANAGER/EMPLOYEE bằng mật khẩu giữ nguyên.
- UAT retail TEST 162: đúng chủ đơn thấy thông báo duyệt; Tien Billy không thấy
  và không xem được đơn; ack/reload không lặp; đơn đã CANCELLED. Xem
  `ACCEPTANCE_CONTINUATION_2026_10_04.md` và `GOOGLE_ACCOUNT_ISOLATION_2026_10_04.md`.
- Restore độc lập ngày 02/10 đã PASS: 60 bảng/10576 dòng đối chiếu cùng snapshot,
  constraints/triggers/sequences hợp lệ. Xem `PRODUCTION_RESTORE_DRILL_2026_10_02.md`.
- Full local snapshot trước đợt này: 1197 tests PASS/276.170s. Không dùng số này
  làm số test của bản phát hành mới; log của staged tree sẽ ghi riêng.
- HTTP production độc lập bằng session đã được server cấp của Google-linked
  test account: /tai-khoan/ 200, /noibo/, trang đơn nội bộ 162 và auth/me đều
  403. Chỉ đọc DB để chọn phiên đã có; không tạo session giả hoặc lưu credential.
  Bằng chứng redacted: output/google_http_live_20261004.json.
- Đối chiếu đủ 97 ID, không trùng/thiếu; tất cả tên tài liệu được dẫn đều tồn tại.
  70 dòng ledger ghi kế thừa; tồn tại file không chứng minh nghiệm thu từng mục.
- SHA-256 bản Word thầy duyệt vẫn là
  9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
  Không sửa bản Word đã duyệt trong đợt này.

## Bản sửa nội dung công bố

Trang chủ, form dịch vụ, sản phẩm, giỏ hàng, checkout và hai trang xem đơn dùng
điều kiện cần xác nhận thay cho mặc định VAT/bảo hành/đổi trả/giao hỏa tốc chưa
có hồ sơ duyệt. Trang dịch vụ bỏ cam kết bảo hành 30 ngày, hỗ trợ 24/7 và chứng
chỉ nhân sự chưa được xác minh. Các số đếm/thời gian/phí trên simulator được ghi
minh họa rõ ràng. Giữ animation, video, WebGL, phép tính giá và dữ liệu nghiệp vụ.

CI thêm nhóm public policy và thông báo khách hàng để kiểm tra ranh giới công
bố, recipient/ack và customer/internal trong mỗi lần push. Không hạ coverage
gate, không bỏ ca kiểm thử hoặc đổi schema.

## Đối chiếu các cổng còn được nhắc đến

| Mục | Bằng chứng hiện hành / giới hạn |
|---|---|
| 7/11/13 | Báo cáo này phân biệt local, live, Human Evaluation và phạm vi đã chốt; hồ sơ cũ là lịch sử. Chưa tự sửa số tiến độ ledger. |
| 43/46/49 | Bản sửa nội dung và regressions sẽ được xác nhận theo release sau deploy. SOP demo không trở thành chính sách thương mại được duyệt. |
| 75 | UAT đúng người/ack/reload retail đã đạt cho TEST 162; không có đo hiệu năng animation. |
| 76 | Cross-device registration được chủ dự án xác nhận UAT 02/10; giữ nguồn Human Evaluation. |
| 85/90/93 | Chạy suite trên staged tree; đối chiếu SHA GitHub/Render và CI mới sau push. |
| 91/94 | Email bốn sự kiện và Sentry nhận Error Events được chủ dự án xác nhận; chưa có message/event ID độc lập cho release cuối. |
| 92 | Render Free không dùng async worker production; chỉ nghiệm thu logic local. |
| 95/97 | Kiểm tra header/cookie/secret guard trong phạm vi release; CSP hiện còn inline/eval, rotation theo xác nhận chủ dự án. |
| 96 | pg_dump → pg_restore local độc lập đã PASS. Off-site backup hoãn; backup D cùng máy chưa bảo vệ mất máy. |

Local Storage là phạm vi học thuật được chủ dự án chọn; không có R2 bucket thật.
Chưa chứng minh phục hồi file media/model Render Free; ba artifact references
trong snapshot restore trước đây chưa có file backup tương ứng. Stock reorder
và workload execution giữ advisory đến khi có domain contract/rollback an toàn.

Ba tài khoản nội bộ dùng mật khẩu demo theo lựa chọn chủ dự án. Không tự đổi
credential trong đợt rà soát này. Cần thay credential khi chuyển sang vận hành
thực tế. Các giới hạn này không được đổi nhãn thành kiểm chứng production PASS.

## Kết quả phát hành

Local release tree `a671a0e2ff5525976ddb1af86bc084ee365bc544`: toàn bộ
`tests` chạy trên PostgreSQL/PostGIS test database độc lập: **1187 tests,
189.552s, OK**. Log: `output/policy_release_twf2mlph/tests.log`.
Các lần chạy lỗi trước được giữ lại; đã sửa fixture thiếu payment_method,
bổ sung manifest cho test đã có và sửa câu quảng bá còn sót ở trang giới thiệu,
không bỏ/hạ assertion. Nhóm policy/manifest riêng: 29 tests, 2.335s, OK.
`manage.py check`: 0 issues; migration drift: No changes detected;
staged diff check: PASS. Quét known-pattern: 800 files và 35 commits, 0 findings
trong phạm vi công cụ (không phải chứng nhận không tồn tại mọi loại secret).

GitHub/Render và quan sát live của release mới đang chờ kết quả thật; sẽ bổ sung
SHA/URL sau phát hành. Bằng chứng Google-linked identity dùng session đã cấp:
trang tài khoản HTTP 200; `/noibo/`, order nội bộ và `/api/v1/auth/me/` HTTP 403.
Đây không phải lần chạy OAuth mới. Browser ERR_BLOCKED_BY_CLIENT không được dùng
làm bằng chứng HTTP 403.
