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

## Kết luận có giới hạn

Đã xử lý mẫu lỗi đã biết bằng bộ chọn được duyệt và đạt20 case mô phỏng mới,
nhưng không thể bảo đảm thắng MA7 ở mọi dữ liệu tương lai. Khi nhiễu hoặc lịch
sử ngắn, chọn MA7 là kết quả hợp lệ, không được quảng cáo thành XGBoost. Chưa có
tăng trưởng doanh thu, hiệu quả kinh doanh hoặc chứng nhận production suy ra
từ các con số mô phỏng này.
