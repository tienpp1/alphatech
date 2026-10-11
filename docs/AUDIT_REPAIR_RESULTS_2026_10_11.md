# Kết quả sửa 36 phát hiện audit — 11/10/2026

Phạm vi riêng F01–F36 của `output/live_audit_20261011/BAO_CAO_KIEM_THU.md`.
Không thay đổi cấu trúc/tiến độ checklist 97 mục. Mã nguồn, test, cấu hình và
bằng chứng local là các mức khác nhau; không có tuyên bố mọi chức năng production
đã nghiệm thu 100%. Những sửa đổi của agent khác có sẵn được giữ nguyên.

## Quyết định của chủ dự án

- RAG production giữ **DETERMINISTIC / NO_API_KEY**, không kích hoạt Gemini live.
- Forecast giữ dữ liệu lịch sử học thuật. Không phát sinh giao dịch synthetic
  trong database nghiệp vụ để làm dữ liệu mới hơn hoặc nâng điểm mô hình.
- Cho phép ảnh AI: một minh họa nhóm thiết bị, ghi rõ không phải ảnh sản phẩm
  thực tế; ảnh ProductImage thật luôn được ưu tiên. Không tạo 44 ảnh giả SKU.
- Cho phép chuyển HOME_DELIVERY sang strict sau kiểm tra tồn kho chỉ đọc.
- Render Free, async worker production tắt và Local Storage giữ nguyên phạm vi.

## Đối chiếu toàn bộ phát hiện

“Sửa local” nghĩa là có thay đổi và kiểm thử phù hợp; không đồng nghĩa có UAT mới
trên production. “Giảm rủi ro” không nghĩa vấn đề chất lượng/dữ liệu đã biến mất.

