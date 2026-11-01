# XGBoost V3 — chọn đặc trưng lịch bằng validation quá khứ

Ngày 19/10/2026; worktree riêng tại
`C:/Users/anhbe/.codex/worktrees/xgb-synthetic-benchmark/ai_business_platform`,
base `4f3c6ab1d043268bb615d6c9f1078b0350cbb52a`. Chủ dự án chọn giữ
XGBoost, thử nghiệm offline, chưa thay production. Không đổi sổ97.

## 1. Kết luận cần đọc trước

**Case noise1912 cũ đã được khắc phục trong phép đo này:** từ kém MA7
1,134244% xuống tốt hơn MA7 1,800558%; MAE giảm 2,901888% so với V2.
Đây là case đã xem, không phải holdout mới hoặc bằng chứng thắng mọi nhiễu.

**Bộ mới:** 49/50 case thắng MA7, primary equal-case mean MAE ratio/MA7
0,623262901417290, tương ứng giảm 37,673710% MAE tương đối. Cả10 case nhiễu
mới đều thắng MA7. Tuy nhiên, V3 **chưa đạt toàn bộ cổng chất lượng đã khóa**:
nhóm level_shift kém V2 5,607179%, vượt giới hạn5%. Không đổi ngưỡng sau khi
thấy kết quả. Job hoàn tất với exit3 đúng quy ước performance FAIL, không lỗi
thực thi. **Không đề xuất thay V2 bằng V3 đại trà hoặc đưa vào production.**

Trên cùng50 case mới, V2 thắng MA7 50/50, primary0,613957254173431; V3
không là cải thiện tổng thể. Equal-case mean của từng tỷ lệ V3/V2 là
1,01052247332234 (kém1,052247%). Đây là phép gộp khác với chia hai primary
hoặc chia MAE gộp; không tráo các mẫu số để làm đẹp số liệu.

## 2. Chẩn đoán và thay đổi

Noise1912 V2 dành30,73% training split gain cho calendar dù dữ liệu sinh là
20 triệu cộng nhiễu độc lập. Có bước giảm dự báo khoảng1,23 triệu từ31/10
sang01/11 ở cùng origin. Đây là dấu hiệu khớp lịch giả, không chứng minh lịch
là nguyên nhân duy nhất. Chênh lệch MAE cũ18.946,78VND/ngày nhỏ hơn biến
thiên block; không gọi đó là suy giảm có ý nghĩa thống kê đã được chứng minh.

Hai module V3 mới tái sử dụng nguyên V2: target residual chuẩn hóa, MA7 anchor,
direct14-day prediction, alpha1; XGB L1/depth2/200trees/rate0,05, seed42,
subsample/colsample1, lambda1, n_jobs1. Không sửa nguồn hay kết quả V1/V2.

Ba mode: `none` bỏ4 cột lịch nhưng vẫn là XGBoost14 đặc trưng; `weekly` giữ
weekday/weekend,16 đặc trưng; `full` giữ đủ18 cột V2. Không dùng scenario,
seed hoặc tên case làm đầu vào selector/model. Không chuyển sang baseline
hay statistical fallback. MA7 anchor vẫn là thành phần công khai của mô hình.

Mỗi chuỗi fit3 shadow model trên438 ngày đầu. Validation146 ngày tiếp theo
chấm10 block14 ngày không chồng nhau, bỏ6 ngày cuối. Chọn best theo mean
block-MAE; lấy sampleSD của10 loss best/sqrt10 làm SEM, ưu tiên mode đơn giản
đầu tiên có loss<=best+SEM. Đây là **one-SE heuristic**, không là khoảng tin
cậy được hiệu chuẩn. Tất cả65 lựa chọn được khóa trước mọi final model.
Sau đó refit trên584 ngày đầu, chấm140/146 ngày cuối bằng10 origin. Không
chọn mode bằng model đã fit584 hoặc chỉnh rule sau final.

## 3. Dữ liệu và protocol

