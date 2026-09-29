# Đối chiếu phạm vi nghiệp vụ — 15/09/2026

Tài liệu này đối chiếu file `1. Chốt phạm vi nghiệp vụ (Phân tíc.txt` với
repository tại commit `a92b31750210c5d68c12faef6989ba9a1673053c`. Nội dung trong
file đính kèm được xem là đề xuất/phạm vi, không phải bằng chứng production.

## Các điểm đã hiệu chỉnh

### Giao hàng tận nhà và tồn kho

`Order.branch` hiện cho phép để trống với `HOME_DELIVERY`, còn địa chỉ giao hàng
là văn bản. Vì vậy chưa thể trung thực tuyên bố hệ thống đã tự chọn “chi nhánh
gần nhất có đủ hàng” theo vị trí thật. Không được gọi geocoder trong transaction
checkout để suy diễn tọa độ hoặc làm chậm/không ổn định nghiệp vụ.

Phạm vi đúng nên triển khai theo hai bước:

1. Khi có chi nhánh fulfillment mặc định được cấu hình và có `StockBalance` cho
   toàn bộ dòng hàng, hệ thống có thể phân bổ có khóa hàng và lưu fulfillment
   branch vào đơn.
2. Chỉ bật chọn “gần nhất” khi có tọa độ giao hàng đã được người dùng xác nhận
   hoặc tọa độ tin cậy từ hồ sơ; nếu không có ứng viên đủ hàng thì trả lỗi rõ
   ràng hoặc dùng fallback đã cấu hình, không âm thầm chọn chi nhánh đầu tiên.

Thông tin mới đã chốt mã mặc định `BR-D1` và các mã fallback `BR-BT, BR-D7`.
Repository hiện đã có service strict allocation, khóa toàn bộ dòng tồn kho trước
khi trừ, hard-stop khi tổng mạng lưới không đủ và nhận tọa độ GPS tùy chọn từ
checkout. Tính năng vẫn được bật qua `HOME_DELIVERY_FULFILLMENT_POLICY=strict`;
giá trị mặc định là `legacy` để không làm hỏng các deployment chưa seed đủ
`StockBalance`. Nearest ordering chỉ được tuyên bố khi request có tọa độ hợp lệ;
không có tọa độ thì dùng thứ tự branch mặc định/fallback đã cấu hình.

### Forecasting

File phạm vi nêu `data/forecasting/retail_product_demand_timeseries.csv`, nhưng
đường dẫn này không tồn tại trong repository hiện tại. Nguồn huấn luyện thật
đang là chuỗi lịch sử theo workspace/DB và fixture kiểm thử. Vì thế chỉ được
gọi dữ liệu CSV là kế hoạch hoặc dữ liệu cần cung cấp, không gọi là provenance
đã xác minh.

Baseline hiện đã có lag-7; từ checkpoint này trainer cũng lưu riêng moving
average 7 ngày (`moving_average_7_*`). Hai baseline không thay thế cho đánh giá
backtest theo thời gian và không chứng minh XGBoost vượt trội.

### Knowledge/RAG và SOP

24 SOP trong `data/knowledge/` tồn tại dưới dạng file, nhưng việc file tồn tại
không tự chứng minh chúng đã được ingest vào đúng workspace, đã được embedding,
hay mọi câu trả lời chính sách đều được kiểm chứng. Các câu hỏi mẫu trong file
phạm vi nên được dùng làm benchmark có expected source/answer sau khi ingest và
review thủ công. Không dùng nhãn “zero hallucination”. Câu hỏi nhạy cảm phải
kiểm tra RBAC/ownership và khả năng từ chối, không chỉ khớp từ khóa.

### Expected answers cần sửa trước khi dùng làm gold set

Một số expected answer trong file phạm vi không khớp nguyên văn SOP hiện có, nên
không được đưa thẳng vào bộ chấm:

- RMA: SOP xác nhận DOA trong **72 giờ**, đổi Fullbox trong 30 phút; máy mượn
  chỉ áp dụng cho laptop từ 25 triệu/VIP khi dự kiến bảo hành **trên 07 ngày
  làm việc**, không phải “>48h”.
- Incident SLA: SOP xác nhận P1 phản hồi **≤15 phút** và MTTR **≤02 giờ**;
  không thấy cam kết on-site “30–45 phút” trong tài liệu này.
- Promo fraud: SOP nêu cùng địa chỉ/số điện thoại đặt >3 đơn trong 15 phút và
  cùng Device ID/IMEI/IP đặt >2 đơn trong 24 giờ; chưa có quy tắc đúng dạng
  “1 voucher/device/24h”.
- Trade-in: SOP dùng mức trợ giá cố định theo Grade (400.000/700.000/1.000.000
  VNĐ), không phải tỷ lệ 15–20%. “Zero Data Leak Guarantee” là quy trình chính
  sách, chưa phải bằng chứng hệ thống đã tự động xóa dữ liệu.
- Change Management, Asset Decommission, giờ làm việc và công tác phí có các
  con số tương ứng trong SOP; vẫn cần kiểm tra workspace ingestion và semantic
  answer trước khi gọi là RAG pass.

Gold set nên chứa expected facts đúng theo SOP, kèm source path và phiên bản;
không dùng câu chữ mạnh hơn tài liệu gốc.

### Báo cáo và bằng chứng production

Commit production được ghi trong file đính kèm không trùng với HEAD repository
hiện tại. Deploy log, CI, secret-redacted env và các URL trong file là bằng chứng
do người dùng cung cấp, chưa được agent độc lập xác minh. Chỉ các lệnh/test có
log trong repository mới được ghi là bằng chứng local; không suy rộng thành
production certification.

## Thứ tự thực hiện tiếp theo

1. Đối chiếu tồn kho production, bật `HOME_DELIVERY_FULFILLMENT_POLICY=strict`
   trên staging trước, rồi mới bật production; xác nhận GPS/địa chỉ fallback.
2. Cung cấp dataset forecasting có provenance hoặc xác nhận dùng dữ liệu DB;
   sau đó chạy backtest theo thời gian và báo cáo cả lag-7 lẫn MA-7.
3. Ingest/review SOP theo workspace và chạy bộ RAG với đánh giá semantic,
   role-specific denial và source citation.
4. Xác minh production bằng commit/deploy/CI/inbox/restore evidence riêng; không
   gộp các bằng chứng mô phỏng với bằng chứng thật.

## Không thay đổi trong checkpoint này

Không đổi route, schema database, chính sách public API, dữ liệu production,
secret, migration hoặc các failure AI demonstration đã được ghi nhận. Các thay
đổi code chỉ bổ sung baseline MA-7 minh bạch và regression test tương ứng.