| ID | Kết quả kỹ thuật / giới hạn |
|---|---|
| F01 | Approval chuyển trạng thái qua canonical service; chặn transition sai, hoàn reservation đúng một lần và rollback atomic khi lỗi. |
| F02 | Phạm vi chốt deterministic; metadata/chế độ thật được giữ. Không có chứng nhận Gemini live hoặc semantic embedding. |
| F03 | Thay tỷ lệ vùng hard-code bằng grid PostGIS/WebMercator 1km; đếm tọa độ thật, công khai ticket thiếu vị trí. Không gọi grid là ML clustering. |
| F04 | Lookup khách hàng chính xác theo workspace; không tìm thấy/mơ hồ không lấy khách đầu tiên. |
| F05 | Forecast/top-products query sai và JSON primitive/non-text chat/bulletin trả 400, không 500 hoặc ghi nghiệp vụ. |
| F06 | Copilot public lọc laptop/ngân sách, nhận đúng Cat6 và câu đặt/theo dõi đơn; policy nhiều phần không bị bỏ sót hoặc bịa cam kết. Vẫn rule-based, không LLM. |
| F07 | Chỉ phát hiện số khác nhau ở cùng câu chuẩn hóa, heading/hiệu lực và đơn vị rõ; bỏ ordinal/ID. Đây là guard bảo thủ, không bộ phân loại mâu thuẫn ngữ nghĩa đầy đủ. |
| F08 | Giảm retrieval mua hàng bị loãng; query số liệu chỉ dùng tool nếu không hỏi tài liệu. Service summary có đủ phân bố trạng thái, cùng phạm vi/tổng. Không tuyên bố mọi câu hỏi RAG đều đúng. |
| F09 | Nguồn legacy mặc định UNVERIFIED; giữ authority/hiệu lực trong citation và prompt, không xem SOP học thuật là phê duyệt thương mại. Chưa có văn bản doanh nghiệp ngoài dự án. |
| F10 | Giảm rủi ro: so từng MAE/RMSE với baseline tốt nhất và hiển thị R² âm. Không huấn luyện lại để che run yếu; chất lượng mô hình cũ chưa cải thiện. |
| F11 | Snapshot lịch sử/cũ/unknown được gắn nhãn với ngày/tuổi dữ liệu; không chuyển ngày dự báo cũ thành tương lai giả. Giữ dữ liệu học thuật theo lựa chọn chủ dự án. |
| F12 | Recommendation cũ có review_state/freshness, không được accept như đề xuất mới hợp lệ. NO_DATA là advisory, không bằng chứng doanh thu sụt giảm. |
| F13 | Rule so COMPLETED theo order_date/kỳ nghiệp vụ với kỳ trước; bỏ điều kiện MAE tốt hơn ⇒ doanh thu giảm và tiêu đề chi nhánh giả. |
| F14 | Hai tool dùng permission canonical retail.view_product/service.view_employee; không bypass membership/RBAC. |
| F15 | Chi tiêu/tổng lịch sử lấy toàn bộ đơn COMPLETED; 10 dòng là sample chi tiết, không cộng CANCELLED như tiền đã chi. |
| F16 | Margin theo Category thật; lọc ID/code/name chính xác, unknown/ambiguous trả rỗng và yêu cầu làm rõ. Không nhóm “other” dưới tên category đầu tiên. |
| F17 | Revenue COMPLETED tách pipeline; margin là doanh số dòng hàng và current-cost estimate. COGS lịch sử chưa có, bỏ fallback 80% và target SOP giả. Category subset không được đối soát với tổng đơn toàn workspace. |
| F18 | Contract-supported recommendation → approval → reviewer tách biệt → execution/audit được test local. Advisory không tự mutation; stock reorder/workload chưa có contract vẫn không map. |
| F19 | Lịch sử gọi API scope owner/workspace/RBAC, phục hồi USER/ASSISTANT và nguồn/tool. New chat reset session; timeout/race giữ trạng thái/draft. Escape metadata citation chống HTML injection. |
| F20 | Horizon/điểm hiển thị theo run thật, thêm lựa chọn SKU/category/branch. Không mặc định 14 ngày. |
| F21 | Cải thiện/xấu đi đúng dấu/màu; baseline comparison không lấy COMPLETED làm chất lượng. |
| F22 | Thời gian dashboard và lịch sử dùng Django active timezone; không lệch UTC/+07 trong cùng lượt chạy. |
| F23 | Telemetry bỏ OPTIMAL/100%/CONNECTED tĩnh; phiên bản đọc runtime, count không gọi là artifact đã chạy hoặc accuracy. |
| F24 | Nhãn database snapshot/HTTP health đúng phép đo. Version query PostGIS thật nhưng không benchmark spatial inference; không tự nhận realtime zero-polling. |
| F25 | Minh họa AI static đã tạo và gắn catalogue/detail có caption/alt. ProductImage thực tế của 44 SKU vẫn thiếu; không bổ sung bản ghi giả. |
| F26 | Giỏ rỗng phí/tổng bằng 0. |
| F27 | Selection dịch vụ blank/sai/không tồn tại bị từ chối trước tạo ticket; không fallback dịch vụ đầu tiên. |
| F28 | Email sai được báo lỗi rõ trước ghi dữ liệu; email trống xử lý theo recipient policy đã có. |
| F29 | Nonce gắn request_number unique hiện có, atomic dedup và PRG; giữ ownership/session và email riêng. Có concurrent test, không tạo model song song. |
| F30 | Liên hệ dùng lời xác nhận tiếp nhận, không hứa phản hồi 24 giờ chưa được duyệt. |
| F31 | GPS không xác định/NaN/>100m bị reject trước đặt origin/gọi routing. Có test callback JS; chưa UAT GPS thiết bị mới trong phiên sửa này. |
| F32 | Browser bị chặn nội bộ thấy trang 403 tiếng Việt với đường về khách hàng; API vẫn JSON 403. |
| F33 | Roster/dịch vụ chat chỉ active internal-eligible; loại Google-linked/VIEWER/inactive, không sửa grant của họ. |
| F34 | Hero không còn bọc nội dung trong layer trang trí inert; contrast/launcher inline ở giỏ/checkout, recommendation dễ đọc; grid checkout có min-width/minmax bảo vệ mobile. Không phải chứng nhận WCAG toàn trang. |
| F35 | Chỉ trả skills/labor/availability ghi nhận, chứng chỉ/tuân thủ chưa xác minh; bỏ suy diễn theo tên, OT×6.5, ca đêm/ISO/bồi hoàn giả. |
| F36 | Preflight strict read-only và test reservation/concurrency. Render lưu HOME_DELIVERY_FULFILLMENT_POLICY=strict; cần deploy và UAT strict checkout hiện hành. |