Generator V1 giữ nguyên5 cơ chế: noise, weekly/calendar, gradual trend,
intermittent spikes và level shift. Không tạo giao dịch/đơn hàng giả trong DB.
65 chuỗi×730 ngày=47.450 dòng mô phỏng, có metadata/provenance và SHA.
Development seeds2026101931/32/33; final seeds2026101941..2026101950, rời các
study cũ. Đây là fresh seed của **cơ chế mô phỏng đã biết**, không là dữ liệu
doanh nghiệp thật hoặc blind external validation. Calibration không được
gọi là điểm final.10 origin×14 ngày/case dùng actual đã biết tại mỗi origin,
không dùng actual tương lai trong block. Baseline ma7/seasonal7/naive1 dùng
cùng origin/horizon/truth; không bỏ case thua hoặc R² âm.

Bundle identity `d196381eea9a075238f7879881ccd14a8f4b0ed1511b08f92d0347a0ffc2e359`.
Selections SHA `16e9067275920981c7e017daffa3a2cc89faf9214de06cae341130dfb7656574`.
Runtime Python3.14.5/NumPy2.4.3/pandas3.0.1/XGBoost3.4.1; bốn thread cap=1.
Một job869,409s, networkguard bật,0 attempted network calls.195 calibration
fits+89 final refits=284 fits; lưu295 model JSON (11 full-mode reuse).

## 4. Kết quả mới và cổng đã khóa

Tỷ lệ dưới đây là mean **per-case unrounded MAE ratio**, không phải ratio
của MAE gộp. Mỗi nhóm10 case.

| Nhóm | V3/MA7 | V3/V2 | Kết luận |
|---|---:|---:|---|
| noise_control |0,925665128498|0,994372505020|Thắng MA7; cải thiện nhẹ so với V2|
| weekly_calendar |0,175753407349|1,000000000000|Giữ chất lượng nhóm|
| gradual_trend |0,302791622191|0,994529038942|Thắng cả hai theo mean ratio|
| intermittent_spikes |0,852091359541|1,007639032573|Thắng MA7, kém nhẹ V2|
| level_shift |0,860012989508|1,056071790077|Thắng MA7 theo nhóm, vi phạm preservation|
| Tất cả50 |0,623262901417|1,010522473322|Không phải cải thiện tổng thể so với V2|

Các check complete/finite/case/family/level_shift/overall/noise PASS;
**preservation FAIL**, vì level_shift>1,05 so với V2. Một case thua MA7:
`final__level_shift__2026101944`, modeweekly, MAE V3=3.428.332,07;
MA7=2.978.733,41; V2=2.616.380,19VND/ngày. V3 kém MA7 15,093619%,
kém V2 31,033406%. Không xóa case này hoặc gọi49/50 là50/50.
So với V2 theo so sánh unrounded nghiêm ngặt:17 tốt hơn,11 bằng,22 kém hơn;
các chênh lệch rất nhỏ vẫn giữ trong JSON. Final mode counts:none20/weekly19/full11.

## 5. Metric gộp bổ sung (V3, không dùng làm primary)

Mỗi hàng gộp1.400 observation của nhóm. MAE/RMSE/bias tính bằng VND/ngày;
MAPE chỉ tính actual khác0, vì vậy không đo đầy đủ chất lượng ngày zero của
intermittent. R² âm giữ nguyên, không đổi thành0 hoặc bỏ khỏi báo cáo.

| Nhóm | MAE | RMSE | MAPE% | R² | Bias |
|---|---:|---:|---:|---:|---:|
| noise_control |1.620.528,21|2.034.859,47|8,3015|-0,040659|55.970,24|
| weekly_calendar |826.289,32|1.025.457,94|3,6187|0,965611|21.628,16|
| gradual_trend |888.499,00|1.116.211,72|2,5121|0,912456|71.515,70|
| intermittent_spikes |10.667.543,58|17.839.354,76|80,5022|-0,134515|-5.591.367,45|
| level_shift |2.444.988,73|4.470.438,38|14,4197|0,715980|1.537.053,33|

