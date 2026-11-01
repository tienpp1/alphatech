# Thiết kế đề xuất: thực nghiệm XGBoost với lịch sử mô phỏng

Ngày: 16/10/2026. Trạng thái: **APPROVED — synthetic offline trước**.
Chủ dự án chốt phạm vi qua câu trả lời ngày 16/10: “Thực nghiệm mô phỏng riêng
trước, chưa đổi production (đề xuất)”. Builder check độc lập: không còn câu hỏi
quan trọng trước lập kế hoạch. Chưa tạo dữ liệu hoặc sửa forecasting runtime.
Không thay đổi trạng thái, cấu trúc hoặc tỷ lệ hoàn thành của sổ 97 mục.

## 1. Yêu cầu và ranh giới bằng chứng

Chủ dự án yêu cầu xử lý việc XGBoost kém MA7, cho phép tự tạo lịch sử cần thiết,
sử dụng các skill Superpowers, và hỏi khi cần thông tin. Quyết định kỹ thuật đề
xuất của người thực hiện là tạo **benchmark học thuật synthetic độc lập**, không
bịa giao dịch vào Neon/local business tables và không nối lịch sử giả vào dữ liệu
cũ rồi gọi đó là dữ liệu quan sát. Việc không ghi business DB là lựa chọn an toàn
đã được người dùng phê duyệt cho đợt này.

Một kết quả tốt trên synthetic chỉ chứng minh mô hình học được cấu trúc của bộ
mô phỏng đó. Nó không thay đổi kết quả lịch sử ngày 14/10, không chứng minh độ
chính xác thương mại và không bảo đảm XGBoost luôn thắng MA7. Không lặp sinh
dữ liệu, đổi seed, đổi công thức hoặc mở rộng grid đến khi tìm được một kết quả
thắng rồi bỏ các lần thua.

## 2. Điều đã kiểm tra, không phải giả định

Bundle `output/forecast_validation_closed_20261014` và nguồn thực nghiệm khớp
hash của lần trước. Dữ liệu 90 ngày, 54/18/18 train/validation/holdout; train
chỉ còn 40 dòng supervised sau lag14. Có 16 ngày gap-fill 0, không phải bằng
chứng doanh số thực tế bằng 0. Năm origin recursive chồng lấn không phải năm
thực nghiệm độc lập.

Mức trung bình tất cả ngày: train 30,790 triệu, validation 46,060 triệu, holdout
22,806 triệu VND. Đây là mô tả thay đổi phân phối, chưa chứng minh quan hệ nhân
quả. XGB dự báo quá cao trên holdout; recursive MAE 24.861.281,73 so với MA7
17.590.478,73, kém 41,33%. Các kết quả xấu vẫn được giữ nguyên.

Các candidate cũ dùng `reg:squarederror`; đặt `eval_metric=mae` không biến hàm
loss thành MAE. Kiểm tra hướng robust loss là giả thuyết hợp lý nhưng chưa phải
bản sửa đã được chứng minh. Pipeline hiện có nhãn `BASELINE_PREFERRED`, nhưng
vẫn công bố forecast của XGB; chưa có cơ chế lựa chọn baseline để thực thi.

## 3. Phạm vi đề xuất cho đợt này

Tái sử dụng feature builder, recursive prediction, metric và baseline của
`apps/forecasting`; thêm công cụ thực nghiệm offline, test, protocol và báo cáo.
Không thay model database, migration, quyền truy cập, business transaction,
forecast production hoặc tự promotion model. Không thêm thuật toán/domain
song song. Nâng cấp lựa chọn mô hình cho runtime là một quyết định khác ở mục 9.

Kết quả bàn giao gồm: dữ liệu synthetic có provenance; protocol khóa trước khi
chấm; XGBoost thật được fit; đối sánh công bằng; artifact có hash/replay; báo cáo
cả thắng và thua. Mục tiêu kỹ thuật là khắc phục hạn chế của **thực nghiệm** và
xác định khi nào XGBoost có ích, không đặt test bắt buộc mô hình phải thắng.

