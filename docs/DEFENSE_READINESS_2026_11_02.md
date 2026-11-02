# Rà soát và sửa trước bảo vệ đồ án ngày 02 tháng 11 năm 2026

## Phạm vi và nguồn đối chiếu

Đối chiếu đề cương teacher_review_v2 đã duyệt, có chat realtime và bản tin nội bộ.
Bản trong output/docx_review/teacher_review_v2 và bản Downloads có hậu tố (1)
trùng toàn bộ byte, cùng SHA-256
9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
Chủ dự án xác nhận dùng bản này ngày 02/11. Không sửa Word để che khoảng trống
triển khai; chưa có bản báo cáo/slide bảo vệ cuối nào khác được chỉ định.

Nhánh sửa bắt đầu từ release 1e2850b trong worktree riêng. Workspace chính ổ D
đang có thay đổi của chủ dự án/agent khác, được giữ nguyên. Sổ checklist 97 không
thay cấu trúc hoặc tiến độ. Đây là rà soát phiên bản có ngày, không chứng nhận
tối ưu tuyệt đối, mọi thiết bị hoặc hiệu quả kinh doanh ngoài thực tế.

## Các lỗi đã sửa và kiểm thử tập trung

1. Khách vào website lần đầu chưa có CSRF cookie nên copilot/cart POST bị403:
   shell cấp token đúng cơ chế Django, không tắt CSRF.
2. Tên/thuộc tính sản phẩm, preview import/mapping/suggestion và popup GIS có
   thể chèn HTML: thoát dữ liệu đúng ngữ cảnh, giữ cấu hình JSON có dấu nháy.
3. Giỏ bên hông thay đổi nhưng trang thanh toán giữ số tiền/dòng hàng cũ:
   chặn submit khi đang thay đổi hoặc chưa rõ kết quả, tải lại đầy đủ review,
   giữ dữ liệu khách đang nhập, không tự replay POST hoặc fallback sang GET.
4. Race timeout/ghi session muộn: token ký gắn session/user/workspace và
   ID/số lượng/giá/method/tổng tiền được kiểm dưới khóa sản phẩm trước khi ghi.
   Review sai trả409, giữ bản nháp đã escape và yêu cầu chốt lại. Không tự nhận
   GET sau timeout là bằng chứng POST đã dừng. JSON review GET không ghi session
   nên không ghi đè cart mới; hai thứ tự SessionStore.save có regression thật.
   UI luôn review=1; direct POST headless cũ ngoài UI vẫn giữ hợp đồng legacy,
   không được gọi đây là cưỡng chế review tuyệt đối cho mọi API client.
5. Bỏ GET làm thay đổi cart sau khi rà toàn bộ caller hiện hành đều POST;
   GET trả405, POST giữ CSRF. Version drawer GET để không hiển thị response cũ.
6. Guest copilot trỏ sai trang chỉ dành tài khoản: dùng route success theo
   session sở hữu hiện có; khách khác vẫn bị chặn.
7. Task import dùng tên trường không tồn tại: sửa assigned_to, giữ kiểm tra
   workspace và giao dịch canonical. Partial/zero import giữ số lỗi/chi tiết,
   không báo xanh hoàn tất hoặc reload làm mất chẩn đoán.
8. GIS page chọn workspace khác session nhưng API không gửi selector: mọi fetch
   gắn workspace đã được cấp quyền của trang; không fallback tenant trái quyền.
9. is_staff không đủ quyền xem PII tọa độ khách: giữ explicit permission và
   superuser hiện hành, bổ sung test staff không quyền.
10. Chat thiếu cách xem quá50 tin cũ: thêm before_id tối đa50, con trỏ lịch sử
    tách polling, giữ draft/scroll, thông báo lỗi/thu hồi quyền. Hai HTTP client
    manager/employee độc lập gửi hai chiều, reload và kiểm cách ly trên TEST.
11. Forecast chưa đi vào rule như đề cương: dùng ForecastRun/ForecastResult đã
    lưu cho luật doanh thu giảm trên10% minh họa. Chỉ nhận daily workspace-wide,
    nguồn/model rõ, đủ14 holdout quan sát và7 ngày so sánh có đơn COMPLETED.
    Không bịa ngày thiếu, không huấn luyện trong rule, không tự tạo action.
    Historical phải opt-in, có nhãn, không chấp thuận như hành động hiện tại.
    Trạng thái ngày được kiểm lại lúc đọc/chấp thuận, kể cả qua nửa đêm.
12. Phục hồi chính sách demo đã được chủ dự án chốt nhưng chỉ tồn tại ở source
    local chưa phát hành. Ba trang đọc công khai, consent/footer/copilot trỏ
    đúng chính sách thay vì Giới thiệu. Email mới gắn phiên bản/link sau khi
    tính key dedup gốc; retry không đổi snapshot cũ. AT-DEMO-1.1 chỉ cập nhật
    ngày/phiên bản và giải thích JSON model guarded lưu trong ForecastRun,
    không biến LocalStorage thành S3 hoặc đưa ra cam kết thương mại mới.

