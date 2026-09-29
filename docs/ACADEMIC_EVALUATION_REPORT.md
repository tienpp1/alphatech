# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM & KIỂM THỬ ĐỊNH LƯỢNG NỀN TẢNG AI BUSINESS PLATFORM

> **Đính chính ngày 14/09/2026 — bản ghi lịch sử, không dùng làm chứng nhận nghiệm thu.** Các bảng số liệu bên dưới được giữ để truy vết bản xuất ngày 08/09; chưa chạy lại thực nghiệm. Các kết luận tuyệt đối trong bản gốc đã bị rút lại như sau:
>
> - XGBoost: theo phần trăm đã lưu, order cải thiện MAE 39,1%, revenue kém baseline 38,5%, ticket kém 2,3%. Cả ba R² đều âm. Không thể kết luận mô hình vượt trội hoặc giải thích phần lớn phương sai. Số MAE bị làm tròn khiến không thể tính lại chính xác phần trăm từ bảng này; cần run gốc.
> - RAG: các tỷ lệ lịch sử dùng heuristic keyword; chưa phải độ đúng/đủ về ngữ nghĩa. Có nguồn bất kỳ chưa chứng minh retrieval đúng; chỉ số fallback trước đây chưa dùng đúng mẫu số precision. Các khẳng định không rò rỉ, luôn trích dẫn, không hallucination chưa được các tỷ lệ này chứng minh.
> - GIS: hai khoảng cách tham chiếu chưa có nguồn độc lập. Không suy ra độ chính xác thực địa hoặc truy vấn PostGIS đúng 100% từ phép tính Haversine này.
> - Phê duyệt/audit: 4 recommendation, 3 approval pending và 0 approved chỉ là số đếm. Tỷ lệ tuân thủ/audit 100% được gán sẵn trong script cũ, không phải kết quả đo; rút lại đánh giá “Xuất sắc”.
> - Các nhãn “Hoàn thành 100%” ở mục 5 là kết luận cũ chưa đủ bằng chứng, không còn hiệu lực. Chia train/test theo thời gian cũng không tự chứng minh đã loại bỏ mọi leakage.
>
> Lệnh xuất mới yêu cầu `--workspace`, giữ từng run và ghi “Chưa đo” khi thiếu bằng chứng. Xem `docs/ACADEMIC_EVIDENCE_WORKFLOW.md`. Phần bên dưới chỉ lưu nội dung lịch sử, không phải đánh giá hiện hành.

**Đề tài**: Xây dựng Nền tảng Quản lý Vận hành Doanh nghiệp Thông minh tích hợp AI và GIS hỗ trợ Phân tích, Dự báo và Ra quyết định  
**Sinh viên thực hiện**: Hà Minh Tiến — **MSSV**: 1250080194 — **Lớp**: 12_ĐH_CNPM3  
**Khoa**: Công nghệ Thông tin — **Trường**: Đại học Tài nguyên và Môi trường TP.HCM  
**Giảng viên hướng dẫn**: ThS. Nguyễn Duy Tuấn  
**Thời điểm xuất báo cáo**: 08/09/2026 02:35:26  

---

## TỔNG QUAN KẾT QUẢ THỰC NGHIỆM

Báo cáo này tổng hợp kết quả đánh giá thực nghiệm định lượng trên môi trường thực tế của nền tảng, bám sát các tiêu chí đã cam kết trong **Mục 2.8 và Mục 3.5 của Đề cương Đồ án Chuyên ngành**, bao gồm:
1. **Dự báo Hồi quy XGBoost**: Đánh giá qua sai số $MAE$, $RMSE$, $MAPE$, hệ số xác định $R^2$ và đối chiếu với mô hình cơ sở (*Naive Seasonal Persistence Baseline*).
2. **Khung Hỏi đáp RAG & Trợ lý AI**: Đánh giá tỷ lệ trích xuất đúng ngữ cảnh (*Retrieval Hit Rate*), độ bám sát sự thật (*Grounded Faithfulness*) và khả năng nhận diện câu hỏi ngoài phạm vi (*Out-of-domain Fallback*).
3. **Phân tích Không gian GIS**: Kiểm chứng độ chính xác của thuật toán tính khoảng cách lượng giác trắc địa mặt cầu Haversine và truy vấn bán kính phục vụ.
4. **Động cơ Khuyến nghị & Quy trình Phê duyệt**: Kiểm tra luồng kiểm soát con người (*Human-in-the-loop Approval*) và các trường hợp audit đã được đo; không suy rộng thành tỷ lệ tuân thủ 100%.

