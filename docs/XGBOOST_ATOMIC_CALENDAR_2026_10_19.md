# XGBoost V4 — chọn nhóm đặc trưng lịch nguyên vẹn

Ngày 19/10/2026. Thử nghiệm trong worktree riêng
`C:/Users/anhbe/.codex/worktrees/xgb-synthetic-benchmark/ai_business_platform`,
base `4f3c6ab1d043268bb615d6c9f1078b0350cbb52a`. Không thay production,
Neon, dữ liệu nghiệp vụ, cấu trúc CSDL hay sổ97. Chưa commit/push/deploy.

## 1. Kết luận

V4 đã hoàn tất 100 final case và **đạt 10/10 cổng chất lượng khóa trước**.
99 case thắng MA7, 0 hòa, 1 thua; primary mean per-case unrounded MAE ratio/MA7
là 0,6156384796877542, tương ứng giảm 38,436152% MAE tương đối. So với V2
trên cùng 100 case, mean per-case V4/V2=0,9969403605718969, cải thiện 0,305964%.
Giữ đúng nhóm lịch tuần/xu hướng/đổi mức của V2, không tái phạm preservation
FAIL của V3. Đây không phải mức “độ chính xác38,44%” hay thắng mọi dữ liệu.

Phạm vi 100% là **đủ cổng hữu hạn đã khóa**, không phải 100/100 case thắng hoặc
dự báo đúng 100%. Case noise2236 vẫn kém MA7 khoảng 0,689438% và được giữ nguyên;
không chỉnh tiếp model trên final này. Audit độc lập và full regression đã PASS;
không nghiệm thu triển khai production hoặc toàn bộ hệ thống từ kết quả offline.

## 2. Chẩn đoán trước khi thay đổi

V1 kém MA7 tổng hợp12,0067%. V2 sửa bằng residual chuẩn hóa và dự báo direct,
đạt cổng riêng nhưng còn case noise1912 kém MA7 khoảng1,1342%. V3 chọn đặc
trưng lịch theo quá khứ đã giúp noise1912 thắng MA7; tuy nhiên V3 không đạt
preservation: nhóm đổi mức kém V2 5,6072% (ngưỡng5%), toàn bộ mean per-case
V3/V2 cũng kém1,0522%. Tất cả báo cáo, mã nguồn và đầu ra đó được giữ nguyên.

Đối chiếu case shift1944 cho thấy lựa chọn `weekly` thực sự tốt hơn `full`
khoảng0,9309% trên validation; đổi one-SE thành argmin vẫn chọn `weekly`.
Sau khi doanh thu giảm mức chưa từng xuất hiện trong phần fit, std28 chuẩn
hóa ra ngoài khoảng fit và model weekly điều chỉnh residual dương quá mạnh.
Replay numeric trees từ JSON và thử thay giá trị đặc trưng cho thấy phản ứng
này; đây không là chứng minh nhân quả hoặc khả năng khái quát của thuật toán.

Kiểm lại65 bảng calibration đã xem của V3 bằng hai lựa chọn none/full cho
39full/26none;25 lựa chọn weekly cũ chuyển thành full. Chẩn đoán này dùng để
đặt giả thuyết, **không phải holdout mới hay điểm nghiệm thu V4**.

## 3. Thay đổi tối thiểu, vẫn là XGBoost

V4 chỉ cho hai schema: `none` bỏ cả4 cột lịch, còn14 đặc trưng; `full` giữ
đủ18 đặc trưng như V2. Không có phương án lịch một phần. API fit/load V4 từ
chối schema weekly. Không dùng scenario, seed, tên case hay ngày đổi mức làm
đầu vào. Không chuyển dự báo sang MA7 hoặc trộn kết quả baseline để thắng điểm.

Giữ nguyên MA7 anchor, residual chuẩn hóa, alpha1 và direct14-day của V2:
L1/depth2/200trees/rate0,05, subsample/colsample1, lambda1, seed42, n_jobs1.
MA7 anchor là thành phần công khai của kiến trúc, không gọi đây là XGB độc lập
không có baseline. Hai module mới tái sử dụng model/evaluate/evidence primitives
cũ, không sửa mã runtime ứng dụng hoặc mã V1–V3.