Kiểm thử tập trung hiện có (các nhóm chồng lặp, không cộng thành full suite):
public sau sửa empty-cart121/121OK12,479s + JS22/22; mapping/GIS74/74OK12,391s + JS9/9;
chat66/66OK12,809s + JS9/9 và5 nhóm transport cũ; forecast/rule/approval99/99
OK38,517s + JS5/5. Các RED, lỗi fixture trung gian và kết quả GREEN được giữ
riêng trong output và báo cáo từng task. Fresh reviewer của từng nhóm đã duyệt
sau các vòng sửa; không coi self-review hoặc tên file GREEN là bằng chứng.
Nhóm phục hồi chính sách249/249OK20,833s và JS22/22PASS463,3033ms; giữ nguyên
15 test/assertions cũ, chỉ thêm2test. Không cộng vào full1574 trước integration.

Whole-branch review tìm thêm trường hợp cart bị xóa hết sau bản chốt: đường
strict trả409 và giữ bản nháp, kể cả sản phẩm vừa bị vô hiệu hóa; nút đặt mua
disabled khi rỗng. Direct POST legacy vẫn redirect như cũ. Reviewer đã đối chiếu
delta850d1eb và không thấy regression mới trong phạm vi này.

## Dependency bảo mật và môi trường kiểm thử

Lượt full đầu ở1c0f614 đạt1564/1564OK292,720s,886 source files không đổi;
đây là bằng chứng trước sửa empty-cart và trước nâng dependency, không phải
chứng nhận bản cuối. Kiểm toán sau đó phát hiện169 dòng/126 advisory duy nhất
trên Python chung,19 dòng/16 advisory trên môi trường công cụ. Đó là hai
inventory khác nhau; không cộng trùng hoặc gọi tất cả là khai thác được.

Nguồn đã nâng floor Django theo từng nhánh vá5.2.18/6.0.9/6.1.2, loại rõ các
patch cũ ở nhánh6.0/6.1; DRF/Pillow/pypdf và transitive HTTP/Daphne có floor
bảo mật tương ứng. CI/build bootstrap pip26.2.2; giữ audit và toàn bộ test cũ.
8 test policy offline đã thấy RED trước sửa và GREEN sau sửa; chúng không thay
audit môi trường thật. Python chung không được nâng/xóa; tạo venv riêng hoàn
toàn để kiểm chứng, giữ phiên bản trực tiếp NumPy/pandas/scikit-learn/XGBoost
của baseline. Transitive như SciPy/joblib được resolver cập nhật và có inventory
riêng; không chạy lại hoặc ghi đè kết quả nghiên cứu cũ.