Tất cả5 method/case/horizon, calibration loss, selection, sai lệch và kết quả
âm nằm trong CSV/JSON của gói bằng chứng; bảng ngắn không thay các bản ghi đó.

## 6. Kiểm lại noise1912 — đã xem, không holdout mới

Cùng rule khóa trước, chọnnone từ validation quá khứ: mean1.719.793,37;
SEM136.998,69; threshold1.856.792,06VND/ngày. Final:

| Model | MAE VND/ngày | Ratio/MA7 |
|---|---:|---:|
| MA7 |1.670.432,251884|1,000000000000|
| V2 full cũ |1.689.379,030261|1,011342440470|
| V3 none |1.640.355,149858|0,981994419712|

V3 giảm49.023,88VND/ngày so với V2. V2 refit JSON SHA trùng model V2 cũ,
mọi metric/baseline/prediction của comparator giữ nguyên. Không đổi đầu ra cũ
thành kết quả mới. Kiểm toán độc lập đã tái dựng cả3 calibration và2 final
model từ JSON, xác nhận arithmetic/selection/metrics/receipts, không fit lại.
Kết quả giải quyết chênh lệch cụ thể đã nêu, không bảo đảm mọi mẫu nhiễu.

## 7. Bằng chứng thực thi và an toàn

- TDD mới9 ca, existing V2 12 ca: focused21/21OK31,765s; task2 final21/21OK25,608s.
  Ca cutoff thật sửa toàn bộ final truth vẫn cho calibration/model/CSV bằng nhau.
  Ca failure/interruption dùng double để kiểm lifecycle, không là quality score.
- Fresh review read-only: không Critical/Important; một minor convenience field
  overallV3/V2 được tính độc lập trong audit và báo cáo này, chưa thêm vào runtime JSON.
- Independent audit:1.464.194 evidence assertions,1.439 SHA entries,0 lỗi;
 65 inputs/115 receipts/295 model JSON; tái dựng41.300 model predictions từ
  past-only features và numeric trees, kiểm89.600 CSV rows. Đây không là số test.
- Replay weekly1941/noise1941:14/14 artifact hashes và4/4 payload khớp chính xác;
  không là hai mẫu accuracy mới. Seen1912 có audit riêng statusPASS/errors0.
- Bandit1.9.4 trên hai module V3:285LOC/0 findings/0 errors/0 nosec;
  py_compile/gitdiffcheck đạt. Không suy rộng thành security certificate cả hệ thống.
- Fullworktree suite/framework/drift có receipt cuối ở mục9; không mượn
  full1432 V2 hoặc full dirtymain.

Metric/one-SE/tree inference kiểm độc lập không gọi benchmark metric/model fit.
NumPy RNG vẫn là dependency chung khi tái sinh seed. Cutoff provenance dựa trên
source khóa/receipt/test invariance; model trees không chứng minh độc lập từng
training row, V3 chưa xuất training-pair trace. Thứ tự mtime/receipt chỉ bổ trợ,
không là signed append-only log hay bằng chứng chống giả mạo đồng bộ mọi file.
Socket guard trong process không thay firewall OS.

## 8. Quyết định và phần chưa đạt

Giữ nguyên production/Neon/runtime app/schema/old90day CSV/V1/V2/sổ97.
Không commit/merge/push/deploy; giữ worktree và bản ZIP riêng. Không browser
UAT vì thay đổi chỉ ở script ML offline, không giao diện/chức năng website.
Các skill Superpowers đã dẫn tới chẩn đoán trước, spec/rule khóa, TDD,
review độc lập và phân biệt integrity PASS với quality FAIL.

Không nâng V3 làm model chính: kết quả không đạt preservation và meanV3/V2
kém nhẹ. Nếu tiếp tục, cần một nghiên cứu mới với nhiều rolling-origin
calibration, ổn định chọn đặc trưng qua các chế độ và cohort chưa từng xem;
khóa tiêu chí trước fit, không tune tiếp50 final này hoặc đảm bảo mọi dữ liệu.
Không thiếu secret/quyền truy cập nào để hoàn tất nghiên cứu offline hiện tại.