Mỗi chuỗi shadow-fit[:438], chấm validation[438:584] bằng10 block14 ngày,
bỏ6 ngày dư. Lấy sampleSD của10 block-MAE tốt nhất chia sqrt10 làm SEM;
ưu tiên none nếu loss<=best+SEM, còn lại chọn full. Từ chối thiếu mode,
boolean, NaN/Inf, số âm và overflow. Đây là **one-SE heuristic**, không phải
khoảng tin cậy được hiệu chuẩn hay bằng chứng ổn định trong mọi chế độ.

Khóa đủ115 lựa chọn trước mọi final fit. Refit[:584], final[584:730] cũng10
block/140 ngày. Mỗi origin chỉ dùng actual đã biết; không dùng future truth
trong block hoặc model fit584 để chấm validation. Nếu chọn full, model đó
được dùng chung với comparator V2 để không tạo khác biệt do refit thừa.

## 4. Protocol khóa trước fit

Giữ nguyên5 generator V1: noise, weekly/calendar, gradual trend, intermittent
spikes và level shift.115 chuỗi×730 ngày=83.950 dòng mô phỏng từ01/01/2024
đến30/12/2025, đơn vịVND, không chứaPII, không ghi giao dịch giả vào CSDL.
Development seeds2026102211/12/13; final seeds2026102221..2026102240.
100 final case,20 mỗi nhóm; các cohort V1–V3 đều đã xem và chỉ dùng chẩn đoán.
Đây là seed mới của cơ chế đã biết, không phải dữ liệu thực hoặc external blind.

Identity: `7eb97e995fcbf5fae2e163941dd16d2ad7b480aff4f97c6d6cdf4ff9edb22b74`.
Python3.14.5/NumPy2.4.3/pandas3.0.1/XGBoost3.4.1;10 source hashes,231 input
files được đóng dấu. Một job native ẩn, bốn thread caps=1, chặn socket trong
process; checkpoint/case receipts để tiếp tục an toàn nếu bị ngắt. Không
tuyên bố cơ chế này đã sửa lỗi desktop tự thoát hay thay thế firewallOS.

Job thực tế2.786,663s (46phút26,663giây),0 lỗi thực thi/exit0,0 attempted
network calls.230 calibration fits+140 final refits=370fits; lưu430 model
JSON, trong đó60 final full models dùng lại cho comparator. Final:none40/full60.
Không dùng thời gian chạy lâu làm bằng chứng chất lượng thay cho metric.

Giữ toàn bộ cổng V3: đủ expected case duy nhất đúngID/scenario/seed; finite;
overall mean ratio/MA7<1; noise mean ratio/MA7<1 và mean V4/V2<=1; mỗi nhóm
<=1,10/MA7; mỗi case<=1,50/MA7; weekly/trend/shift mỗi nhóm<1/MA7 và
<=1,05/V2. Thêm trước fit: **overall mean per-case V4/V2<=1**, tỷ lệV2 hữu
hạn/không âm/không boolean. Chỉ chạy một protocol/cohortV4; không thayseed,
generator, ngưỡng hoặc metric sau final. COMPLETED khác accuracy PASS.

## 5. Kết quả final và cổng chất lượng

Mỗi nhóm20case, cùng origin/horizon/truth. Các tỷ lệ dưới đây là mean của
từng tỷ lệ MAE unrounded, không phải chia hai MAE gộp hoặc hai primary.

| Nhóm | V4/MA7 | V4/V2 |
|---|---:|---:|
| noise_control |0,933449346806|0,987708674834|
| weekly_calendar |0,174760524469|1,000000000000|
| gradual_trend |0,305297955200|1,000000000000|
| intermittent_spikes |0,852340738112|0,996993128025|
| level_shift |0,812343833852|1,000000000000|
| Tất cả100 |0,615638479688|0,996940360572|

Các check `complete`, `finite`, `overall`, `level_shift`, `families`, `cases`,
`noise`, `preservation`, `v2_finite`, `overall_v2` đềuPASS. So với V2 có25case
tốt hơn,60bằng đúng (full reuse),15kém hơn; không đánh đồng mean gain với
không có regression ở từng case. So với MA7 có99thắng/0hòa/1thua.

