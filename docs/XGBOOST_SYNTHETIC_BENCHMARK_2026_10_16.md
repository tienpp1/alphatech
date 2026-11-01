# XGBoost và MA7 — thực nghiệm synthetic ngày16/10/2026

Trạng thái: **hoàn tất đợt thực nghiệm offline và regression; chưa chứng minh XGB vượt MA7 bao quát**.

## Phạm vi chủ dự án đã chốt

Thực nghiệm mô phỏng riêng trước, chưa đổi production; thực hiện trong native
worktree `C:/Users/anhbe/.codex/worktrees/xgb-synthetic-benchmark/ai_business_platform`
từ base `4f3c6ab1d043268bb615d6c9f1078b0350cbb52a`. Không trộn thay đổi đang dở ở
`D:/ai_business_platform`. Không ghi Neon hoặc business DB, không migration,
không thay forecast đang phục vụ, không sửa tiến độ/cấu trúc sổ97.

Đây là dữ liệu synthetic do công thức tạo ra, không phải đơn hàng thực. Kết
quả cũ ngày14/10 vẫn giữ nguyên: recursive14-day MAE XGB24.861.281,73 so với
MA7 17.590.478,73 (XGB kém41,33%). Thực nghiệm mới không thay thế thất bại đó
bằng một tuyên bố chất lượng thương mại.

## Phương pháp đã khóa trước fit

30 chuỗi ×730ngày =21.900 dòng: năm kịch bản (nhiễu, mùa vụ tuần/lịch, xu hướng,
gián đoạn/outlier, thay đổi mức), mỗi kịch bản ba seed development và ba seed
final. Công thức/seed/input/source/runtime hashes được ghi trước fit tại
`output/forecast_synthetic_20261016/protocol.json` và `input_manifest.json`.

Raw split438/146/146 theo thời gian. Candidate12 =objective squarederror hoặc
absoluteerror ×depth2/4 ×trees100/250/400, các tham số khác cố định. Chọn một
cấu hình chung theo mean của15 tỷ lệ MAE so vớiMA7 trên development validation,
mỗi chuỗi trọng số ngang nhau. Thiếu case/lỗi fit làm candidate không đủ điều
kiện; giữ cả lỗi. Không dùng final để chọn hyperparameter hay sửa generator.

Chốt selection trước khi fit15chuỗi final. Mỗi model final fit train+validation
của chính chuỗi đó, không fit final targets. So selectedXGB/referenceXGB100d4/
MA7/seasonal7/naive1 trên cùng10block recursive14ngày không chồng,140ngày riêng;
6ngày đuôi không nằm trong primary và được công bố. Origin sau được biết actual
của các block đã qua; bên trong một block chỉ append dự báo của chính phương
pháp. Không refit giữa origin. One-step146ngày là secondary, nhãn riêng.

Generator và protocol đã biết nên đây không phải holdout mù do người độc lập
thiết kế. Nhiều seed/block không tự tạo chứng nhận ý nghĩa thống kê. Mô hình có
thể thắng ở dữ liệu có cấu trúc và thua khi có nhiễu/thay đổi phân phối; báo cáo
phải hiển thị tất cả. Không kiểm chuẩn prediction intervals trong đợt này.

## Mã nguồn, kiểm thử và review

- `scripts/forecast_synthetic_data.py`: sinh dữ liệu/công thức/provenance.
- `scripts/forecast_synthetic_benchmark.py`: chọn cấu hình, chấm recursive/one-step,
  artifact, immutable receipts, checkpoint/OS lock và resume.
- `tests/test_forecast_synthetic_benchmark.py`:18ca về dữ liệu, leakage, selection,
  replay, no-overwrite, partial failures, corruption/resume và case isolation.

RED ban đầu:3test thiếu generator;5test thiếu evaluator;4test thiếu evidence
runner. Sau implementation, fresh reviewer tìm4lỗi Important: trials cũ chưa
được so sánh, finalization không resume được, receipt chưa gắn từngcase/payload,
runtime chưa khóa trướcfit. Đã tái hiện4test/5failure (hai boundaryfinalization),
sửa rồi GREEN4/4. Toàn bộ18test cuối OK76.829s; không sửa/xóa test có sẵn.

Baseline8tests feature/offline trước implementation OK8.895s trên DBTEST riêng
466db62f03cd4dd4 đã tựhủy. Các test orchestration có double cho bước fit chậm
để tái hiện interruption; không dùng các double đó làm bằng chứng accuracy.
Tests model/replay/future-perturbation và benchmark sử dụng XGBoost thật.

Bandit1.9.4 từ `.venv-quality` quét hai script mới:0findings/0errors.
Python global và `.venv` không có Bandit, các lần probe đó thất bại và không
được tính là scanPASS; không cài dependency mới. Source/framework suite cuối
được ghi riêng sau khi thực nghiệm kết thúc, không mượn1461PASS ngày14/10.

## An toàn, tái lập và quyết định kỹ thuật

