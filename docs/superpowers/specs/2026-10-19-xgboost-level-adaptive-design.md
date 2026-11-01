# XGBoost thích nghi mức doanh thu — thiết kế V2

## Mục tiêu và phạm vi đã xác nhận

Ngày19/10 chủ dự án đồng ý bản thử nghiệm riêng, chưa đổi production. Sửa cơ
chế không thích nghi mức doanh thu trong benchmark16/10; không hứa thắng mọi
chuỗi tương lai. Giữ nguyên Neon, runtime app, migration, dữ liệu kinh doanh,
nguồn/kết quả V1 và cấu trúc/tiến độ97. Không fine-tune trên final V2.

## Chẩn đoán có bằng chứng

V1 fit target tuyệt đối một lần. Sau khi mức mới đã được quan sát,294/294 dự
báo ở7origin sau giảm vẫn cao hơn thực tế: MAE12,138triệu vs MA7 2,419triệu.
One-step cũng lệch11,87triệu. Đây chủ yếu là thiếu cơ chế thích nghi mức, không
chỉ lỗi recursive. V1final đã xem, chỉ được gọi diagnostic/seen.

## Thiết kế thuật toán (quyết định của người triển khai)

Một XGBRegressor dự báo trực tiếp h=1..14, không đưa dự báo vào lag để dự báo
ngày tiếp. Tại mỗi origin chỉ dùng lịch sử đã biết. Anchor=mean7; scale=
max(mean7,mean28/4,1VND). Học residual `(actual_h-anchor)/scale`, khôi phục
`max(0,anchor+alpha*scale*prediction)`. Đây là **MA7-anchored direct residual
XGBoost**, không tuyên bố XGBoost nguyên bản độc lập baseline.

Features: lag1/7/14/28 và mean7/14/28/56, std7/28 chia scale; anchor/scale;
tỷ lệ mean7-mean28 và mean7-mean14 chia scale; horizon; lịch ngày đích
day_of_week/day_of_month/month/is_weekend. Không input scenario/seed/date-break,
không đọc actual sau origin. Training chỉ chứa cặp origin,target đều nằm trước
fit cutoff, minimum history56 ngày. Sample weight=scale/median(training scales)
để loss normalized không vô tình ưu tiên origin rất nhỏ. Floor1VND có nghĩa
scale equivariance chỉ chính xác khi floor không hoạt động.

Grid khóa trước: objective L2/L1 × depth2/4,200trees,learning_rate.05,
subsample1,colsample1,lambda1,random_state42,n_jobs1; correction alpha.5/1.
Bốn fits/case, tám ứng viên; alpha0 bị loại để không đổi tên MA7 thành XGBoost.
Chọn duy nhất một cấu hình chung bằng mean case MAE ratio/MA7 unrounded trên
development validation, fixed-order ties. Không đổi grid sau khi mở final.

## Thiết kế thực nghiệm khóa trước khi fit

Tái sử dụng generator V1 nguyên trạng (5families,730ngày,438/146/146,h14,
10origin không chồng lặp,140ngày scored/6tail), chỉ thay seed đã khóa:
development2026101901/02/03, final2026101911/12/13/14/15:40chuỗi,29.200ngày.
Các family cố ý tương tự V1: đây là fresh-seed test cùng cơ chế mô phỏng,
không phải blind holdout độc lập, dữ liệu thương mại hoặc đủ mọi loại regime.
Validation không có cú giảm final: thích nghi phải đến từ representation
past-only, không từ biết trước ngày giảm. Giới hạn này phải công bố.

Fit development[:438], validation[438:584]; sau selection fit final[:584].
Tại mỗi final origin cập nhật lịch sử quan sát, không refit. Baselines MA7,
seasonal7,naive1 recursive và V1selected absolute-XGB L1/depth2/250trees dùng
cùng origin,horizon,truth. Primary equal-case mean unrounded MAE ratio toMA7.
Giữ nguyên mọi loss,negativeR²,RMSE/MAPE/bias,per-case/per-family/per-horizon.

Cổng đo lường đặt trước: overall ratio<1, level_shift family ratio<1,
mọi family ratio<=1.10, không case ratio>1.50; nếu không đạt ghi FAIL, không
đổi generator/metric/cutoff/seed hay chạy lại chọn kết quả đẹp. Các cổng này
không bảo đảm thắng mọi case hay mô hình production đã cải thiện.

## Evidence và phục hồi

Script V2/new module riêng, không sửa4nguồn frozen V1. Freeze protocol,
runtime, source SHA, input SHA trước fitting; selection immutable trước final.
Tái sử dụng locks/checkpoint/case receipts V1; V2 phải kiểm source/runtime/
receipt hashes khi resume, giữ failed/incomplete attempts. Lưu model JSON,
feature contract,fit cutoff,training pair counts,origin traces,CSVpredictions,
metrics/selection/results và manifest. Không DB/network; threads1, một job nặng.

## Nghiệm thu

TDD: arithmetic reconstruction; training cutoff/no future features; invalid
daily histories; zero/constant; origin-only inference; recent-level adaptation
with fixed residual model; realXGB replay; selection before final; incomplete/
failed/tampered evidence. Existing18tests giữ nguyên. Independent reviewer và
arithmetic auditor; full worktree suite, Bandit,compile,diffcheck. Báo cáo phân
biệt fresh final,old diagnostic,localtests và production chưa đổi. Không dùng
browser để giả minh chứng ML. Không commit/push/merge/deploy trong lượt này.
