# XGBoost thích nghi mức doanh thu —19/10/2026

## Phạm vi

Chủ dự án đồng ý bản thử nghiệm riêng. Worktree cô lập dựa trên4f3c6ab;
không đổi production/Neon/runtime forecast/migration, không tạo giao dịch và
không thay cấu trúc/tiến độ97. Đây không phải fine-tuning một LLM.

## Nguyên nhân thực sự của kết quả cũ

V1 giữ nguyên:11/15case thắng, equal-case mean relativeMAE kémMA7 12,0067%.
Trong7origin sau khi mức giảm đã quan sát, XGBvẫn lệch dương toàn bộ294 dự
báo: MAE12,138triệu vsMA7 2,419triệu. One-step với lịch sử thật cũng lệch
11,87triệu: không chỉ cộng dồn recursive. Trees target doanh thu tuyệt đối
không có cơ chế extrapolate xuống mức mới; validation V1 không có cú giảm này.
Kết quả cũ không bị viết lại hay đổi trọng số chấm.

## Thuật toán mới

Tên chính xác: **MA7-anchored direct residual XGBoost**. Anchor mean7 đã biết,
scale=max(mean7,mean28/4,1VND); XGB học `(actual_h-anchor)/scale`, đầu ra
`max(0,anchor+alpha*scale*residual)`. Dự báo trực tiếp h1..14 từ cùng origin,
không nhét futureactual hoặc dự báo trước đó vào feature ngày sau. Feature
lag/rolling chuẩn hóa, trend ngắn hạn và lịch ngày đích; không scenario/seed/
ngày break. Khi nhận quan sát mức mới, anchor thích nghi ngay mà không phải
đợi cây học lại target tuyệt đối. Không thể biết trước cú sốc chưa có tín hiệu.

Không được gọi đây là standaloneXGB thuần thắng baseline: mô hình dùng MA7
làm neo và một correction học bằng XGBoost thật. Alpha0 bị loại khỏi grid.

## Protocol đã khóa trước khi fit

40chuỗi×730ngày=29.200quan sát mô phỏng; generator V1 giữ nguyên, development
3seed và final5seed mới. Chia438/146/146, h14,10origin/140ngày scored,6tail
chưa đủ block bỏ theo protocol cũ. Grid4fit×2alphas,60developmentfits; chọn
duy nhất một cấu hình từ15validationcase bằng mean ratioMAE unrounded.
Sauselection mới fit25finalcase (mỗi case một adaptive và một V1raw comparator).
MA7/seasonal7/naive1 dùng đúngorigin/truth/horizon, recursive không oracle.

Cổng đặt trước: overallMAEratio<1; level_shift<1; mỗi family<=1,10; mỗi
case<=1,50; đủ25case duy nhất đúngID/scenario/seed. Mọi loss vànegativeR² giữ.
Case/runtime/source/input SHA khóa; selection immutable; percase receipts/
checkpoint/exclusivewriter, failed/incomplete attempts không bị xóa.

Freshseed của cùng cơ chế đã biết, không holdout mù độc lập hay dữ liệu thật.
Validation không chứa cú giảm final; adaptation đến từ representation mới,
không từ biết trước thời điểm giảm. Không suy ra chất lượng doanh thu thật.

## Kết quả và kiểm chứng

Study hoàn tất532,656s (02:22:27–02:31:20UTC19/10),110fits; networkguard
0calls, không DB. Development chọn L1/depth2/200trees/alpha1,0 với meanratio
0,5784805983567297. Selection được ghi trước final và không điều chỉnh sau đó.
Identity inputmanifest:
`cf5fc1f8d7c526ca6e884a11880f6da9ccdf6b198987541f67a577d8892acc2d`.

**Fresh final25case:24thắng/1thua; primarymeanratio0,6038106056329053,
tức giảmMAE39,6189% soMA7. Tất cả6checks của cổng khóa trước đều PASS.**

| Family (5case/family) | V2MAE trung bình (VND) | MA7MAE trung bình | V1rawMAE trung bình trên chính freshseed | Mean per-case giảmMAE/MA7 | Sốthắng |
|---|---:|---:|---:|---:|---:|
| Noise control |1.577.158,51|1.691.418,78|1.578.806,27|6,66%|4/5|
| Weekly calendar |797.693,81|4.796.188,05|788.088,62|83,36%|5/5|
| Gradual trend |850.382,72|2.989.742,81|1.565.293,44|71,51%|5/5|
| Intermittent spikes |10.349.699,48|12.446.867,78|11.049.454,98|16,52%|5/5|
| Level shift |2.324.057,23|2.909.737,96|9.661.905,48|20,05%|5/5|

AbsoluteMAE trong bảng là mean các case; primary là mean các **ratio từngcase**,
không chia hai MAE trung bình hay đổi sang pooledmetric để làm đẹp. V1raw trên
freshseed cũng không phải con số V1final16/10 (seed khác).

Case thua được giữ nguyên: `final__noise_control__2026101912`,ratio
1,01134244047016, tức kémMA7 1,1342%. Không khẳng định thắng mọicase. V2vẫn
cóR²âm ở noise (mean khoảng−0,06) và intermittent (khoảng−0,14), MAPE gần80%
ở intermittent trênngày nonzero; forecast chưa giải quyết bất định của spike.
V2weekly cóMAE cao hơn một chút soV1raw trênfreshseed dù vẫn hơnMA7. RMSE/
MAPE/R²/bias đầy đủ giữ trongresults.json vàaudit, không chỉ chọnMAEđẹp.

MetricV2 trung bình từngcase, tính độc lập từ CSV (không làpooledR²):

