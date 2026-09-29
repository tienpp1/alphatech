# Chuẩn bị demo cục bộ an toàn — 16/09/2026

Đề tài: Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI.
Đây là hướng dẫn chuẩn bị, không phải bằng chứng nghiệm thu production.

## Database và migration

Chọn PostgreSQL/PostGIS riêng cho demo trong `.env` local. Không dùng URL
production/staging và không ghi URL chứa mật khẩu vào báo cáo. Kiểm tra tên/host
trong cấu hình trước khi chạy. Không thay database hiện tại bằng database demo.

```powershell
python manage.py check
python manage.py migrate --plan
python manage.py migrate --noinput
python manage.py showmigrations
python manage.py seed_demo --confirm-empty-demo --identity-only
python manage.py runserver 127.0.0.1:8000
```

`--identity-only` chỉ tạo quyền, 4 vai trò, 4 tài khoản và 2 workspace; không
có sản phẩm/ticket/dự báo để trình diễn nghiệp vụ. Nếu cần bộ dữ liệu đầy đủ,
bỏ `--identity-only` ngay lần seed đầu trên một database demo mới khác.
Không chạy seed lại, không xóa database cũ để vượt chốt an toàn, không chạy
đồng thời hai lệnh seed. Full domain seed chưa được chạy lại trong đợt 28.

Cập nhật đợt 30 (17/09): full domain seed đã qua smoke test trên database test
riêng, gồm đủ 3 forecast run hoàn tất. Lệnh báo DEMO PARTIAL nếu các bước được
bắt lỗi chưa hoàn tất; không xem dữ liệu seed là chứng minh chất lượng mô hình.

Lệnh từ chối khi DEBUG=False, host database không phải local hoặc đã có
User/Workspace/Role. Đây là chốt vận hành, không nhận biết được database
production được chuyển tiếp qua tunnel local. Người vận hành vẫn phải xác minh
đích kết nối. Mật khẩu demo đã công khai trong README/source; không dùng cho
tài khoản thật. Lệnh không in mật khẩu/token ra terminal.

## Quyền từ chính seed hiện tại

| Tài khoản | abc-retail | xyz-service | Minh họa phù hợp |
|---|---|---|---|
| admin | ADMIN + superuser | ADMIN + superuser | Quản trị; không dùng để chứng minh RBAC của người dùng thường |
| manager | MANAGER | EMPLOYEE | Quản lý retail; ở service chỉ xem/tạo request, không quản lý task |
| employee | EMPLOYEE | EMPLOYEE | Retail xem/tạo order; Service là Kỹ thuật viên xem task/schedule, ghi nhận nhật ký công việc (log labor), không quản lý/gán request hay xem analytics |
| viewer | VIEWER | VIEWER | Xem các tài nguyên được cấp; không có ai.chat hay quyền phê duyệt |
| khách hàng tự đăng ký | Không membership | Không membership | Chỉ cổng khách hàng; không tự tạo tài khoản này qua seed |

Đợt 49 đã thống nhất vai trò Kỹ thuật viên (Gate 70 closed): kỹ thuật viên mang vai trò EMPLOYEE tại xyz-service, được xem task/lịch trình và log_labor cho chính mình; từ chối quản lý request, gán việc, quản lý task và xem báo cáo tài chính analytics. Xem HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md.

## Chuỗi demo có kiểm soát

1. Dùng tài khoản thường và chọn đúng workspace trước khi mở `/noibo/`.
   Kiểm tra quyền xem/tạo/từ chối theo bảng trên, không dùng superuser cho ca từ chối.
2. Chạy nghiệp vụ trên dữ liệu demo được chuẩn bị riêng. Với phê duyệt, chỉ
   thực thi action có contract/payload hợp lệ; người duyệt khác người yêu cầu.
   Khuyến nghị nhập hàng hoặc cân bằng nhân sự không đồng nghĩa đã có action
   tự động an toàn. Không minh họa chúng như giao dịch đã được thực thi.
3. Dự báo: mở đúng run và workspace, giữ kết quả kém baseline; phân biệt
   backtest một bước với đường dự báo nhiều ngày. Không nói seed chứng minh lợi ích thật.
4. Trợ lý: áp dụng `DEMO_FALLBACK_RUNBOOK.md`; đọc nhãn LLM_RESPONSE,
   DETERMINISTIC, NO_CONTEXT/UNKNOWN và nguồn. Không coi kết quả mô phỏng là LLM thật.
5. GIS: khoảng cách địa lý khác tuyến đường; không cam kết traffic hay tuyến
   ngắn nhất tuyệt đối. Ghi nhận lỗi nhà cung cấp thay vì giấu lỗi.

## Bằng chứng hiện có / còn thiếu

`test_seed_demo_safety` kiểm tra chốt môi trường/dữ liệu và output redaction.
`test_role_acceptance_matrix` gọi seed thật chế độ identity rồi kiểm tra quyền.
Đợt 28: 10 test qua; không chứng minh toàn bộ UI hoặc full domain seed.
Chưa diễn tập tất cả vai trò xuyên suốt bằng browser; README/kịch bản cũ còn
cần đối chiếu các phần ngoài phạm vi đợt này. Mục 87 chỉ một phần.

Đợt 30: bổ sung full-seed/forecast completion assertions, test reporting và nhãn
SLA thiếu dữ liệu. Browser đã xem snapshot manager/technician bằng dữ liệu dựng;
không tương đương walkthrough đăng nhập/POST thực tế. Mục 87 vẫn một phần.
