# XGBoost V4 — calendar như một nhóm nguyên vẹn

## Intent và quyết định

Chủ dự án yêu cầu tiếp tục hoàn thiện sau V3, giữ XGBoost/thử nghiệm riêng,
không production. Builder chọn thay đổi hẹp: ablate toàn bộ calendar thay vì
chọn partial-weekly. Đây không là lời hứa chủ dự án đã duyệt riêng cấu trúc này
hoặc thuật toán sẽ thắng mọi dữ liệu. Mục tiêu nghiệm thu là tất cả cổng cố
định dưới đây, không100% dự báo đúng hoặc100% mọi mẫu tương lai.

V3noise1912 đã được sửa nhưng preservationFAIL. Forensics thấy1944weekly thực
sự tốt hơn full0,9309% trên validation, pairedSE gần bằng gain, rồi lệch dương
sau downshift chưa xuất hiện trong fit. Vì vậy đổi one-SE thành argmin không
đủ. Savedmodel cho thấy std28 sau shift ngoài trainingrange và partial-weekly
phụ thuộc mạnh hơn vào volatility correction. Đây là phản ứng model đã đo,
không causal/generalization proof. Kiểm65 calibration ĐÃ XEM bằng2-mode rule
cho39full/26none, không structured-none; chỉ là chẩn đoán, không holdout V4.

## Architecture cố định, không làm nhiều thay đổi một lúc

Giữ nguyên V2/V3 source/data/results. Model/provenance pipeline cũ không sửa.
V4 wrapper chỉ cho `none`14 features hoặc `full`18 features qua V3fit_mode/
load_mode. Calendar4cột có mặt cùng nhau hoặc vắng cùng nhau. `weekly` model
bị từ chối ở API V4load/fit. Không scenario/seed/caseID input hoặc detect ngày
break. Không statistical fallback/averaging. FixedV2 L1/depth2/200trees,
rate.05/subsample1/colsample1/lambda1/random42/n_jobs1, alpha1/MA7anchor unchanged.

Chọn giữa2 mode bằng cùng one-SE simplicity heuristic, ordernone/full.
Exact2keys, mỗi key10finite nonnegative numeric blockMAE, rejectbool/missing/
overflow. Best=minmean, exacttie ưu tiênnone. SEM=sampleSD(best10loss)/sqrt10;
chọnnone nếu meanlossnone<=bestmean+SEM, còn lạifull. Đây là candidate-space
simplification, **không tuyên bố đã chứng minh stability**, không confidence
guarantee. Rule vẫn có thể bỏ calendar yếu hoặc chọn mean hơi kémfull.

## Chronology và cohort khóa trước fit

Mỗi chuỗi730ngày: shadowfit[:438], validation[438:584],10block14day/140scored,
6tail bỏ. Khóa đủ115 selections trước mọi final refit[:584] vàfinal[584:730]
10block14day. Mỗi origin chỉ dùng actual đã biết, không futuretruth trongblock.
Không dùng refit584 chấm validation. Full selected thì reuse với comparatorV2.

Giữ nguyên5generator V1/formulas, ngày2024-01-01..2025-12-30, VND, không sửa
historical transactions/Neon/businessDB. Developmentseeds2026102211/12/13;
finalseeds2026102221..2026102240.115series/83.950rows,100freshfinalcases,
20mỗi family. Đây là freshseed của sameknown mechanisms, không externalblind.
Cohort lớn hơn V3 để giảm phụ thuộc vài seed; không là power/confidence claim.
Mọi V1/V2/V3final bây giờ làSEEN; không tái công bố thành holdout mới.

## Cổng giữ nguyên và tăng kiểm soát tổng thể

Reuse V3gates không sửa: đủ expectedcase duy nhất đúngID/scenario/seed,
finite unrounded metrics; overallmeanMAEratio/MA7<1; noise meanratio/MA7<1 và
meanpercaseV4/V2<=1; mọi family<=1.10vsMA7; case<=1.50vsMA7;
weekly/trend/levelshift mỗi family<1vsMA7 vàV4/V2<=1.05. GiữlevelshiftgateV2.
Thêm trước fit: overall meanpercaseV4/V2<=1, mọi ratioV2 finite>=0. Không nới
bất kỳ cổng cũ, không chọn metric sau kết quả. Count actualwins/ties/losses.
Giữ MAE/RMSE/MAPE/R²/bias/allhorizons, zeroactualMAPEexclusions/negativeR².
Study COMPLETED khác performancePASS; exit3cho qualityFAIL, không bỏ evidence.

Một protocolV4/finalcohort cố định, chạy một lần. Nếu qualityFAIL vẫn giữFAIL,
không tự thayseed/generator/gate hoặc thử liên tiếp holdout đếnkhiPASS.

## Evidence, verification, delivery

New scripts forecast_atomic_calendar.py + forecast_atomic_benchmark.py; tests
test_forecast_atomic_calendar.py + test_forecast_atomic_benchmark.py. Reuse
actual XGB/schema/evaluate/score/gate/evidence primitives; no app/schema/API/UI.
10sourcehashes (8V3+2new),runtime/input/protocol freeze,caseboundreceipts,
exclusivewriter/checkpoint/verifiedresume; immutable115selections before100final.
Calibration2models+700rowCSV/case; final2models+700rowCSV/case, methodsatomic,
v2,ma7,seasonal7,naive1. Keep failures/attempts. Neveroverwrite oldstudy/archive.

Fresh review; independent arithmetic/hash/modelJSON inference audit; exactreplay
predeclared finalnoise2221/shift2221; diagnostics oldnoise1912 andoldshift1944
afterfreshfinal only, labelSEEN andcheckV2comparatorSHA againstoriginal.
TDD for2modearithmetic/schema/invalid inputs/cutoff/failure/resume/gates.
Fullworktree suite on fresh disposable loopbackPostgreSQL/PostGISTEST, auto
teardown; fastMD5/legacyfixturecompat onlytestprocess disclosed, runtimeunchanged.
Bandit/compile/diff; CURRENT_STATUS/CHANGELOG/inventory/report; SHA-whitelist
delivery onD, no secrets/DBdump. No commit/push/deploy/97progresschange.
Oneheavyjob at a time/nativehidden/threadcaps1/networkguard, checkpoint survives
desktopclosure ifOSstillruns. No claim desktopcrash fixed or browserUATneeded.