Case thua duy nhất: `final__noise_control__2026102236`, modenone.
MAE V4=1.601.327,037854; MA7=1.590.362,468926; V2=1.669.302,705877VND/ngày.
V4/MA7=1,0068943836025812, V4/V2=0,9592790044707858. Dù cải thiện V2 khoảng
4,072100%, V4 vẫn không thắng MA7 ở case này. Không thaycase/seed hoặc “sửa”
điểm sau khi đã chấm. Kết luận giới hạn này phải đi cùng mọi công bố đạt cổng.

Bảng dưới gộp2.800 observation/nhóm; MAE/RMSE/bias bằngVND/ngày. Đây là
metric bổ sung, không thay mean per-case ratio ở bảng trên. MAPE chỉ tính
actual khác0; R² âm vẫn giữ nguyên. Undefined metric nếu có trong từng
horizon được giữ null, không biến thành0 để làm đẹp kết quả.

| Nhóm | MAE | RMSE | MAPE% | R² | Bias |
|---|---:|---:|---:|---:|---:|
| noise_control |1.652.560,72|2.078.160,66|8,4496|-0,035804|-25.384,05|
| weekly_calendar |838.107,53|1.051.597,74|3,6757|0,964663|-9.369,44|
| gradual_trend |920.435,09|1.148.327,16|2,6155|0,910318|10.607,10|
| intermittent_spikes |10.343.051,00|17.166.589,15|78,9459|-0,120913|-5.134.279,75|
| level_shift |2.375.013,53|4.294.139,80|13,6769|0,738351|1.321.234,53|

Mọi metric của5method, từng case và14horizon, cùng calibration loss/selection
đều nằm trongCSV/JSON của gói bằng chứng. Những bảng ngắn không thay dữ liệu đó.

## 6. Hai case cũ đã xem

Sau final mới kiểm lại noise1912 và shift1944 bằng cùng rule đã khóa. So
modelSHA và mọi prediction/metric/baseline V2 với bản gốc. Hai case này không
được gộp vào100 final mới và không là đánh giá độc lập chưa từng xem.

| Case đã xem | Mode | MAE V4 | MAE V2 gốc | MAE MA7 | V4/MA7 |
|---|---|---:|---:|---:|---:|
| noise1912 |none|1.640.355,149858|1.689.379,030261|1.670.432,251884|0,981994419712|
| shift1944 |full|2.616.380,194173|2.616.380,194173|2.978.733,409988|0,878353257596|

Noise1912 từ kém MA71,134244% ở V2 thành tốt hơn MA71,800558%; MAE giảm
2,901888% so với V2. Cùng kết quả V3 đã biết, không gọi đây là cải thiện mới
chưa từng xem. Shift1944 giảm MAE23,683583% so với V3 weekly lỗi cũ, nay thắng
MA712,164674% và bằng đúng V2. V2 comparator modelSHA vẫn nguyên:

- Noise1912: `8b882e0a8f1eb52e790312a3a1cb9aaec4176cdb4935d5de753c597bad19a9af`.
- Shift1944: `88135730c53306f597b71571a1270a5c4d366dbee505bd8d9b6374782c58f30d`.

Replays mới noise2221/shift2221 cho12/12 artifactSHA và4/4 payload khớp chính
xác. Replay81,811s, old-SEEN diagnostics77,049s, mỗi stage0 network calls,
thread caps1. Đây là bằng chứng tái lập, không cộng thêm mẫu accuracy.

## 7. Kiểm chứng và bằng chứng

TDD11 ca mới, cộng21 ca V2/V3:32/32 focused tests OK189,837s. Review phát
hiện thêm hai lỗi bằng chứng: boolean lọt cổng ratio và resume COMPLETED có
thể tin manifest bị thay; đã viết ca RED rồi sửa và GREEN32/32 trước khi freeze.
Lifecycle doubles chỉ dùng kiểm failure/resume/thứ tự, không là accuracy score.