---

## 1. ĐÁNH GIÁ MÔ HÌNH DỰ BÁO HỒI QUY XGBOOST (FORECASTING)

### 1.1. Phương pháp luận & Thiết lập Thực nghiệm
- **Thuật toán**: XGBoost Regressor kết hợp bộ đặc trưng chuỗi thời gian (*Time-Series Feature Engineering*): độ trễ lịch sử (*Lag 1, 7, 14 ngày*), trung bình trượt (*Rolling Mean 7, 14 ngày*), và đặc trưng lịch biểu (*Day of Week, Month, Weekend*).
- **Phân chia Dữ liệu**: Phân chia theo thứ tự thời gian tuyến tính (*Time-based Split 80/20*), không phân chia ngẫu nhiên (*No Random Shuffle*). Cách này giảm nguy cơ leakage do trộn tương lai vào quá khứ, nhưng không tự chứng minh đã loại bỏ mọi nguồn leakage.
- **Mô hình Cơ sở đối chứng (Naive Baseline)**: Sử dụng phương pháp lưu giữ giá trị chu kỳ tuần trước ($y_{t-7}$), phản ánh đúng quy luật tuần hoàn kinh doanh thực tế.
- **Công thức Sai số**:
  $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|, \quad \text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$

### 1.2. Bảng Số liệu Đánh giá Thực nghiệm

