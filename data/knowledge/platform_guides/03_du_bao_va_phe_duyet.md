# Hướng dẫn nội bộ: dự báo và phê duyệt

Phạm vi: hướng dẫn nền tảng, bản 09/10/2026. Nguồn: docs/PROJECT_CONTEXT.md, apps/forecasting và apps/approvals. Không phải lệnh thực thi hoặc tham số của một hành động thật.

## Dự báo có phải doanh thu chắc chắn không?

Dự báo là ước lượng từ dữ liệu và cấu hình model, không phải doanh thu đã ghi nhận. Xem target, granularity, horizon, SKU/category/branch, khoảng thời gian dữ liệu và trạng thái run. Không so một dự báo tuần với doanh thu ngày mà không quy đổi đúng. Khi thiếu RMSE hợp lệ, không tự tạo khoảng tin cậy. Mô phỏng what-if phụ thuộc giả định, không phải tác động nhân quả đã được đo.

## Khi XGBoost kém baseline thì kết luận thế nào?

Trình bày metric theo đúng tập dữ liệu và backtest theo thời gian. Nếu sai số lớn hơn baseline, không mô tả mô hình vượt trội. Đối chiếu kích thước mẫu, seasonality, dữ liệu thiếu, leakage và cách chia train/test. Không sửa nhận xét để che số liệu. Muốn chứng minh cải thiện cần lần chạy mới và bằng chứng tương ứng.

## Forecast đang chờ hoặc server restart thì làm gì?

Kiểm tra trạng thái run và tiến trình worker của môi trường đó. Worker local không chứng minh có worker production. Phạm vi Render Free hiện chưa chạy worker async production riêng. Không báo dự báo đã hoàn tất nếu run chưa có kết quả. Không tự spawn daemon thread hoặc đánh dấu SUCCESS để thoát trạng thái chờ.

## AI có được tự đổi giá hoặc duyệt hành động không?

AI không tự thay đổi dữ liệu chỉ vì người dùng yêu cầu trong chat. Những hành động được hỗ trợ cần action contract, quyền, validation, yêu cầu phê duyệt và cơ chế thực thi được kiểm soát. PENDING chỉ là chờ phê duyệt, không phải đã thi hành. Người đề xuất và người quyết định phải tuân thủ separation of duties của hệ thống. Kiểm tra kết quả thực thi, không suy luận từ thông báo tạo đề xuất.

## Có thể tự nhập hàng hoặc cân bằng nhân lực không?

Không coi recommendation stock reorder hay workload balancing là giao dịch đã thực hiện. Các ánh xạ chưa đủ domain transaction/rollback vẫn advisory trong phạm vi đã chốt. Không tự bịa tham số thiếu, kho đích, nhân sự hoặc giá. Trước khi mở rộng cần định nghĩa contract và kiểm thử quyền, tính hợp lệ, idempotency, cạnh tranh và rollback.