Bandit1.9.4 trên đúng hai module V4:253LOC/0 findings/0 errors/0 nosec/0 skip.
py_compile và git diff --check đạt. Đây không phải chứng chỉ an ninh hệ thống.
Kiểm toán độc lập tính metric/one-SE/gate/baseline và suy luận numeric trees
không gọi hàm chấm điểm/model fit của benchmark. NumPy RNG vẫn dùng chung
khi tái sinh seed. Audit thực tếPASS/0errors:2.358.891 evidence assertions,
2.421 SHA entries; tái sinh83.950dòng, kiểm115 calibration+100 final receipts,
430 JSON models/60.200 past-only JSON predictions và150.500 CSV observations.
Đây là số phép kiểm bằng chứng, **không phải2,36triệu unittest**.

Audit riêng2case đã xem cũngPASS/0errors:43.943checks/74SHA entries,
1.460dòng tái sinh,8newmodel+1oldV3 schema,1.260JSON predictions,2.800CSV
observations. Cả hai V2 comparator khớp SHA/prediction/metric gốc. Các stage
replay/mainaudit/seenaudit đềuexit0 và giữ accuracy_gate_passed=true đúng
kết quả final, không dùng integrity flag để sửa quality flag.

## 8. Giới hạn và quyết định phạm vi

Không hứa thắng mọi mẫu nhiễu, dự báo đúng100%, xác suất cải thiện đã được
hiệu chuẩn hoặc hiệu quả trên dữ liệu doanh nghiệp. R² âm, case thua/hòa và
sai số từng horizon phải giữ nguyên. MAPE loại actual0 nên không phản ánh
đầy đủ ngày không có doanh thu; MAE là primary, không tráo metric để thắng.

Chọn hai mode có thể bỏ tín hiệu lịch yếu hoặc giữ tương quan giả. One-SE có
thể chọn mean validation hơi kém để ưu tiên đơn giản.100 case tăng độ phủ
seed nhưng không là power analysis, kiểm định thống kê hay bảo đảm tương lai.
Một trăm case thắng (nếu có) cũng không suy ra mọi dữ liệu tương lai đều thắng.
100 case ở đây là20 seed×5 cơ chế, không phải100 seed độc lập; các chuỗi cùng
seed không được chứng minh độc lập thống kê. Không suy diễn khoảng tin cậy.

Provenance huấn luyện dựa trên mã khóa, receipts và test cutoff; JSON trees
không tự chứng minh từng dòng training. SHA/mtime local không là log ký số
append-only, không chống người có quyền sửa đồng bộ toàn bộ bằng chứng.
Integrity PASS phải đọc riêng với quality PASS/FAIL; không mượn testPASS làm
bằng chứng modelPASS. Các skill Superpowers định hướng chẩn đoán, protocol
khóa trước, TDD, fresh review và kiểm chứng độc lập thay vì sửa điểm báo cáo.

Không cần browser UAT vì không đổi giao diện/chức năng web. Không tích hợp
production trong lượt này; muốn áp dụng thực tế cần nghiên cứu riêng trên
giao dịch canonical, rolling-origin ngoài mẫu và kế hoạch triển khai được duyệt.
Không cần thêm credential hoặc thông tin của người dùng cho nghiên cứu offline.

### Các ruling và đánh đổi

1.100% nghĩa là đủ cổng hữu hạn đã khóa; không cam kết thắng mọi dữ liệu.
2. Inline và delegate chẩn đoán/builder/review/audit độc lập, một heavy job;
   đánh đổi: không reviewer riêng cho từng task nhỏ.
3. Atomic none/full là quyết định kiến trúc trong phạm vi thử nghiệm pureXGB;
   đánh đổi: không bảo đảm đã chứng minh ổn định hoặc giữ được mọi tín hiệu.
4.100 final/20 mỗi nhóm và thêm overallV2 gate trước fit; đánh đổi: tốnCPU
   hơn, không thay được external holdout hoặc power/confidence analysis.
5. Một cohortV4 cố định, giữ mọi FAIL cũ; đánh đổi: có thể không đạt quality
   và phải báo đúng, không tìm seed tiếp cho đến khi PASS.
6. Review không chấm empirics; thay bằng execution/replay/audit/full thật,
   không suy diễn từ mã nhìn hợp lý.
7. Không nghiệm thu production/tổng97/generalization/signed attestation;
   đánh đổi: cần bước riêng nếu sau này muốn công bố những phạm vi đó.
8. Deferred minor: benchmark summary chỉ có wins; audit/báo cáo bổ sung đủ
   wins/ties/losses, không đổi nguồn đã freeze chỉ để thêm convenience field.