| Bài toán Dự báo | Workspace | Mẫu Train / Test | XGBoost MAE | XGBoost RMSE | MAPE (%) | $R^2$ | Naive Baseline MAE | Cải thiện MAE (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Retail Order Volume | ABC Tech Store | 61 / 15 | 1 | 1 | 46.8% | -0.211 | 1 | **+39.1%** |
| Retail Revenue | ABC Tech Store | 61 / 15 | 38,384,684 | 42,706,228 | 1967.3% | -3.374 | 27,712,533 | **-38.5%** |
| Service Ticket Volume | XYZ IT Technical Services | 64 / 15 | 1 | 2 | 52.4% | -0.685 | 1 | **-2.3%** |

> **Nhận xét học thuật đã hiệu chỉnh**:
> - Kết quả không đồng nhất: order volume có cải thiện MAE theo phần trăm đã lưu, trong khi revenue và ticket volume kém baseline.
> - Cả ba R² trong bản xuất lịch sử đều âm; vì vậy không thể kết luận XGBoost vượt trội hoặc giải thích phần lớn phương sai. Cần chạy lại trên run được chọn trước khi dùng cho quyết định vận hành.

---

## 2. ĐÁNH GIÁ KHUNG HỎI ĐÁP RAG & TRỢ LÝ AI (KNOWLEDGE BASE)

### 2.1. Thiết lập Thực nghiệm
- **Tài liệu nạp mẫu**: 4 Quy chế Bán hàng & Bảo hành (Retail) và 5 Quy trình Vận hành Tiêu chuẩn SOP & Cam kết SLA (Service).
- **Công nghệ**: Phân đoạn văn bản (*Recursive Chunking 500 ký tự, overlap 50 ký tự*), vector hóa nội dung (*Embedding API*) và lập chỉ mục không gian vector với `pgvector` trên PostgreSQL.
- **Bộ câu hỏi kiểm thử**: 16 câu hỏi trắc nghiệm chia làm 4 nhóm:
  1. *Document-only*: Câu hỏi thuần túy tra cứu điều khoản quy định nội bộ.
  2. *Structured-only*: Câu hỏi truy vấn số liệu kinh doanh qua Tool Calling.
  3. *Hybrid*: Câu hỏi kết hợp tài liệu và dữ liệu nghiệp vụ thời gian thực.
  4. *Out-of-domain*: Câu hỏi không có trong tri thức công ty nhằm kiểm tra cơ chế từ chối có kiểm soát (*Controlled Fallback*), không gọi đây là bằng chứng “zero hallucination”.

### 2.2. Kết quả Đánh giá Định lượng

| Không gian Tri thức | Số lượng Câu hỏi Test | Tỷ lệ Tìm kiếm Đúng Ngữ cảnh (Retrieval Hit Rate) | Độ đúng có Căn cứ Tài liệu (Grounded Accuracy) | Tỷ lệ Từ chối Ngoài phạm vi (Fallback Precision) |
| :--- | :---: | :---: | :---: | :---: |
| **Bán lẻ ABC Tech Store** | 10 câu | **100.0%** | **90.0%** | **100.0%** |
| **Dịch vụ Kỹ thuật XYZ IT** | 9 câu | **100.0%** | **77.8%** | **100.0%** |

> **Nhận xét học thuật đã hiệu chỉnh**:
> - Các tỷ lệ trong bảng là kết quả heuristic của bản xuất lịch sử, không phải độ đúng ngữ nghĩa hay độ đủ của câu trả lời.
> - Một số test hiện kiểm tra nguồn, quyền và fallback; chúng không chứng minh mọi câu trả lời đều có citation đúng hoặc không rò rỉ trong mọi tình huống.
> - Fallback được kiểm tra trên các ca ngoài phạm vi đã định; cần bộ đánh giá độc lập và semantic review trước khi kết luận chất lượng RAG tổng quát.

---

## 3. ĐÁNH GIÁ PHÂN TÍCH KHÔNG GIAN GIS & PHÉP TÍNH TRẮC ĐỊA

### 3.1. Thiết lập Thực nghiệm
- **Lớp dữ liệu không gian**: Tọa độ trắc địa chuẩn WGS84 (SRID 4326) được lưu trữ và lập chỉ mục không gian (*Spatial GiST Index*) trong CSDL PostGIS.
- **Thuật toán kiểm chứng**: Phép tính khoảng cách mặt cầu Haversine:
  $$d = 2R \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \text{lat}}{2}\right) + \cos(\text{lat}_1)\cos(\text{lat}_2)\sin^2\left(\frac{\Delta \text{lon}}{2}\right)}\right)$$
  với bán kính Trái đất $R = 6,371$ km.

### 3.2. Bảng So sánh Khoảng cách Trắc địa Thực tế (Địa bàn TP.HCM)

| Cặp Tọa độ Kiểm thử | Tọa độ (Lat, Lon) | Khoảng cách Hệ thống tính | Khoảng cách Trắc địa Chuẩn | Độ lệch / Sai số (%) |
| :--- | :--- | :---: | :---: | :---: |
| Cho Ben Thanh (Q.1) → Landmark 81 (Binh Thanh) | (10.7725, 106.698) → (10.795, 106.7219) | 3.62 km | 3.65 km | 0.93% |
| Cho Ben Thanh (Q.1) → San bay Tan Son Nhat (Tan Binh) | (10.7725, 106.698) → (10.8185, 106.6588) | 6.67 km | 6.65 km | 0.31% |

> **Nhận xét học thuật đã hiệu chỉnh**:
> - Hai cặp tọa độ minh họa có sai số dưới 1% so với giá trị tham chiếu trong bảng; đây không phải đánh giá độc lập trên toàn miền địa lý.
> - Kiểm thử bán kính hiện có bao phủ các ca điểm trong/ngoài/đúng biên và workspace, nhưng không đủ để tuyên bố PostGIS đúng 100% hoặc chứng minh SLA thực địa.