Follow-up hữu hạn: stockout phân biệt MISSING_BALANCE/NEGATIVE_BALANCE với
RECORDED_BALANCE=0; counter verified_out_of_stock/inventory_unverified/demand
unassessed và ngày nguồn có trong API/UI/AI. Thiếu dữ liệu không được gọi “an toàn”.
Recommendation cũng bỏ tạo cảnh báo hết hàng từ balance thiếu/âm. Nhu cầu cũ,
không rõ hoặc legacy là advisory MEDIUM, không đủ căn cứ accept; số dư ghi nhận
0 vẫn được phân biệt. Giải thích nêu heuristic/giả định lead time, không gọi là
XGBoost đã kiểm chứng hoặc cam kết cung ứng. Không retrofit các dòng lịch sử.
Đối sánh chỉ một baseline không còn được mô tả là vượt hai baseline.
Mutation parser từ chối ID/giá/số lượng bị cắt một phần, nhân sự E1≠E10,
trạng thái đích mơ hồ và scheduler thiếu ticket_id. Không chọn entity đầu tiên.

## An toàn dữ liệu và cấu hình

Neon preflight: 44 sản phẩm active × 3 chi nhánh, mỗi chi nhánh 44 StockBalance;
missing pairs=0, negative=0, BR-D1 có 5 số dư 0. Đó là dữ liệu ghi nhận, không
kiểm kê vật lý. Không cập nhật số dư, khách hàng, tài liệu cũ hoặc giao dịch.
Render config PUT chỉ đổi một biến fulfillment; các biến khác được so trước/sau.
Local .env (ignored) và .env.example/render.yaml đặt strict; runtime default vẫn
legacy cho môi trường chưa được đối chiếu. Không sửa migration/schema/model.

Đã chạy system check và migration drift trên database test mới: 0 issues,
No changes detected. Test dùng config.settings_evidence_test, database loopback
ngẫu nhiên và tự hủy đúng DB test của lượt chạy; không reset database nghiệp vụ.
Email test locmem và provider mô phỏng không là bằng chứng inbox/live LLM.

## Kiểm thử đã ghi log

Các lượt chồng lặp, **không cộng thành số test duy nhất**:

| Lượt / log trong output | Kết quả |
|---|---|
| audit_repair_root_final_retry.log | 55/55 OK, 265.739s: root/RAG/Google boundary/collaboration. |
| public_repairs_20261011_extended.log | 111/111 OK, 369.853s: public/strict/concurrency/OAuth/outbox. |
| public_repairs_20261011_final.log | 69/69 OK, 121.789s: public/cart/email. |
| public_repairs_20261011_image_and_hero_retry.log | 47/47 OK, 128.702s: ảnh/hero/policy/ecommerce. Legacy chỉ trong process compatibility; strict tests có override riêng. |
| forecast_rec_telemetry_repair_tests_20261011.log | 41/41 OK, 154.893s. |
| stockout_final_scope_tests_20261011.log | 36/36 OK, 12.903s. |
| live_audit_20261011/governance_tools_regressions.log | 79/79 OK, 44.425s trước hai regression cuối. |
| live_audit_20261011/governance_tools_final_selector_tests.log | 38/38 OK, 2.402s, selectors và status_distribution cuối. |
| audit_repair_final_integration_tests.log | 150/150 OK, 129.782s; check/drift, history, tools/approval, forecast/stockout/strict. |
| audit_repair_javascript_final.log | 23/23 OK, 475.7684ms; lịch sử thực từ template và GPS callback/routing thực từ source. |
| audit_repair_last_changes_retry.log | 68/68 OK, 132.665s; renderer, demo cũ, selectors/status và layout contract. |
| audit_repair_static_layout_tests.log | 2/2 OK, 0.007s; static storage và intrinsic layout. Không thay browser QA. |
| recommendation_evidence_release_regressions_20261011.log | 54/54 OK, 100.393s; evidence gate, stockout và recommendation→approval. |
| phase11_fixture_freshness_final_regressions_20261011.log | 52/52 OK, 69.514s; fixture ngày tương đối, giữ assertion về nguồn giao dịch và kỳ recommendation. |
| live_audit_20261011/discovery_isolation_regressions.log | 13/13 OK, 37.512s; registry model test riêng, migration drift trước/sau discovery đều {}. |
| acceptance_verification/20261011T142548Z/django.log và result.json | 1361/1361 OK, 295.775s; fingerprint 752 file nguồn không đổi, exit 0, DB test tự hủy. |
| repair_release_snapshot_tests_v2_20261011.log và repair_release_snapshot_result_v2_20261011.json | 1349/1349 OK, 378.022s; export Git index không có .env/untracked files; index không đổi trong lượt, DB test tự hủy. |