Job nền native hidden, một heavyjob tại một thời điểm; OMP/OPENBLAS/MKL/NUMEXPR
threads1, XGBn_jobs1. Socket guard chặnDNS/connect, không Django setup/DB/provider.
Manifest khóa Python3.14.5/NumPy2.4.3/pandas3.0.1/XGBoost3.4.1 và threadsettings;
resume từ môi trường khác bị từ chối thay vì trộn kết quả.

Receipt gắn bundle/case/candidate, payload đối chiếu hashedoutcome, checkpoint
giữ hashreceipt. Filetrials/results/resultmanifest tồn tại phải bằng phép tính
đã xác minh; không overwrite. Failedcase không tựretry; interruptedattempt giữ
nguyên và attempt mới tách biệt. Đây là phát hiện thay đổi bằng hash trong môi
trường local, không phải chữ ký số chống người quản trị sửa toàn bộ bằng chứng.

Rulings: triển khai inline và reviewcuối để giảm overhead; copy chỉ approved
spec/plan vào worktree; sửa phép tính tayMA7step2 thành192/7 trước code; giữ
worktree/artifact và không merge/push/deploy tựđộng. Chi phí/giới hạn: bộ test
worktree không chứng nhận các thay đổi chưa commit khác của main.

Deferred minors từ review: phân loại win/tie trong summary dùng MAE hiển thị đã
round2 (selection dùng số thô); sai biệt dưới đơn vị làm tròn có thể thànhtie.
Interruptedattempt có thư mục được giữ nhưng chưa có receiptinterruption riêng;
không gọi thư mục thiếu result là thànhcông. Chi tiết ở ledger của plan.

## Chạy lại

Từ worktree, với các native-thread env bằng1:

```powershell
python -m unittest tests.test_forecast_synthetic_benchmark -v
python scripts/forecast_synthetic_benchmark.py --output output/my_new_experiment
python scripts/forecast_synthetic_benchmark.py --output output/my_new_experiment --resume
```

Lệnh đầu không thay businessDB. Output phải mới; resume chỉ với cùng source,
protocol, runtime và artifacts chưa thay đổi. Không dùng lại tên output để che
kết quả thất bại. Bản chạy full đã có helper ignored `output/run_synthetic_job.py`
để guardnetwork/lưu exitreceipt; stdout/stderr và jobreceipt nằm trong output.

## Nguồn phương pháp

XGBoost phân biệt objective với evaluationmetric, có L1 `reg:absoluteerror`:
https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html.
Scikit-learn giải thích chia theo thời gian thay vì shuffle/KFold như IID:
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html.
Các nguồn này không chứng nhận kết quả benchmark của đồ án.

## Kết quả, kiểm chứng cuối và giới hạn

Job native kết thúc exit0 sau763,599s (12phút43,6giây), bắt đầu00:29:48UTC và
kết thúc00:42:31UTC ngày16/10/2026. Đủ180fit development và30fit final (selected
và reference cho15case), không lỗi fit. Socketguard bật, số lệnh mạng bị chặn0,
không networkcall/DB/provider từ job. Artifact/metric success là thực thi thành
công, không có nghĩa mọi model đạt chất lượng.

Validation chọn `xgb_07`: `reg:absoluteerror`, depth2,250trees, learning_rate0,05,
subsample/colsample0,8, reg_lambda1. Mean relativeMAE development0,655290789964;
đây không phải finalscore. Selection được lưu trước tất cả model final.

Kết quả primary recursive14ngày, trung bình ba seed final mỗi kịch bản:

| Kịch bản | MAE XGB (VND) | MAE MA7 (VND) | Mean cải thiện MAE theo case | Thắng/thua |
|---|---:|---:|---:|---:|
| Nhiễu quanh mức ổn định | 1.601.673,66 | 1.686.313,27 | +4,67% | 2/1 |
| Mùa vụ tuần và lịch | 795.046,45 | 4.875.474,77 | +83,71% | 3/0 |
| Xu hướng tăng từ từ | 1.483.792,47 | 3.121.752,22 | +52,42% | 3/0 |
| Doanh thu gián đoạn/outlier | 12.079.348,08 | 14.139.725,48 | +14,72% | 3/0 |
| Thay đổi mức đột ngột | 9.585.330,00 | 3.042.657,54 | **−215,55%** | 0/3 |

**Kết luận primary không phải XGB thắng toàn bộ:**11thắng/4thua, nhưng mean
của15tỷ lệ MAE theo case =1,120067433156, tương đương **kémMA7 12,0067%**.
Đây là cách tổng hợp cùng loại đã chốt khi chọn model, phải nêu trước các cách
tổng hợp khác. Trung bình gộp MAE VND của các case là XGB5.109.038,13 so với
MA7 5.373.184,66, giảm khoảng4,92%; đó là tổng hợp khác, không dùng để thay đổi
primary hoặc tuyên bố thắng chung. R² âm, RMSE/bias/MAPE và từng seed/horizon
được giữ trong CSV/JSON; cải thiện MAE không tự đồng nghĩa cải thiện mọi metric.