| Family | RMSE (VND) | MAPE trênngàynonzero | R² | Bias (VND) |
|---|---:|---:|---:|---:|
| Noise control |1.998.163,90|8,00%|−0,06|−70.266,12|
| Weekly calendar |1.006.879,08|3,51%|0,97|−22.507,91|
| Gradual trend |1.057.841,64|2,42%|0,92|−21.093,14|
| Intermittent spikes |17.365.908,32|79,97%|−0,14|−5.097.598,54|
| Level shift |4.255.312,51|13,34%|0,74|1.233.070,14|

Audit độc lập (không import metric/generatorbenchmark, khôngfit) tính lại
**1.479.612assertions/873hashchecks,0errors**, tái sinh40inputseries, đối chiếu
mọi baseline/truth/anchor/scale/7301trainingpairs từngfinalcase, selection,
modelJSON vàcổng. Đây không phải1,47triệu testđộc lập hay trustedtimestamp.
File `output/audit_level_20261019.json` có cả metric mean-case và pooled theo
family, phân biệt rõ. ModelJSON kiểmobjective/trees/depth/features, không chứng
minh mọi thao tác trongRAM. Filesystemtime không là chữ ký thời gian độc lập.

Hai replaycase chọn trước khi xemfinal (weekly1911 vàlevel_shift1911) refit
cùnginput: **8/8fileSHA giống tuyệt đối**,2/2metricpayload giống nhau. Không
tính replay là dữ liệu kiểm định mới. Nguồn V1 và dữ liệu kinh doanh giữ nguyên.

Đối chiếu riêng bộ15case cũ (đãthấy/diagnostic, không holdout mới):V2thắng14/15,
meanratio0,6006364668978599 = giảmMAE39,9364%; level_shift giảm21,2142%.
V1gốc vẫn giữ kết quả kém12,0067%, không viết lại.15/15raw comparator modelJSON
refit cóSHA giống hệt selectedXGBmodel V1gốc: so sánh không đổi đối thủ yếu hơn.
Không dùng diagnostic này chọn lại cấu hình; selection V2đã khóa trước đó.

**Full-suite worktree19/10:1.432/1.432testsOK293,820s,0failure/error/skip.**
Snapshot761textinputs/source_unchanged=true, result tại
`output/acceptance_verification/20261019T023626Z/result.json`. PostgreSQL/PostGIS
TESTdatabase random của lượt được tựhủy; không reset DBnghiệpvụ. MD5hasher và
legacyfulfillmentfixturecompat chỉ trong testprocess (strictregressions override),
không đổi security/runtime settings. Sau PASS chỉ bổ sung receipt/tài liệu.
Không mượn full1420 của nguồn16/10 hoặc1461dirtymain; không chứngnhận CIhayRender.

Frameworkcheck0issues/migrationdriftNoChanges trênTESTriêng; Bandit1.9.4 hai
script0finding/error; compileall vàgitdiffcheck đạt.12V2testsOK10,133s và
23model+V1testsOK94,967s là lượt chồnglặp riêng, không cộng vào full1432.
Log RED banđầu và RED reviewguards giữ nguyên, khôngxóa/nới testcase cũ.

Bộ90ngày nghiệpvụ họcthuật14/10 và điểm kémMA7 trướcđó không bị viết lại;
lượt này chưa đánhgiáV2 trên bộ đó. Nghiệmthu ở đây hoàn tất **bản thử nghiệm
thíchnghi và các cổng môphỏng đã khóa**, không phải100%accuracy/khả năng thắng
mọidữliệu hoặc rolloutproduction. Không phát sinh thông tin cần người dùng
cung cấp thêm trong phạm vi offline đã chốt.

## Sử dụng bản thử nghiệm

Hai module mới: `scripts/forecast_level_adaptive.py` (fit/predict) và
`scripts/forecast_level_benchmark.py` (evidence runner). Kernel nhận DataFrame
daily liên tục,cột targetkhôngâm; tối thiểu57observations để cótrainingpair.
Inference cần56ngày lịch sử và1–14ngàyliêntiếp saungàycuối. Không tự đọcDB.

```python
from scripts.forecast_level_adaptive import fit_direct, model_params, predict_direct
import pandas as pd
model = fit_direct(history, model_params())
dates = pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=14)
prediction = predict_direct(model, history, dates, alpha=1.0)
```

Để lặp lại study trong thư mục output **mới**: đặt OMP/OPENBLAS/MKL/NUMEXPR
NUM_THREADS=1, rồi `python scripts/forecast_level_benchmark.py --output PATH_MOI`.
`--resume` chỉ dùng với cùng source/runtime/input, không ghi đè kết quả cũ.
Replicate cùngseed không thành bằng chứng holdout mới. Chưa tích hợp kernelV2
vào ForecastRun/worker/API. Muốn chuyển production cần test dữ liệu nghiệp vụ
đại diện, feature/provenance contract và rollback artifact; không tự promote.

## Ranh giới và quyết định kỹ thuật

Thực hiện inline cùng một reviewer độc lập để hạn chế quota/context; diagnostic
và arithmetic audit độc lập song song. Giữ nguồn chưa commit trong worktree do
chưa có yêu cầu tích hợp. Chi phí của lựa chọn: cần giữ worktree và review/tích
hợp riêng trước production. Training dùng mọi cặp origin→target còn trongcutoff,
tail có ít horizon hơn, trace công khai; không giả như balanced full-horizon.
Review phát hiện hai guard pair/case-completeness, đã thêm RED→GREEN; bảng
metric theo family sẽ ghi riêng, không dùng pooledMAE thayprimary meanratio.