## 4. Bộ dữ liệu và cách khóa thử nghiệm

Đề xuất 5 kịch bản, mỗi chuỗi 730 ngày, đơn vị VND, không PII:

1. Mức nền ổn định có nhiễu: negative control, mô hình phức tạp có thể thua MA7.
2. Mùa vụ theo tuần và lịch: tín hiệu calendar đã có trong feature builder.
3. Xu hướng tăng từ từ cùng mùa vụ: kiểm tra khả năng theo kịp thay đổi mức.
4. Doanh thu gián đoạn và các đợt tăng đột biến: kiểm tra độ nhạy outlier.
5. Mức nền thay đổi theo thời gian: stress test, không hứa dự báo trước cú sốc.

Công thức, biên độ, phân phối nhiễu, thời điểm break và code generator phải ghi
trong protocol trước lượt benchmark đầu. Đây là dữ liệu giả lập, không hiệu
chỉnh để giống một doanh nghiệp đã được khảo sát. Mọi dòng CSV có provenance
qua metadata và dataset hash; không dùng nhãn `business_observed`.

Hai cohort seed cố định trước khi fit:

- Development: 2026101601, 2026101602, 2026101603.
- Final evaluation: 2026101611, 2026101612, 2026101613.

Tổng 30 chuỗi/21.900 daily rows. Công thức đã biết nên đây **không phải** bộ
holdout độc lập do người chấm bên ngoài tạo. Tuy nhiên cohort cuối không tham
gia chọn candidate, sửa generator hoặc chọn feature. Bất kỳ việc sửa protocol
sau xem kết quả phải tạo version mới, giữ nguyên kết quả version trước.

Mỗi chuỗi chia raw rows theo thời gian: 438 train, 146 validation, 146 test.
Không shuffle. Lưu CSV, metadata, protocol/source hash trước fit; output mới
không được ghi đè artifact đã có. Phân vùng test của development cũng không
dùng để lựa chọn; có thể để chưa chấm để giảm công việc và tránh thêm tuning.

## 5. Candidate và lựa chọn

Giữ candidate reference 100 trees/depth4/squared-error của đợt trước. Đề xuất
grid mới đúng 12 cấu hình: objective {squarederror, absoluteerror}, depth {2,4},
trees {100,250,400}; các tham số khác cố định như reference, `n_jobs=1` và
random_state42. Không early stopping/eval_set trên final test. Giữ reference
riêng nếu cần tránh trùng candidate, không đổi danh sách sau xem kết quả.

Chọn **một cấu hình XGB chung** bằng mean relative MAE đối với MA7 trên
validation recursive của toàn bộ 15 chuỗi development. Mỗi chuỗi/kịch bản có
trọng số ngang nhau; tỷ lệ MAE chỉ tính khi baseline MAE > 0, trường hợp 0 phải
ghi chưa xác định và quy tắc tie-break cố định theo thứ tự candidate. Thua không
bị bỏ khỏi trung bình. Fit lỗi được lưu, candidate không đủ các chuỗi không
được chọn. Nếu không có candidate hợp lệ, kết thúc FAILED, không chấm final.

Các mức loss/depth/tree này là lựa chọn đề xuất của người thực hiện, không phải
thông số đã được người dùng chốt hoặc đảm bảo tối ưu. Không thêm log-transform,
biến ngoại sinh hoặc feature mới ở version đầu: tránh thay nhiều biến cùng lúc.

Khóa selection.json trước final evaluation. Với từng chuỗi final, fit cấu hình
đã chọn bằng train+validation của **chính chuỗi đó**, không dùng final test;
reference fit cùng lịch sử. Dữ liệu mô phỏng chỉ dùng trong artifact offline.

## 6. Chấm điểm công bằng

