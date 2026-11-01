# Bộ chọn dự báo có cổng chất lượng — 01/11/2026

## Phạm vi được duyệt

Chủ dự án đồng ý chọn XGBoost hoặc MA7 từ validation quá khứ, hiển thị mô hình
thực tế, phát hành mã nguồn và thêm forecast mới vào Neon. Model JSON có kiểm
SHA/scope được lưu giới hạn 1 MiB trong ForecastRun hiện có để khôi phục suy luận
khi Render Free mất file. Không thêm bảng, không nạp giao dịch mô phỏng, không
đổi quyền hoặc ghi đè run cũ. Các lựa chọn phạm vi và sổ97 giữ nguyên.

## Quy tắc và ranh giới khoa học

`guarded_direct_v1` giữ mô hình direct MA7-anchored của V4. Chọn nhóm đặc trưng
lịch none/full bằng one-SE, chỉ dùng validation. XGBoost cần giảm MAE ít nhất10%,
lợi ích trung bình lớn hơn3 sample-SE và thắng ít nhất80% block; tối thiểu2 block
quan sát được. Đây là heuristic thận trọng của người triển khai, không phải
khoảng tin cậy99% đã hiệu chuẩn hay quy tắc được suy ra độc lập trước V4.

Nếu không đủ điều kiện thì chọn MA7 có lý do. XGBoost được chọn sẽ refit qua
validation, chấm holdout riêng, rồi refit serving trên toàn bộ lịch sử. Model
serving không được dùng để chấm holdout. Một cổng triển khai riêng từ chối run
có MAE holdout kém MA7; không đổi sang MA7 sau khi nhìn đáp án. Vì vậy số liệu
chỉ của các run được phép xuất bản không phải ước lượng holdout không thiên lệch.

Chỉ DAILY/horizon<=14/minimum initial fit70 đủ điều kiện candidate XGBoost.
MA7 cho WEEKLY nghĩa là7 kỳ. Dữ liệu tối thiểu49 kỳ, thiếu quan sát không được
biến thành điểm số đúng. Không dựng thêm giao dịch hoặc zero đến ngày hiện tại
để làm lịch sử trông mới. Nguồn lịch sử cũ vẫn có cảnh báo stale và R² âm.

## Study mới đã thực thi

Giữ nguyên generator V1:5 cơ chế mô phỏng, mỗi cơ chế4 seed mới
`2026110121..2026110124`, tổng20 chuỗi/14.600 dòng. Khóa source/runtime/protocol/
inputs trước fit; mỗi lựa chọn xảy ra trước holdout của chính case đó, không
tuyên bố khóa đồng loạt20 model trước mọi holdout. Đây không phải benchmark
mù bên ngoài hoặc dữ liệu giao dịch thật. Không đổi seed/ngưỡng sau kết quả.

Study identity SHA-256:
`be31e4c0abf7cc02d3cb8f57544b3533e4e0463f6b47d562f00bad8887205860`.

Thời gian433,522 giây, một luồng xử lý,0 lần thử kết nối mạng, không truy cập
database nghiệp vụ. Cả5 cổng định trước đạt. Kết quả13 thắng/7 bằng/0 thua MA7;
trung bình **tỷ lệ MAE từng case** là0,6517315445, giảm34,8268% so với MA7.
Không đánh đồng tỷ lệ trung bình này với MAE gộp của mọi giá trị doanh thu.

| Cơ chế | Trung bình MAE mô hình chọn / MAE MA7 |
|---|---:|
| Nhiễu | 1,0000000000 |
| Lịch tuần | 0,1808910745 |
| Xu hướng | 0,3034454239 |
| Gián đoạn/đột biến | 0,9491323708 |
| Đổi mức doanh thu | 0,8251888533 |

Mỗi case chấm đủ10 block×14 ngày=140 dòng, không trùng/thiếu;6 ngày dư cuối
holdout không thuộc block đầy đủ. Audit kiểm riêng grid validation/holdout,
nguồn actual, phép tính MAE/MA7 đệ quy và replay JSON serving. JSON serving
không phải model holdout đã lưu; không tuyên bố replay holdout từ model đó.

## Mẫu cũ và bằng chứng giữ nguyên

CSV V4 noise2236 được pin SHA
`75184768cdc9de5e5ec11d4860c2bb4a6867b5b0b9eda3f8035cbe50398b8d75`.
Đây là V4 final đã từng xem, được dùng làm diagnostic, không phải holdout mới.
Bộ chọn mới dùng MA7: MAE1.590.362,468925897, tỷ lệ1,0; phần thua0,6894% của
XGBoost V4 không còn trong lựa chọn mới. Báo cáo V4 vẫn giữ kết quả cũ99/100,
không sửa hoặc che lỗi. V1/V3 FAIL cũng giữ nguyên.

Bằng chứng máy-readable nằm dưới `output/forecast_guarded_release_20261101/`,
receipt `output/guarded_study_receipt_20261101.json` và
`output/guarded_audit_20261101.json`. Output/model/data không công bố lên GitHub.
Chỉ source, test và tài liệu nghiên cứu được đưa vào release. Local full test,
GitHub CI, Render và Neon là các cổng riêng: không suy ra chúng đã đạt từ study.
Hồ sơ vận hành thực tế được lưu riêng tại
`D:/AlphaTech_Private/forecast_guard_20261101/` sau khi thực thi.

## Kiểm thử source trước phát hành

Tree573d219: full local **1.508/1.508 tests OK**,279,731 giây,0 failure/error/
skip;788 source files giữ nguyên trong run. Database TEST ngẫu nhiên riêng đã
được hủy đúng phạm vi. Receipt:
`output/acceptance_verification/20261101T124111Z/result.json` và `django.log`.
MD5 password hashing chỉ ở process TEST, legacy fulfillment chỉ để tương thích
fixture; không đổi runtime hoặc bỏ các ca kiểm strict fulfillment.