9. Full suite là superset của32 focused tests, dùng một lần cho final regression
   Task2 và bằng chứng Task3; handoff sẽ kiểm raw log/sourcefreeze. Đánh đổi:
   hai task dùng chung receipt thật, không chạy lặp vô ích hoặc đếm audit
   assertions thành số unittest. Mẫu báo cáo được chuẩn bị lúc chờCPU, số liệu
   chỉ điền sau thực thi và được đối chiếu audit trước fullsourcefreeze.

## 9. Full verification và bàn giao

Full worktree **1452/1452 test PASS trong312,229s**,0failure/error/skip;
snapshot775 tệp, source_unchanged=true/changed_source_paths=[] tại
`output/acceptance_verification/20261019T105622Z`. Database riêng
`test_alphatech_evidence_358ddb022ab449ed` được tạo và hủy sau run; không reset
development/production DB. MD5 hasher và legacy fixture compatibility chỉ
process test, strict tests tự override, không thay runtime. Đây không phải
full dirtymain, remote CI hoặc production certification.

Framework systemcheck0issues, migrationcheck/dryrunNoChanges trên TEST riêng
cũng đãPASS. So snapshot V3, không đổi/xóa mã hoặc test cũ ngoài docs; chỉ
thêm4tệp Python củaV4. Sau full chỉ cập nhật receipt/định dạng tài liệu và
checkbox, không thay model source, test, generator, gate hay metric.

Handoff đã xác nhận609 tệp nguồn ngoài docs khớp fullsnapshot;2.140 frozen
artifact entries củaV1/V2/V3 và1.310 củaV4 giữ SHA. Main97/old90day business
CSV, runtime app/schema và18 control anchors cũ đều không đổi. Hai cờ cuối
`integrity_verified=true` và `accuracy_gate_passed=true` đều dựa trên kiểm
tra thực tế, không đồng nghĩa chứng nhận dữ liệu thật/production/universal.

Quy trình bàn giao tạo mới trênD bằng whitelist, không.env/secret/DBdump;
đọc lại mọi ZIP entry kiểm SHA, không ghi đè gói V1/V2/V3. Worktree giữ nguyên,
chưa integration. Các bản input/model/results V4 được đóng gói đầy đủ; đối
chiếu lịch sử chỉ kèm controls và hai case cũ liên quan, không phải bản sao
toàn bộ mọi artifact củaV1–V3. Các gói cũ vẫn được giữ riêng nếu cần chạy lại
kiểm toán lịch sử đầy đủ. Không dùng ZIP này như bản sao toàn bộ ứng dụng.

Plan trong ZIP là snapshot ngay trước bước đóng gói để tránh vòng tự tham
chiếu; receipt `XGBOOST_ATOMIC_V4_DELIVERY_20261019.json` ngoài ZIP xác nhận
archiveSHA, reportSHA, từng entrySHA, số lượng và cờ nghiệm thu thực tế.
Sau đó chỉ cập nhật checkbox/ledger worktree, không sửa bytes của gói đã tạo.

Báo cáo: `D:/ai_business_platform/output/XGBOOST_ATOMIC_CALENDAR_2026_10_19.md`.
Gói: `D:/ai_business_platform/output/XGBOOST_ATOMIC_V4_EVIDENCE_20261019.zip`.
Receipt: `D:/ai_business_platform/output/XGBOOST_ATOMIC_V4_DELIVERY_20261019.json`.

Lần preflight đóng gói đầu dừng trước khi tạo fileD: phép so dictionary yêu
cầu float bằng đúng bit trong khi math.fsum/statistics và NumPy khác khoảng
1–2e-16 ở vài mean ratio. Identity và mọi cờ gate đều khớp. Raw failurelog
được giữ; không sửa số liệu hoặc cổng. Helper bàn giao dùng numeric tolerance
1e-12 giống handoff đã kiểm, nhưng keys/identity/boolean/shape vẫn nghiêm ngặt,
NaN/Inf và thay đổi thực chất bị từ chối. Ba test delivery-only đã RED→GREEN;
không cộng chúng thành1455 full-app tests. Đây là sửa helper artifact sau full,
không đổi model source hoặc các test trong fullsnapshot.
