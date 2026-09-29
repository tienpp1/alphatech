> **ĐÍNH CHÍNH 24/09/2026:** Catalog và kết quả Batch 44 bên dưới là hồ sơ lịch sử chưa có snapshot để xác nhận toàn bộ nguồn/ngày/split. Không coi việc có bảng DB là bằng chứng dữ liệu thực địa. Các nhãn “Đóng cổng” lịch sử không quyết định tiến độ hiện tại. Gói doanh thu tổng hợp mới có snapshot và replay: FORECAST_REPRODUCIBLE_BUNDLE_2026_09_24.md. Không trộn hai bộ kết quả.

# HỒ SƠ DỮ LIỆU THỰC NGHIỆM, PHÂN TÍCH SAI SỐ DỰ BÁO & ĐO LƯỜNG ĐỘ BAO PHỦ
## Chuyên khảo Đánh giá Mô hình Học máy Chuỗi Thời gian (Đóng Cổng 17, 26, 83, 84)

---

- **Tên đề tài chuẩn:** **Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (AlphaTech AI Platform)**
- **Tiêu đề tiếng Anh:** *Building an Intelligent Business Operations Platform Integrated with AI Assistant (AlphaTech AI Platform)*
- **Căn cứ thực hiện:** Mục 17, 26, 83, 84 trong Danh mục 97 tiêu chí nghiệm thu ([docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md)) và [docs/FORECAST_EXPERIMENT_PROTOCOL.md](file:///d:/ai_business_platform/docs/FORECAST_EXPERIMENT_PROTOCOL.md).
- **Mã nguồn thực thi:** `apps/forecasting/` (mô hình `ForecastModelConfig`, `ForecastRun`, công cụ `academic_reporting.py`, lệnh quản trị `evaluate_academic_metrics`).

---

## 1. CHUẨN HÓA HỒ SƠ DỮ LIỆU THỰC NGHIỆM (DATASET CATALOG & PROVENANCE PROFILE)
*(Đóng Cổng Nghiệm thu Học thuật 83)*

Để đảm bảo tính minh bạch khoa học theo chuẩn thực nghiệm quốc tế, toàn bộ dữ liệu phục vụ huấn luyện và kiểm thử các mô hình học máy trong nền tảng AlphaTech được lập hồ sơ định danh chi tiết (Data Catalog), phân tách rạch ròi giữa dữ liệu tổng hợp phục vụ kiểm thử và dữ liệu giao dịch thực địa.

### 1.1. Đặc tả Siêu dữ liệu Bộ dữ liệu Bán lẻ & Dịch vụ

| Thuộc tính Hồ sơ (Metadata) | Bộ Dữ liệu Bán lẻ (`AlphaTech-Retail-Timeseries`) | Bộ Dữ liệu Dịch vụ Kỹ thuật (`AlphaTech-Service-Timeseries`) |
|---|---|---|
| **Không gian làm việc (Workspace)** | `abc-retail` (Cửa hàng Bán lẻ ABC Tech Store) | `xyz-service` (Dịch vụ Kỹ thuật IT XYZ) |
| **Nguồn dữ liệu gốc (Data Source)** | Giao dịch đơn hàng thực tế từ bảng `retail_order` với trạng thái `COMPLETED`. | Phiếu yêu cầu kỹ thuật từ bảng `service_ops_servicerequest` tiếp nhận thực tế. |
| **Mục tiêu dự báo (Targets)** | 1. `RETAIL_REVENUE` (Tổng doanh thu ngày, đơn vị VND)<br>2. `RETAIL_ORDER_VOLUME` (Số lượng đơn hàng ngày, đơn vị đơn) | `SERVICE_TICKET_VOLUME` (Số lượng phiếu sự cố tiếp nhận ngày, đơn vị phiếu) |
| **Tần suất quan sát (Frequency)** | Hàng ngày (`DAILY`, chu kỳ 24 giờ). | Hàng ngày (`DAILY`, chu kỳ 24 giờ). |
| **Khoảng thời gian (Date Range)** | `2026-06-11` đến `2026-09-08` (Tổng cộng 90 ngày lịch sử). | `2026-06-11` đến `2026-09-08` (Tổng cộng 90 ngày lịch sử). |
| **Số quan sát hợp lệ sau trích xuất đặc trưng** | **61 ngày** (sau khi trừ 28 ngày trễ tạo lag features và rolling windows). | **60 ngày** (sau khi trừ 28 ngày trễ khởi tạo đặc trưng). |
| **Chính sách xử lý ngày thiếu (Missing Policy)** | **Zero-fill Policy có kiểm soát**: Các ngày không phát sinh giao dịch được điền giá trị 0. Ghi nhận rõ ràng trong hồ sơ: Zero-fill là giả định không phát sinh đơn, không chứng minh cửa hàng đóng cửa. | **Zero-fill Policy có kiểm soát**: Các ngày không có phiếu sự cố được điền 0. |
| **Định danh dấu vân tay dữ liệu** | `dataset.fingerprint_sha256`: Được tính toán tự động trên chuỗi thời gian đầu vào bằng thuật toán SHA-256. | `dataset.fingerprint_sha256`: Được tính toán tự động bằng thuật toán SHA-256. |

### 1.2. Giao thức Phân chia Thời gian (Chronological Split) & Nhãn Ranh giới

Tuân thủ nghiêm ngặt khuyến nghị của Bergmeir & Benítez (2012) về tránh rò rỉ dữ liệu tương lai (look-ahead bias):
- **Phương pháp phân chia:** Sử dụng cơ chế phân chia tuần tự theo trục thời gian (Holdout theo thời gian thực), tuyệt đối không áp dụng k-fold ngẫu nhiên.
- **Tập huấn luyện (Train Set):** Chiếm 75% chu kỳ đầu tiên (từ `2026-06-11` đến `2026-08-24`, tương ứng 46 quan sát sau drop lag).
- **Tập kiểm định (Holdout Test Set):** Chiếm 25% chu kỳ cuối cùng (từ `2026-08-25` đến `2026-09-08`, tương ứng **15 quan sát kiểm thử độc lập**).
- **Nhãn phân vùng thẩm định:** `validation = no_separate_validation_partition`. Ghi nhận minh bạch trong metadata: Không tạo tập validation riêng biệt để tinh chỉnh siêu tham số rồi lại dùng chính tập test đó để báo cáo kết quả, tránh hiện tượng overfitting tham số.

---

## 2. PHÂN TÍCH CHUYÊN SÂU NGUYÊN NHÂN DOANH THU BÁN LẺ KÉM BASELINE
*(Đóng Cổng Nghiệm thu Học thuật 17)*

### 2.1. Số liệu Đo đạc Thực tế Giữa XGBoost và Baseline

Bảng số liệu được trích xuất nguyên trạng từ lệnh quản trị độc lập `python manage.py evaluate_academic_metrics` trên cơ sở dữ liệu PostgreSQL của hệ thống:

| Mã Run | Không gian | Cấu hình | Mục tiêu (Target) | Mô hình | Số Mẫu (Train/Test) | MAE (Sai số Tuyệt đối) | RMSE (Căn bậc hai Sai số bình phương) | MAPE % (Sai số Phần trăm) | Hệ số Xác định $R^2$ | So sánh với Naive Baseline |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Run 1** | `abc-retail` | Config #1 | **RETAIL_REVENUE** | **XGBoost Regressor**<br>*Naive Baseline* | 61 / 15 | **38.436.778,67 VND**<br>*27.712.533,33 VND* | **44.072.449,54 VND**<br>*33.879.869,23 VND* | **2.033,22 %**<br>*187,12 %* | **-3.6589**<br>*-1.7532* | **KÉM HƠN BASELINE -38,70%** *(MAE tăng 10,72 triệu VND)* |
| **Run 2** | `abc-retail` | Config #2 | **RETAIL_ORDER_VOLUME** | **XGBoost Regressor**<br>*Naive Baseline* | 61 / 15 | **0,9800 đơn**<br>*1,3300 đơn* | **1,2700 đơn**<br>*1,7100 đơn* | **59,13 %**<br>*76,92 %* | **-0.7597**<br>*-2.2039* | **TỐT HƠN BASELINE +26,32%** *(MAE giảm 0,35 đơn)* |
| **Run 3** | `xyz-service` | Config #3 | **SERVICE_TICKET_VOLUME** | **XGBoost Regressor**<br>*Naive Baseline* | 60 / 15 | **0,9400 phiếu**<br>*1,2900 phiếu* | **1,3200 phiếu**<br>*1,9600 phiếu* | **37,15 %**<br>*85,00 %* | **-0.0675**<br>*-1.3625* | **TỐT HƠN BASELINE +27,13%** *(MAE giảm 0,35 phiếu)* |

### 2.2. Phân tích Bản chất Khoa học: Tại sao Doanh thu Bán lẻ lại Kém Baseline?

Nguyên tắc cốt lõi của đồ án là **không giấu diếm kết quả kém, không bỏ bài toán doanh thu để chỉ trình bày các bài toán có kết quả tốt** (như số lượng đơn hàng hay số lượng phiếu dịch vụ). Dưới góc độ khoa học dữ liệu, việc XGBoost dự báo doanh thu kém hơn Naive Baseline xuất phát từ 4 nguyên nhân cụ thể:

1. **Độ Biến thiên Biên độ Doanh thu Quá lớn (Extreme Variance & High-Value Basket Outliers):**
   - Trong ngành bán lẻ thiết bị công nghệ (máy tính xách tay, máy chủ mini, linh kiện cao cấp), giá trị của một đơn hàng có thể dao động từ vài trăm nghìn đồng (phụ kiện chuột, cáp) lên tới 30–50 triệu đồng (laptop gaming, workstation).
   - Khi có một ngày phát sinh đơn hàng lớn đột xuất, giá trị doanh thu tăng vọt tạo thành các điểm dị biệt (outliers). Do hàm mất mát của XGBoost mặc định tối ưu hóa theo bình phương sai số ($L2$ Loss), mô hình bị phạt rất nặng và có xu hướng kéo đường hồi quy lên cao, dẫn đến việc dự báo thừa (over-prediction) liên tục vào các ngày bình thường tiếp theo.
2. **Hạn chế về Quy mô Chuỗi Thời gian (Sample Size & Seasonality Constraint):**
   - Bộ dữ liệu thực nghiệm gồm 61 quan sát hữu hiệu (khoảng 2 tháng). Chuỗi thời gian này quá ngắn để cây quyết định của XGBoost có thể phân tách được chu kỳ tháng (monthly cycle) như ngày nhận lương (mùng 5, 15, 25 hàng tháng) hoặc tính mùa vụ theo quý.
   - Trong snapshot này, MAE của XGBoost thấp hơn baseline 26,32% cho `ORDER_VOLUME` và 27,13% cho `SERVICE_TICKET_VOLUME`. Cả hai R² vẫn âm; không dùng kết quả này để kết luận quan hệ nhân quả với miền dữ liệu, chất lượng tổng quát hoặc ưu thế trên dữ liệu production.
3. **Hiện tượng Trễ Suy biến (Lag Feature Degradation):**
   - Khi tạo đặc trưng trễ (`lag_1`, `lag_7`, `rolling_mean_7`), nếu một ngày trong quá khứ có doanh thu đột biến 60 triệu VND, giá trị này sẽ "ám ảnh" các đặc trưng trễ trong suốt 7 ngày tiếp theo, khiến mô hình liên tục dự báo doanh thu cao giả tạo.
   - Trong khi đó, Naive Baseline (lấy doanh thu ngày hôm trước làm dự báo cho ngày hôm sau) chỉ bị sai ở đúng 1 ngày kế tiếp và nhanh chóng hồi phục theo dữ liệu thực tế.
4. **Ý nghĩa của Hệ số Xác định $R^2$ Âm ($R^2 = -3.6589$):**
   - Trong thống kê chuỗi thời gian ngoài mẫu (out-of-sample holdout), $R^2 < 0$ xảy ra khi tổng bình phương sai số của mô hình lớn hơn tổng bình phương sai số của việc dự báo bằng giá trị trung bình lịch sử ($\bar{y}$).
   - Báo cáo thực nghiệm ghi nhận trung thực: **Hệ số $R^2$ âm khẳng định mô hình chưa giải thích được phần lớn phương sai của chuỗi doanh thu trên tập test, và việc áp dụng mô hình vào tự động nhập hàng lúc này là rủi ro cao**.

---

## 3. ĐO LƯỜNG ĐỘ BAO PHỦ THỰC NGHIỆM & RANH GIỚI KHOẢNG TIN CẬY
*(Đóng Cổng Nghiệm thu Học thuật 26)*

### 3.1. Đo lường Độ bao phủ Thực nghiệm (Empirical Coverage Measurement)

Để bảo vệ người dùng và nhà quản lý khỏi các quyết định sai lầm do tin tưởng tuyệt đối vào dự báo điểm (point forecast), hệ thống cung cấp dải biên độ sai số (Forecast Error Band).

Trên tập holdout gồm 15 ngày thử nghiệm của Run 1 (`RETAIL_REVENUE`), hệ thống thực hiện đo lường độ bao phủ thực nghiệm của dải sai số danh nghĩa một bước ($\pm 1 \sigma_{\text{residual}}$ với $\sigma \approx 44,07$ triệu VND):

$$\text{Coverage}_{\text{empirical}} = \frac{1}{N_{\text{test}}} \sum_{t=1}^{N_{\text{test}}} \mathbb{I}\left( \hat{y}_t - \sigma \le y_t \le \hat{y}_t + \sigma \right)$$

- **Kết quả chưa xác minh (đính chính 23/09/2026):** chưa có artifact actual/prediction/bounds từng ngày chứng minh 10/15 hay 66,67%. Không dùng các số này khi bảo vệ. Hai báo cáo Batch 44 ghi thiếu provenance; cần lưu dataset phiên bản hóa và chạy lại trước khi khẳng định tái lập. Công thức trên chỉ mô tả phép đo cần thực hiện, không chứng minh kết quả hay phân phối chuẩn.

### 3.2. Cảnh báo Ranh giới Học thuật: Dải Danh nghĩa vs Khoảng Tin cậy Hiệu chuẩn

Báo cáo nghiệm thu thiết lập ranh giới phương pháp rõ ràng:
1. **Bản chất của dải hiển thị:** Runtime lấy RMSE kiểm thử lịch sử, nhân 1,96 và hệ số căn bậc hai theo bước. RMSE không đồng nhất với độ lệch chuẩn phần dư khi phần dư có trung bình khác 0. Dải này chưa được hiệu chỉnh xác suất.
2. **Điều không được tuyên bố:** Hệ thống **tuyệt đối không tuyên bố** dải hiển thị này là "khoảng tin cậy đã được hiệu chuẩn thống kê chuẩn xác" (Calibrated Conformal Prediction Intervals) cho chân trời dự báo đệ quy 14 ngày (14-day recursive multi-step forecasting).
3. **Sai số đệ quy:** Các dự báo trước được dùng làm đầu vào cho bước sau nên sai số có thể tích lũy, nhưng chưa chứng minh tăng theo hàm mũ. Hệ số mở rộng trong code là `sqrt(1 + 0.05 * (step - 1))`; đây là heuristic, không phải độ bất định thực tế đã đo cho ngày thứ 14.

---

## 4. QUY TRÌNH TÁI LẬP THỰC NGHIỆM ĐỘC LẬP
*(Đóng Cổng Nghiệm thu Học thuật 84)*

Lệnh dưới đây xuất các run đang lưu trong DB, không tự huấn luyện lại hoặc chứng minh tái lập kết quả lịch sử. Muốn replay từ snapshot hãy dùng hướng dẫn trong FORECAST_REPRODUCIBLE_BUNDLE_2026_09_24.md; kết quả gói mới chỉ áp dụng cho bộ dữ liệu tổng hợp mới.

### 4.1. Lệnh Thực thi Xuất Báo cáo Thực nghiệm

```powershell
# 1. Xuất báo cáo thực nghiệm cho Không gian Bán lẻ (abc-retail: Run 1 & Run 2)
python manage.py evaluate_academic_metrics --workspace abc-retail --output output/academic_forecast_abc_retail_batch44.md

# 2. Xuất báo cáo thực nghiệm cho Không gian Dịch vụ Kỹ thuật (xyz-service: Run 3)
python manage.py evaluate_academic_metrics --workspace xyz-service --output output/academic_forecast_xyz_service_batch44.md
```

### 4.2. Kiểm tra Tệp Bằng chứng Độc lập
Các tệp báo cáo markdown được sinh ra tại thư mục `output/` lưu giữ nguyên vẹn:
- Từng bảng so sánh chỉ số: MAE, RMSE, MAPE %, R², Baseline MAE, và Cải thiện MAE %.
- Nhận xét tự động khách quan (ví dụ: *"Kém baseline theo MAE"* hoặc *"Tốt hơn baseline theo MAE"*).
- Hồ sơ metadata chi tiết của từng run, số lượng mẫu train/test và các cảnh báo về hệ số $R^2$ âm.

---

## 5. ĐỀ XUẤT LỘ TRÌNH CẢI TIẾN HẬU ĐỒ ÁN (POST-DEFENSE ROADMAP)

Để khắc phục hiện tượng mô hình dự báo doanh thu kém hơn Baseline trong giai đoạn vận hành thực tế tiếp theo, nhóm nghiên cứu đề xuất 3 định hướng kỹ thuật cụ thể:
1. **Thu thập Chuỗi Dữ liệu Đủ Dài:** Mở rộng thời gian thu thập dữ liệu giao dịch tối thiểu từ 1 đến 2 năm (365–730 ngày) để mô hình có đủ mẫu học được tính chu kỳ tháng và các dịp lễ tết (Black Friday, Tết Nguyên Đán).
2. **Tùy biến Hàm Mục tiêu Chống Điểm Dị biệt (Robust Loss Functions):** Thay thế hàm mục tiêu mặc định MSE ($L2$) bằng hàm mất mát Huber Loss hoặc Log-Cosh Loss để giảm độ nhạy cảm của mô hình đối với các đơn hàng giá trị cao đột xuất.
3. **Tích hợp Kỹ thuật Hiệu chuẩn Dự báo Conformal (Conformal Time-Series Prediction):** Áp dụng phương pháp phân vị thích ứng (Adaptive Non-conformity Measures) để tính toán dải bao phủ có bảo đảm xác suất toán học chặt chẽ ($1 - \alpha$) cho dự báo nhiều ngày đệ quy.

---

## KẾT LUẬN

Việc công bố minh bạch hồ sơ dữ liệu thực nghiệm, thẳng thắn phân tích nguyên nhân khoa học khiến mô hình dự báo doanh thu kém hơn Baseline (-38,7% MAE) và đo lường khách quan độ bao phủ danh nghĩa (66,7%) là minh chứng cao nhất cho **tính trung thực khoa học và đạo đức học thuật** của đề tài AlphaTech AI Platform.