### Rulings của lượt thực hiện (theo thứ tự, kèm đánh đổi)

1. Thực hiện inline, delegate diagnostic/builder/reviewer/auditor riêng để giữ
   một heavy job; đánh đổi: chỉ một fresh whole-change review, không mỗi task.
2.65 series/50 fresh final và one-SE ưu tiên đơn giản; đánh đổi: heuristic có
   thể chọn sai, không confidence guarantee hay khả năng thắng mọi mẫu.
3. Giữ detached worktree chưa commit/không integration; đánh đổi: cần bước
   tích hợp riêng nếu sau này được duyệt, không hiện ngay trên website.
4. Reviewer không chấm empirics; thay bằng execution/replay/audit/fullsuite;
   đánh đổi: code hợp lý vẫn có thể thất bại chất lượng (lần này đã xảy ra).
5. Production/DB/RBAC ngoài review vì không đổi; đánh đổi: chưa kiểm chứng
   triển khai phương pháp mới ở môi trường thật.
6. Không chấm real-business/universal validity; đánh đổi: simulation không
   đủ chứng minh hiệu quả với giao dịch hoặc dữ liệu tương lai của doanh nghiệp.
7. Không thêm signed chronology; đánh đổi: checksum local không chống được
   người có quyền sửa đồng bộ mọi bằng chứng.
8. Giữ gate FAIL, không tune/reseed/relax sau final; đánh đổi: không thể nghiệm
   thu V3 đạt mọi mục tiêu chất lượng hoặc tuyên bố đã hoàn thiện100% thuật toán.
9. Đóng gói cả nghiên cứu FAIL, tách integrity_verified và accuracy_gate_passed;
   đánh đổi: người đọc cần giữ phân biệt này, không hiểu test PASS là model PASS.

Deferred minor: overallV3/V2 convenience field chưa thêm vào kết quả benchmark;
audit và báo cáo đã chứa đủ metric đó, không bỏ sót tổng thể khi công bố.

## 9. Receipt full verification và bàn giao

Fullworktree **1441/1441OK328,195s**,0 failure/error/skip; snapshot768 tệp,
source_unchanged=true/changed_source_paths=[] tại
`output/acceptance_verification/20261019T091622Z`. PostgreSQL/PostGIS TEST
`test_alphatech_evidence_e3490a59c7ea4a03` được tạo riêng và hủy sau run.
Hasher MD5 và legacy fulfillment-fixture compatibility chỉ trong process test;
các strict tests tự override, không đổi runtime hashing/fulfillment của app.
Đây không phải full CI hoặc full dirtymain hiện tại.

Framework systemcheck0issues, migrationcheck/dryrunNoChanges trên TEST riêng;
không ghi migration hay reset database hiện hành. Sau fullPASS chỉ cập nhật
receipt tài liệu/checklist kế hoạch, không sửa các module/test hoặc metric/gate.
Handoff đã kiểm lại605 tệp nguồn ngoài docs với snapshotfull,2.140 frozen
V1/V2/V3 hash entries, hai audit/replay/seen stage receipts, main97 và old90day
CSV; tất cả giữ đúng hash. Cờ integrity_verified=true, accuracy_gate_passed=false.

Bàn giao create-only trên ổD: báo cáo này và
`D:/ai_business_platform/output/XGBOOST_CALENDAR_V3_EVIDENCE_20261019.zip`,
kèm `XGBOOST_CALENDAR_V3_DELIVERY_20261019.json` chứa SHA-256/size/count.
ZIP dùng whitelist, không chứa.env, credential hoặc bản dump dữ liệu nghiệp vụ;
mọi entry được đọc lại kiểm SHA. Không overwrite bất kỳ gói V1/V2 nào.
`integrity_verified=true` phải đọc cùng **`accuracy_gate_passed=false`**;
hoàn tất công việc thử nghiệm/kiểm chứng không có nghĩa đạt100% chất lượng model.