Lệnh chính (Python là .venv-acceptance/Scripts/python.exe):

```powershell
python manage.py test tests.test_live_audit_rag_collaboration tests.test_ai_history_audit tests.test_audit_governance_tools_regressions tests.test_approval_state_integrity tests.test_tool_registry tests.test_enterprise_qna tests.test_forecast_recommendation_audit_repairs tests.test_stockout_source_freshness tests.test_retail_stockout_prediction tests.test_home_delivery_fulfillment --settings=config.settings_evidence_test --noinput -v 1
node --test tests/ai_assistant_history.test.cjs tests/branch_finder.test.cjs
python -m compileall -q apps config tests
python scripts/check_release_secrets.py --output output/audit_repair_secrets_final.json
git diff --check
```

Secret scan known patterns: 839 source files, findings=[]; không phải kiểm tra
toàn lịch sử/entropy hoặc chứng minh secret đã rotate ở provider.
Bandit theo scope CI apps/config, bỏ migration: findings=[]/errors=[] sau sửa
false positive B105 cho nonce rỗng (không phải credential), có rationale cạnh dòng.
Không tắt rule toàn cục; một suppression riêng B105 được ghi trong báo cáo scan.
Log audit_repair_bandit_release_retry.json. Lượt command trỏ config không tồn tại
được lưu như lỗi thao tác, không gọi đó là scan thành công.

Lỗi trung gian được giữ: root fixture email unique/Category thiếu và context
router bỏ nhầm hướng dẫn; public47 có 5 checkout failures khi .env đổi strict
nhưng fixture legacy không có kho; compatibility được tách ở tiến trình test,
không giảm strict ứng dụng. Cross-system154 có 1 failure trong demo yêu cầu
nhãn “Bằng chứng”; renderer được sửa, assertion giữ nguyên. Governance regressions
đã tái hiện lỗi trước sửa. Không xóa/skip/nới test để gọi kết quả xanh.
Lượt audit_repair_last_changes_tests.log có 66 test thực PASS nhưng một test label
không tồn tại do gọi sai tên; không báo 67/67. Lượt retry đúng tên đạt68/68.

Full-suite đầu: 1360 tests trong 260.147s, FAILED (2 failures, 1 error), nguồn
không thay đổi trong lượt chạy. Log ở acceptance_verification/20261011T141126Z.
Nguyên nhân đã đối chiếu: fixture Phase11 hard-code ngày cũ; manifest hồ sơ chưa
liệt kê 6 test mới; DummyTenantEntity của test isolation đăng ký vào app registry
thật khi discovery gây migration drift giả. Sửa fixture/manifest/registry riêng,
không bỏ hoặc nới assertion, không thêm migration nghiệp vụ. Thêm một regression
discovery nên lượt đầy đủ tiếp theo có 1361 tests.

Lệnh full-suite dùng scripts/run_acceptance_verification.py --fast-test-passwords:
MD5 chỉ trong tiến trình database test dùng một lần, không đổi password hasher
ứng dụng. HOME_DELIVERY_FULFILLMENT_POLICY=legacy chỉ ở tiến trình kiểm tương thích;
các test strict có override riêng và cấu hình local/Render vẫn strict. Wrapper
kiểm fingerprint mã nguồn trước/sau. Lượt password-hasher mặc định bị ngắt trước
kết luận được giữ log riêng, không được coi là PASS.