Primary: 10 block recursive 14 ngày không chồng lấn từ đầu mỗi partition 146
ngày; 140 target dates, 6 ngày đuôi không nằm trong primary phải ghi rõ. Trước
mỗi origin chỉ dùng lịch sử đã có; trong block mỗi phương pháp append dự báo
của chính nó, không đọc actual tương lai. Không refit giữa origin.

XGB selected, XGB reference, MA7, seasonal7 và naive1 dùng cùng origin, horizon
và target population. Secondary: one-step quan sát lịch sử, ghi nhãn riêng,
không trộn hai kiểu thành cùng một kết quả.

Lưu MAE/RMSE/R2/bias, theo kịch bản/seed/horizon; báo số unique dates và origins.
Không biến các hàng dự báo thành cỡ mẫu độc lập để tính chứng nhận thống kê.
Tổng hợp win/loss/tie và mean/median cải thiện MAE; tỷ lệ phần trăm không xác
định khi baseline MAE0 phải giữ null. Không chỉ báo kịch bản tốt nhất. Không
chứng nhận prediction intervals ở đợt này.

## 7. Tests, review và vận hành an toàn

Theo TDD: RED rồi GREEN cho deterministic generator/provenance, validation-only
selection, final-target perturbation không đổi selection/model/first-origin
prediction, non-overlap origins, baseline parity, fit failure retention,
no-overwrite, hash/replay. Test kiểm protocol, **không assert XGB thắng**.

Không Django setup/DB/network/provider trong runner. Chạy một job nặng tại một
thời điểm, native background hidden khi cần, native threads1, log/checkpoint
trên đĩa và đầu ra gọn vì máy từng bị toàn ứng dụng thoát. Không hứa đã sửa
nguyên nhân crash. Không cần browser cho metric offline; không tạo UI chứng
minh thay số liệu. Regression feature/metric/offline phải pass, sau đó review
độc lập và verification-before-completion trước bất kỳ tuyên bố hoàn thành.

Runtime/script phải có manifest versions/source/input/artifact hash, trạng thái
từng case và resume xác minh protocolhash (không ghi đè failure bằng success).
Không paid API, không cài dependency hoặc deploy trong đợt đề xuất này.

## 8. Tiêu chí bàn giao và trường hợp chưa đạt

Hoàn tất đợt synthetic khi chạy đủ protocol/case hoặc có failure được ghi đúng,
test/replay/review đạt và báo cáo mọi kết quả. Nếu XGB vẫn thua ở một hoặc nhiều
kịch bản thì ghi đúng; không coi yêu cầu "chỉ dừng khi xong" là quyền ép score.
Không kết luận đã cải thiện trên dữ liệu lịch sử thật hay đã hoàn tất mọi mục97.

Muốn đánh giá lại lịch sử cũ sau thay cấu hình chỉ được ghi **exploratory / test
đã xem**, không dùng làm chứng nhận mới. Muốn xác nhận cải thiện thực tế cần dữ
liệu có nguồn và thời đoạn tương lai chưa dùng điều chỉnh.

## 9. Quyết định và phần nằm ngoài đợt này

1. Đã chốt **synthetic offline riêng để bảo vệ đồ án**, giữ lịch sử
   thật/Neon và forecast runtime không đổi ở đợt này.
2. Nếu mục tiêu tiếp theo là cải thiện forecast đang phục vụ trong web, cần chốt
   cơ chế validation chọn XGB hoặc baseline, hiển thị rõ phương
   pháp đã dùng thay vì gắn nhãn XGB cho MA7 không? Đợt này cần thiết kế riêng
   vì tác động tới artifact/inference/UI và không bảo đảm XGB thuần luôn thắng.

## Nguồn kỹ thuật đối chiếu

- XGBoost, Learning Task Parameters: phân biệt objective/evaluation metric và
  reg:absoluteerror: https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html.
- Scikit-learn, TimeSeriesSplit: chia tập theo thứ tự thời gian, không dùng
  KFold/shuffle như dữ liệu độc lập:
  https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html.

Các nguồn này hỗ trợ phương pháp, không xác nhận model của đồ án đã tốt hơn.