Đối chiếu bản vá từ [Django](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/),
[Pillow](https://github.com/python-pillow/Pillow/security/advisories/GHSA-78g4-xqwv-q3g8),
[pypdf](https://github.com/py-pdf/pypdf/security/advisories/GHSA-5849-834g-hvw5)
và các maintainer. Twisted có advisory IMAP ghi chưa có patched version; source
dự án không có IMAP listener/import tương ứng. Không suy ra upstream đã vá chỉ
vì bản mới ngoài khoảng affected ghi trong feed; rủi ro dư này tiếp tục được
ghi rõ, không ignore advisory để đạt số0. Report chi tiết và inventory local
nằm tại output/defense_dependency_triage_20261102.md. Audit/full trên venv mới
đã có receipt riêng; chưa gọi production đã nâng dependency.

Full tại8b8ca8095ee6523deba37dc14b66466977a9af49 trên venv mới đạt1574/1574
OK355,253s,887 source files không đổi, không skip; database TESTc096e9a692da4719
tự hủy. Audit chính venv80 distribution:0advisory/0skip; pip check đạt. Django
check0issue và migration drift No changes detected trên TEST riêng. Bandit apps/
config khôngmigrations:0finding/0error; secret-pattern guard880file:0finding,
không phải kiểm toán toàn bộ lịch sử secret. Các receipt tại
output/defense_verification/20261102T022653Z và output/defense_*_20261102.*.
Phiên bản kiểm chứng: Django6.1.2/DRF3.18.3/Pillow13.0.0/pypdf6.21.4,
Twisted26.10.0/autobahn26.10.2; đây là local, không suy ra inventory production.

Đối chiếu bổ sung tìm thấy chính sách demo chủ dự án đã chốt ngày12/10 chỉ có
ở workspace chính chưa phát hành. Phần này đã được ghép từng hunk, không chép
đè cả views/checkout/shell đã sửa. Bản1.1 chỉ sửa mô tả storage model hiện tại
và phiên bản/ngày; không tự thêm cam kết thương mại. Lượt full1574 phía trên
trước integration chính sách, nên bản cuối cần receipt source-freeze riêng.

## Đối chiếu các nhóm yêu cầu Word

| Yêu cầu đề cương | Triển khai và kiểm chứng | Giới hạn giữ rõ |
|---|---|---|
| Khách hàng đăng ký/xác minh/đặt hàng/dịch vụ/tra cứu | public_web, ownership, email outbox; regression nguồn và HTTP entry pages | Không gửi thêm email hoặc đơn thật trong đợt này |
| Điều khoản và quyền riêng tư demo | Nguồn AT-DEMO-1.1, ba trang đọc, link consent/help/email và snapshot regression | Không phê duyệt SOP thương mại hoặc chứng nhận pháp lý |
| Quản lý Retail/Service/dashboard/báo cáo | Canonical /noibo/, services/selectors và API phân quyền | HTTP entry/detail không thay thế mọi thao tác CRUD visual |
| Nhân viên theo dõi công việc được phân công | EMPLOYEE seed có view_request/task/schedule; UI/API hiển thị công việc của workspace | Không có yêu cầu Word về trang riêng chỉ-my-tasks; không tự đổi role/grants |
| Integration và Mapping | Staging/preview/canonical apply, Task và partial outcomes được sửa | Không nhập file vào production |
| RAG và Gemini có nguồn/chế độ rõ | Knowledge ingest/retrieval/tool/synthesizer có code; no-key deterministic hiện hành | Chưa có live Gemini/embedding evaluation theo lựa chọn chủ dự án |
| XGBoost, baseline, time split/backtesting | Engine/thực nghiệm/provenance/guarded selector đã có; không sửa kết quả cũ | MA7 có thể được chọn; dữ liệu lịch sử, không bảo đảm thắng mọi chuỗi |
| Forecast + luật tạo khuyến nghị có lý do | Nối forecast đã lưu vào advisory, nguồn/run/model/threshold/so sánh rõ | Ngưỡng minh họa, không thương mại/causal guarantee; historical không executable |
| Tool + Human Approval + Audit | Hợp đồng xác định, người duyệt độc lập, idempotency/atomic/audit có regressions | Reorder/workload chưa đủ contract tiếp tục advisory |
| GIS lớp/khoảng cách/bán kính/cách ly | PostGIS/reference, explicit page selectors, PII/escaping được sửa | Không là GPS thiết bị hoặc engine giao thông thời gian thực |
| Chat realtime + lịch sử + bản tin | Polling3s, history paging, bulletin scoped create/edit/read, hai client TEST | Không WebSocket; browser live hai phiên chưa quan sát đợt này |
| Bàn giao source/dữ liệu/kiểm thử/báo cáo | Có source và hồ sơ ngày cụ thể; đợt này thêm matrix/regressions | Chưa nghiệm thu báo cáo/slide nộp cuối ngoài đề cương |

## HTTP production trước phát hành sửa

Probe read-only 02/11 08:34–08:35 giờ Việt Nam:12 public GET và29 mục đọc mỗi
vai trò manager/employee, chỉ POST đăng nhập thông thường. Không5xx/lỗi mạng;
manager28 đọc được và1 selector trái quyền403; employee7 module thiếu capability
trả403, selector trái quyền403, các mục được cấp quyền trả200. Public homepage
thiếu CSRF cookie đúng lỗi baseline chưa deploy lúc kiểm. Không gửi dữ liệu
nghiệp vụ, gọi forecast GET có thể provision config, logout thu hồi token hoặc
lưu token/cookie/PII trong evidence. Timings một lượt không là load benchmark.
Chi tiết: output/defense_http_smoke_20261102.json và report riêng.

## Bản tích hợp cuối và cổng phát hành

Full tại fbb85bb45e072a307e9d0cbf1c2c4871537bfad8 đã đạt **1591/1591**,
337,286s, không skip;892tệp nguồn không đổi trong lượt. TESTaafe549c25df40c8
tự hủy. Bằng chứng: output/defense_verification/20261102T024558Z/result.json,
source_before.json và django.log. Đây là bản có cả chính sách1.1, không cộng
các nhóm focused. Mật khẩu hasher nhanh và compatibility fixture legacy chỉ
ở process TEST; runtime strict/RBAC không đổi. AggregateJS73/73PASS2146,5141ms,
cùng5nhóm transport; security scan bản cuối Bandit0finding/0error và
884file secret-pattern0finding. Không suy ra không còn mọi lỗ hổng.

Sau lượt full chỉ cập nhật ba tài liệu bằng chứng/kế hoạch: báo cáo này,
CURRENT_STATUS và plan; không đổi app/test/asset/CI/dependency. Các test tài liệu
và framework/drift được kiểm lại riêng. Phiên bản phát hành có thể khác SHA
full ở commit receipt-only; closure đối chiếu hash mã chạy với source_before.

Push/CI/deploy đúng SHA và HTTP sau deploy là cổng bên ngoài riêng, không tự
suy ra từ local. Kết quả cuối được lưu create-only tại
D:/AlphaTech_Private/defense_readiness_20261102/BAO_CAO_BAO_VE_2026_11_02.md
và closure_<SHA>.json sau khi cổng thực sự đạt; không dùng tên đường dẫn này
làm bằng chứng trước khi tệp tồn tại. CI quality.yml là focused/coverage/security,
không gọi đó là full-suite GitHub. Không thay đổi model/kết quả dự báo hoặc giao
dịch; ngoại lệ hai quyền đọc EMPLOYEE được chủ dự án duyệt được ghi rõ dưới đây.

Browser UAT bị chặn bởi công cụ: CUA không ghi được kernel assets (path missing),
reset/retry vẫn lỗi; Node REPL độc lập cũng không khởi tạo. Đó không phải HTTP500
của dự án. Không dùng HTTP/VM để giả mạo browser hoặc khẳng định giao diện mượt
trên điện thoại. Cần kiểm visual sau khi công cụ hoạt động lại; không yêu cầu
restart ứng dụng giữa tác vụ nặng vì lần trước đã gián đoạn tiến trình.

## Bổ sung từ Chrome thật và phân quyền production

Release06e9d62 đã có CI nhánh41380138662 và main41380888222 cùng success;
RenderFree dep-dbjvrfgu01pc738lb1g0 live đúng SHA, health200. Probe94request
khách/manager/employee có2assertion chưa đạt: EMPLOYEE tasks/schedules403.
Không đổi kỳ vọng thành403 để làm xanh. Đối chiếu auth/me và plan chỉ đọc cho
thấy roleEMPLOYEE thiếu2grant nguồn seed đã có. Chủ dự án đồng ý rõ việc thêm
service.view_task/service.view_schedule cho role dùng chung; chỉ thêm2M2Mrow,
giữ mọi grant cũ/userflags/membership và auditSYSTEM_JOB113. Retry no-op không
thêm audit; profile thực tế đã có2quyền đọc, vẫn không có manage/assign.
Plan/apply/19testoperator/ảnh hưởng1active membership mỗi2workspace nằm ở
private/employee_role_sync; không reset hoặc thay dữ liệu bán hàng.

Theo yêu cầu thử cách khác, đã dùng Chrome có sẵn156.0.8078.76 qua Playwright
CLI headless, phiên riêng không đọc profile/cookie của người dùng. Desktop1365
và mobile-size390 kiểm4scenario,64assertion:62đạt,2lỗi cùng một nút retry.
Video nền phát thật, đổi giỏ/tổng/phí/draft đúng; manager login và2poll chat
giữ draft, history3tin/exhausted,5trang nội bộ đọc được ở hai kích thước.
Không lỗi JS/HTTP trong lượt cuối; mobile emulation không là điện thoại thật.
Không gửi đơn/email/chat/bản tin/RAG/approval; chỉ giỏ phiên guest và login.

Hai lần login đầu lỗi do parser credential của driver, không phải tài khoản
hoặc app; đã sửa parser theo block chính xác, giữ nguyên kết quả lỗi cũ. Không
reset mật khẩu. Headercart là link sang trang giỏ theo hợp đồng hiện có, nên
không gọi hàm ẩn để giả kiểm drawer ngay trên checkout. >50tin chat live chưa
được dùng; testcase123tin vẫn là TEST riêng, không sản xuất100tin trên production.

Lỗi retry: hidden=true nhưng stylesheet nút ép display:flex. CSS sửa chỉ
`#checkout-summary-retry[hidden]`, không đổi animation/logic. Source/render RED1
được giữ, focused57/57OK7,444s vàJS22/22PASS228,7732ms sau sửa. Chrome thử CSS
tạm thời12/12: thành công ẩn nút; lỗi GET thật thì hiện retry/chặn submit/xóa
token; khôi phục mạng và click retry thì phục hồi. Đây là hypothesis chưa deploy,
không dùng nó thay kiểm browser sau phát hành. Full/CI/live/probe/browser của
bản CSS cuối sẽ có receipt riêng trong hồ sơ private; không mượn1591 hoặc
62/64 để gọi mọi cổng hoàn thành.

## Quyết định phạm vi vẫn giữ nguyên

Không bật API LLM trả phí, không tạo giao dịch giả nâng điểm, không thay ảnh SKU,
không dựng worker trả phí/S3, không sửa dữ liệu hoặc kết quả forecast cũ. Local
storage, Render Free, historical forecast và các lựa chọn backup/offsite trước
đây vẫn là giới hạn đồ án đã chốt, không tự biến thành chứng nhận production.