---

## 4. ĐÁNH GIÁ ĐỘNG CƠ KHUYẾN NGHỊ & QUY TRÌNH PHÊ DUYỆT (DECISION SUPPORT)

### 4.1. Chỉ số Đánh giá Quy trình Human-in-the-loop

| Tiêu chí Đánh giá | Kết quả Ghi nhận | Đạt chuẩn Đề cương |
| :--- | :---: | :---: |
| **Tổng số Đề xuất Khuyến nghị đã sinh** | 4 đề xuất | Đạt |
| **Tổng số Yêu cầu Phê duyệt được khởi tạo** | 3 yêu cầu | Đạt |
| **Yêu cầu đã được Quản lý phê duyệt (Approved)** | 0 yêu cầu | Đạt |
| **Yêu cầu đang chờ xét duyệt (Pending)** | 3 yêu cầu | Đạt |
| **Tuân thủ Cơ chế Duyệt 2 cấp (Human-in-the-loop)** | **Đã kiểm tra trên các ca approval hiện có**; chưa có mẫu số toàn hệ thống | **Chưa kết luận tỷ lệ** |
| **Ghi vết Nhật ký Kiểm toán (Audit Log)** | **Đã kiểm tra trên các action/snapshot đã nêu**; chưa chứng minh đủ mọi actor, diff, IP và transaction | **Chưa kết luận tỷ lệ** |

> **Nhận xét học thuật**:
> - Các ca đã kiểm tra thể hiện nguyên lý thiết kế: AI tạo đề xuất, người có quyền khác duyệt, sau đó hệ thống mới thực thi.
> - Chuỗi `Dữ liệu → Đề xuất AI → Quản lý Duyệt → Hệ thống Thực thi → Nhật ký Audit` chưa phải bằng chứng bao phủ mọi tool, middleware và transaction boundary.

---

## 5. BẢNG TỔNG HỢP ĐỐI CHIẾU VỚI CAM KẾT TRONG ĐỀ CƯƠNG ĐỒ ÁN

| Mục tiêu theo Đề cương Đồ án | Trạng thái Nghiệm thu | Bằng chứng Thực nghiệm / Mã nguồn |
| :--- | :---: | :--- |
| **1. Hai Workspace Retail & Service** | **Đã triển khai; nghiệm thu giới hạn** | Workspace-scoped queries và RBAC đã có test theo phạm vi; chưa phải chứng nhận toàn hệ thống. |
| **2. Tích hợp & Ánh xạ Dữ liệu Chuẩn** | **Đã triển khai; cần nghiệm thu dữ liệu** | `apps/integration` & `apps/mapping`; cần test dữ liệu sai/trùng/khác workspace đầy đủ. |
| **3. Phân tích Không gian GIS PostGIS** | **Đã triển khai; đã đo một số ca** | `apps/gis` và Leaflet; live provider/device và độ chính xác thực địa vẫn là giới hạn. |
| **4. Trợ lý AI Hỏi đáp RAG** | **Đã triển khai; chất lượng còn giới hạn** | `apps/knowledge`; semantic correctness, contradiction và live provider provenance chưa đủ. |
| **5. Dự báo Doanh thu / Khối lượng XGBoost** | **Đã triển khai; kết quả không đồng nhất** | Pipeline, baseline và metric có; revenue/ticket từng kém baseline, recursive interval chưa calibrated. |
| **6. Đề xuất Khuyến nghị có Phê duyệt** | **Đã triển khai; action có giới hạn** | Approval/audit có test theo action; reorder/workload và audit completeness còn ngoài phạm vi. |
| **7. Đánh giá Định lượng Thực nghiệm** | **Đã có công cụ; chưa chứng nhận toàn bộ** | `evaluate_academic_metrics` giữ từng run và trạng thái “Chưa đo”; cần run reproducible và review độc lập. |

---
*Báo cáo được khởi tạo tự động bởi hệ thống kiểm định AI Business Platform.*