Framework check0 issues và migration dry-run không thay đổi, cũng trên TEST
riêng. Secret-pattern scan869files/0findings; Bandit227files/34.402LOC/0findings
trong phạm vi cấu hình hiện có (1 check được loại trừ có sẵn, không thêm nosec).
Không coi scanner là bằng chứng secret đã rotate hoặc không có lỗ hổng mọi loại.

Các review core/lifecycle/study và fix round đã được thực hiện. Lỗi trung gian
về coverage evidence, nhãn mô hình, chart và cleanup được giữ log RED/failed;
GREEN2 của lượt fix từng có4 NameError, đã sửa và chạy lại34/34OK13,137 giây.
Full1508 là lượt sau các bản sửa đó; không biến các log lỗi thành PASS.
Các cập nhật tài liệu sau full không được gọi là full runtime mới; phải giữ
non-document source fingerprint trước khi push. CI/live receipts là cổng riêng.

## Phát hành đầu và sửa khả năng chấm dữ liệu thưa

Commit032b205 đã qua CI41308558218 và41309132726, Render Free
`dep-dbjjh1ou01pc73flqgbg` live/health200. Tuy nhiên lần thêm Neon đầu đã
rollback toàn bộ:0run release mới và mọi row cũ giữ fingerprint. Không ghi đó
là phát hành dữ liệu thành công. Receipt đọc riêng:
`D:/AlphaTech_Private/forecast_guard_20261101/publication_failure_readonly.json`.

Nguyên nhân là availability: chuỗi dịch vụ125kỳ có quan sát cuối ở phần dư11kỳ
của holdout25, trong khi core chỉ chấm block14đầy đủ đầu tiên nên không còn
quan sát nào. Sửa runtime căn holdout thành block14kết thúc đúng cuối lịch sử,
chỉ dựa N/phần trăm yêu cầu, không dùng giá trị hoặc sai số. Core/study5source
giữ nguyên. Lưu cả split yêu cầu/thực tế, không gắn nhãn gap-zero là quan sát.
N125/f=.2 thành28kỳ, initial69 nên chọn MA7 do không đủ điều kiện XGBoost.
Fixture hồi quy kiểm trường hợp1quan sát/R²không xác định; không được suy ra
số1đó là số liệu canonical Neon. Số quan sát và R² thực được đọc riêng từ run,
giữ cảnh báo ít mẫu và không chứng minh chất lượng tổng quát. Không suy ra score34,8268%của study
cho cấu hình holdout runtime này. Bản sửa phải qua hồi quy/CI/live mới trước
khi thử thêm dữ liệu lại. N56..62/f=.5 vẫn bị từ chối khi initial<7, không tự
bịa metric hoặc đổi dữ liệu để vượt điều kiện.

Bản sửa7fd0df9 đã được review không còn issue, focused39/39OK16,287s và full
local1513/1513OK551,611s,0failure/error/skip. Source788files giữ nguyên trong
run và TEST tựhủy; receipt `output/acceptance_verification/20261101T133437Z/`.
Năm source của core/study giữSHA đúng manifest cũ; không huấn luyện lại hoặc
đổi kết quả20case để khớp runtime. Các log RED và lượt lỗi test trung gian
được giữ riêng; không dùng localfull làm bằng chứng CI hoặc Neon thành công.

## Bằng chứng vận hành runtime14b089c

GitHub main và feature CI41313881279/41312958786 completed/success cùng
commit14b089c. RenderFree `dep-dbjkc2nb9u1s73e9on60` live đúng commit/health200.
Sau bản sửa đã thêm đúng4config/4run/56result/4SYSTEM_JOBaudit vào Neon;
mọi row có trước publication giữ fingerprint, không thêm bảng hoặc giao dịch
mô phỏng. Lần retry cùng release không thêm/sửa row. Bốn model snapshot đã
kiểm SHA/scope và suy luận trong process kiểm thử với thư mục model trống,
khớp14ngày/giá trị đã lưu. Đây không phải quan sát một API suy luận từ xa mới.

Browser production bằng phiên admin đã đọc cả3chỉ tiêu bán lẻ và1dịch vụ:
đúng modelMA7, đủ14điểm, cảnh báo lịch sử/ít mẫu/R²âm và không bịa feature
importance XGBoost. Số canonical thực nằm trong biên bản riêng; fixture1điểm
không được dùng thay số thực. UAT chỉ đổi workspace của phiên đã được cấp
quyền, không cấp thêm membership hoặc sửa dữ liệu nghiệp vụ.

Receipt riêng tại `D:/AlphaTech_Private/forecast_guard_20261101/` gồm
`after.json`, `snapshot_serving.json`, `idempotency.json`, `ui_readback.json`;
không công bố transaction/model native/các metric kinh doanh lên GitHub.
Source/model history cũ, sổ97 và CSV lịch sử bảo vệ giữ nguyên. Các commit
tài liệu sau runtime14b089c không được gọi là huấn luyện lại hoặc đổi dữ liệu.

## Kết luận có giới hạn

Đã xử lý mẫu lỗi đã biết bằng bộ chọn được duyệt và đạt20 case mô phỏng mới,
nhưng không thể bảo đảm thắng MA7 ở mọi dữ liệu tương lai. Khi nhiễu hoặc lịch
sử ngắn, chọn MA7 là kết quả hợp lệ, không được quảng cáo thành XGBoost. Chưa có
tăng trưởng doanh thu, hiệu quả kinh doanh hoặc chứng nhận production suy ra
từ các con số mô phỏng này.
