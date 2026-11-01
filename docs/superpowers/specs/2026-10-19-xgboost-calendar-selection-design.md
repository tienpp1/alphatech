# XGBoost V3 — chọn đặc trưng lịch bằng validation quá khứ

## Phạm vi chủ dự án xác nhận

Giữ XGBoost, thêm chọn đặc trưng lịch; không chuyển sang dự báo lai/baseline.
Tiếp tục worktree riêng, không production/Neon/DB/migration/97-ledger change.
Không sửa các nguồn hay kết quả đã khóa của V1/V2. Không hứa thắng mọi dữ liệu.

Case noise1912 V2 thua18.946,78VND/ngày (1,1342%); thắng6/10origin nhưng
model dành30,73% training splitgain cho calendar dù generator iid. Đây là dấu
hiệu spurious fit, không là bằng chứng causal duy nhất hoặc lỗi riêngseed.
Chênh lệch nhỏ hơn biến thiên block: descriptive SE50.343VND; không đủ cơ sở
gọi suy giảm có hệ thống. Không sửa đáp án, bỏcase hoặc đổi metric cũ.

## Thay đổi tối thiểu

Reuse V2 origin_features/supervised_pairs/model_params và reconstruction alpha1.
XGB L1/depth2/200trees,rate.05,subsample1,colsample1,lambda1,random42,n_jobs1.
Ba featuremode cố định theo thứ tự đơn giản trước:

1. `none`: bỏ day_of_week/day_of_month/month/is_weekend; giữ horizon và tất cả
   lag/rolling/trend normalized past-only.
2. `weekly`: chỉ giữ day_of_week/is_weekend trong calendar.
3. `full`: nguyên18feature V2.

Không nhận scenario/seed/têncase/ngàybreak làm inputmodel/selector. Wrapper
predict chỉ subset cột đã lưu khi fit; modelJSON lưu đúng feature_names. Model
không được tự suy ra mode từ dữ liệu target future hay cấu hình runtime khác.

## Quy tắc chọn per-series khóa trước khi fit

Mỗi chuỗi730ngày: fit3shadowmodels trên[:438], dự báo10block14ngày không chồng
lặp trên[438:584] (140ngày scored/6tail). Giữ blockloss MAE thực đo của mỗi
mode. Best=min(mean(blockloss)), fixed modeorder ties. SEMbest=sampleSD của
10blockloss best /sqrt(10). Chọn mode đơn giản đầu tiên có meanloss<=bestmean+
SEMbest. Đây là **one-standard-error simplification heuristic**, không là
confidence guarantee (các block/history có phụ thuộc). Không chọn theo R²,
không tìm lại ngưỡng sau khi thấy final.

Chỉ sau khi khóa toàn bộ case selections mới refit mode đã chọn trên[:584],
rồi score heldout[584:730]. V2full comparator fit cùng584rows/params/anchor/
horizon; nếu modefull được chọn có thể reuse chính model đó, ghi rõ reuse.
Không dùng model refit584 để chấm lại validation438:584. Không online đổi mode
trên10finalblock; chỉ cập nhật observations đã biết tại mỗi origin như V2.

## Dataset/protocol khóa trước

Generator V1 giữ nguyên5families/730ngày; không sinh giao dịch kinh doanh.
Development seeds2026101931/32/33, final seeds2026101941..50:65chuỗi/47.450rows.
15development chỉ báo cáo selection diagnostics; không gọi calibration scores
là test quality.50final là freshseed của cùng cơ chế mô phỏng đã biết, không
blind external/real-business validation. Final cohort pre-holdout[:584] được
dùng fit/chọn mode per-series, finaltargets[584:] không tham gia lựa chọn.

Primary bằng V2: equal-case mean unrounded MAE ratio/MA7. Comparator MA7,
naive1,seasonal7 recursive cùngorigin/horizon/truth. Báo thêm V3/V2 percase,
family và overall; giữ tất cả loss,RMSE,MAPE,R²,bias vàbyhorizon.

Cổng predeclared: đủ50unique finalcases đúngID/scenario/seed; overall<1vsMA7;
noise meanratio<1vsMA7 và mean percase V3/V2<=1; mọi family<=1.10vsMA7;
weekly/trend/shift mỗi family<1vsMA7 vàV3/V2<=1.05; mỗi case<=1.50vsMA7.
Không đặt50/50wins như một bảo đảm mọi mẫu; count thực tế phải công bố.

Case V2noise1912 được chạy sau freshfinal bằng cùngrule đã khóa, chỉ là
**seen diagnostic** để biết chênh1,13% cũ còn không; không gọi holdout mới và
không dùng nó tune rule. Nếu vẫn thua phải ghi thật, không vòng lặp épPASS.

## Evidence / safety

Hai moduleV3 riêng, reuse immutable V1/V2 sources. Freeze65input/source/runtime/
protocol trướcfits, checkpoint exclusivewriter/hashed case receipts, failure
retained. Calibration65receipts lưu3models/CSV/blockloss/selection; selection
manifest toàn bộ trước50outerfinalreceipts. CSV final có V3/V2 và3baselines;
featurecontract/fitcutoff/checkpointbinding rõ. No network, threads1,1heavyjob.

TDD: filtering/replay/selection arithmetic, no future feature, training vs
validation cut, tie/zeroSEM/NaN/partialcase, pairedscore, persistence/resume.
Fresh review; independent arithmetic/hash audit; replay2case chọn trước
(weekly1941,noise1941); old1912 diagnostic. Fullworktree suite/PostGIS TEST
riêng tựhủy; Bandit/compile/diff; updateCURRENT/CHANGELOG/inventorydoc only.
Gói mã/evidence mới trênD, không overwrite V1/V2. Chưa commit/push/deploy.