1361 là suite của WORKTREE LOCAL, gồm 12 test trong ba module untracked có sẵn
(backup mã hóa/R2/restore safety). Các file này thuộc phần việc khác, được giữ
nguyên và không tự stage. Không gọi 1361 là số test giống hệt checkout GitHub;
bản index được kiểm riêng như bảng trên. Không có skips trong hai log lượt PASS.

Export index đầu có 1348 tests, FAILED (2 failures, 1 error), 385.097s: lệnh stage
trước đó chưa đưa ba sửa fixture/manifest/registry vào index. Log giữ ở
repair_release_snapshot_tests_20261011.log; không gọi đó là PASS. Bản v2 đã stage
đúng và PASS1349; khác worktree12 test untracked được giữ nguyên. Tree kiểm:
86d15ec59ee0b93a1ac68729c24c152bfb09880b. Sau lượt kiểm chỉ bổ sung biên bản kết
quả/status, không đổi code/test. Scan ở export thiếu .git trả files_scanned=0,
không được dùng làm bằng chứng; scan workspace839 file vẫn findings=[].

## Browser và bằng chứng phát hành

Browser dùng fixture LOCAL SYNTHETIC trong database test riêng: chuyển hai
history, new chat, ảnh+disclosure, giỏ hàng, checkout, bộ lọc SKU/category/branch,
telemetry snapshot. Không gửi đơn checkout hoặc email thật từ fixture.
Ảnh QA ở output/audit_repair_20261011_browser. Lượt fixture cũ hết timeout/cache
CSS cũ không được coi là PASS; dùng namespace static mới để kiểm đúng bản sửa.
Browser v5 xác nhận stylesheet 181 rules được tải; public base sử dụng static
storage thay đường /static/ hard-code (tôn trọng manifest/cache version production).
Viewport390×844: document scrollWidth375, form x24→351.2, grid327.2px;
không tràn ngang, control/summary/inline launcher đọc được. Lưu checkout-mobile.png,
checkout-mobile-viewport.png và catalog-desktop.png mới. Không submit đơn.
Fixture kết thúc OK731.399s và tự hủy đúng DB test riêng; viewport đã reset.
Full-suite local đã PASS như trên; rollout/CI sẽ được ghi sau, chưa suy ra live UAT.

Ảnh tạo qua imagegen: static/public/images/technology-illustration-ai-v1.png,
1.658.922 byte, nhóm laptop/monitor/router/tower không brand. Prompt tóm tắt đầy
đủ ý: “Clearly stylized clean 3D illustration of unbranded technology devices,
laptop, monitor, router and desktop tower, light neutral background, no text,
logos, specifications, certification or claims representing a real SKU.”
Không dùng ảnh AI để khẳng định thông số/mẫu hàng, không tạo ProductImage giả.

## Các giới hạn chưa được sửa bằng việc làm test xanh

1. R² âm/kém baseline vẫn hiện hữu; dữ liệu học thuật cũ không được biến thành
   doanh thu thật. Cần dữ liệu thực đủ mới và đánh giá ngoài mẫu nếu muốn vận hành.
2. No live Gemini/semantic embedding theo lựa chọn chủ dự án. RAG không bảo đảm
   đáp ứng mọi câu hỏi, guard mâu thuẫn là bảo thủ chứ không hiểu ngữ nghĩa toàn diện.
3. Chưa có policy thương mại/COGS lịch sử/chứng chỉ nhân sự đã xác minh ngoài đồ án.
4. ProductImage thật còn thiếu; asset AI static chỉ cải thiện phần minh họa.
5. GPS thật, checkout strict/approval animation/email hai inbox và recommendation
   mutation UAT cần kiểm trên deployment mới. Không gọi local fixture là UAT.
6. Full suite worktree local đã PASS, không chứng nhận load test, restore/offsite/
   media bền vững mới trong phiên này; không mở worker/paid service hoặc action
   contract đã cố ý chưa map.

Kết luận: hoàn tất xử lý hữu hạn các lỗi mã nguồn và nhãn dữ liệu trong audit theo
phạm vi đã chốt; không chứng nhận toàn bộ hệ thống production hoặc sửa chất lượng
XGBoost chỉ bằng thêm cảnh báo. Sổ 97 mục không thay đổi.