XGB học tốt mùa vụ có tín hiệu lặp lại trong mô phỏng này, nhưng không theo
kịp mức mới chưa có trong tập fit. Đây là diễn giải phù hợp stresscase, không
là chứng minh nguyên nhân thống kê hoặc lời hứa cho doanh nghiệp thật. Không
đổi generator/seed/grid sau khi thấy điểm final, không loại kịch bản thua và
không promotion model. Mục tiêu XGB vượtMA7 một cách bao quát **chưa đạt**.

Kiểm toán độc lập (không gọi metric/selector của application) tính lại tất cả
CSV, generator, baseline, selection, modelJSON và provenance:470.031checks,
1.589lượt kiểm SHA,0errors. Đây là đếm assertion kiểm file/số học, **không phải**
470.031test độc lập hoặc chứng nhận ý nghĩa thống kê. Báo cáo:
`output/audit_synthetic_receipts_20261016.json`.

Replay case chọn trước `final__weekly_calendar__2026101611` từ CSV đã frozen,
không chọn seed tốt nhất: hai modelJSON, recursiveCSV, one-stepCSV, metricsJSON
khớp SHA cả5/5; payloadmetrics cũng bằng nhau. Receipt nằm ở
`output/forecast_synthetic_replay_20261016/replay_receipt.json`.

Phần đã hoàn tất: dữ liệu/bộ thực nghiệm có thể tái lập, robustloss/chọn cấu hình
đúngvalidation, đối sánh/review/resume và bằng chứng thật. Phần chưa chứng minh:
XGB tốt hơn lịch sử cũ, tốt hơn mọi scenario, chất lượng thương mại hay forecast
production. Nếu tiếp tục cần protocol/cohort đánh giá mới và thiết kế thích ứng
mức/so vớibaseline rõ ràng; không tuning lại final đã xem. Runtime trên web và
giao dịch Neon giữ nguyên theo lựa chọn chủ dự án.

So với cấu hình XGBreference cố định, cấu hình được chọn thắng14/15case và
giảm mean relativeMAE khoảng6,85% trên synthetic. Đây là secondary comparator
đã định trước, không thay primaryMA7 còn kém12,01% và không là cải thiện trên
history90ngày cũ. Reference pooledMAE5.543.136,51VND; không so chéo bộ dữ liệu.

### Regression cuối và lỗi trung gian

RunnerHEAD không hỗ trợ `--fast-test-passwords`; lượt004613Z đã được chủ động
ngắt khi phát hiện flag bị bỏ qua, không tínhPASS. Chỉ ownTESTec6c31b9f36c49ad
được dọn sau đối chiếu creationlog và0activeconnections, khôngFORCE/killDBsession.
Helper cleanup lần đầu lỗi decodingcp1252 trước mọiSQL; sửa explicitUTF8 rồi
dọn thành công. Không dữ liệu nghiệp vụ bị xóa hoặc reset.

Lượt full thực sự005031Z:1420test/573.312s, FAILED1 duy nhất
`test_all_test_files_accounted_in_manifest`, vì chưa thêm tên test mới vào
HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md. Sourceunchanged=true/754textinputs,
DBTEST346e1544d30c4637 tựhủy. Chỉ sửa inventory, giữ test/assertion/log gốc.
Lượt này không được gọi làPASS. Chờ focusedgate và fullrerun sau sửa tài liệu.

Các fullrun dùng MD5 và legacyHOME_DELIVERY chỉ trong tiến trình TEST; strict
tests có override riêng. Runtimeproduction và mật khẩu hiện hữu không đổi.
Fullworktree base4f3+đợtsynthetic không bao gồm các thay đổi uncommitted khác
ở dirtymain; không dùng kết quả này chứng nhận cả main/CI hoặc production.

Lượt cuối `output/acceptance_verification/20261016T010546Z`: **1.420/1.420 OK,
692,628s,0failures/errors/skips**, exit0, source_unchanged=true,754textinputs.
DBTEST00c03cf87cd84c72 đã tựhủy. Chỉ thêm receipt tài liệu sau snapshotPASS,
không đổi script/test/app source. Các lỗi/gián đoạn trước giữ nguyên bằng chứng.

Focusedmanifest6/6OK3.385s; fresh Django check0issues, migrationdrift
Nochangesdetected, DBTESTriêng tựhủy; gitdiffcheck đạt. Không migration mới,
không thay sourceforecast runtime hoặc dữ liệu nghiệp vụ. Đây là kiểm chứng
worktree riêng, không phải fulldirtymain/GitHubCI hay liveproduction.

Code/evidence được giữ ở nativeworktree để chủ dự án chọn cách tích hợp.
Chưa commit/merge/push/deploy. Không archiveworktree hoặc xóa ignoredartifacts
trước khi lưu bộ bằng chứng ra nơi khác. Tóm tắt quyết định/giới hạn/minors ở
trên là đầy đủ cho đợt này; không coi việc đóng đợt là model đạt mọi mục tiêu.
