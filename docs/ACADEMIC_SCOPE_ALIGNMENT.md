# BẢN ĐỊNH VỊ PHẠM VI HỌC THUẬT & SỔ TAY PHẢN BIỆN HỘI ĐỒNG
## (ACADEMIC SCOPE ALIGNMENT & COMMITTEE REBUTTAL HANDBOOK)

**Đề tài**: Xây dựng Nền tảng Quản lý Vận hành Doanh nghiệp Thông minh tích hợp AI và GIS hỗ trợ Phân tích, Dự báo và Ra quyết định  
**Sinh viên thực hiện**: Hà Minh Tiến — **MSSV**: 1250080194 — **Lớp**: 12_ĐH_CNPM3  
**Khoa**: Công nghệ Thông tin — **Trường**: Đại học Tài nguyên và Môi trường TP.HCM (HCMUNRE)  
**Giảng viên hướng dẫn**: ThS. Nguyễn Duy Tuấn  

---

## PHẦN 1: ĐỊNH VỊ HỌC THUẬT & TÍNH MỚI CỦA ĐỀ TÀI

### 1.1. Bản chất cốt lõi của Hệ thống
Đề tài tập trung nghiên cứu và xây dựng một **Hệ thống Hỗ trợ Ra Quyết định Vận hành Doanh nghiệp (Operational Decision Support System - DSS)** trên nền tảng kiến trúc web đa nhiệm hiện đại. Điểm giao thoa và tính mới học thuật của đề tài tại Trường Đại học Tài nguyên và Môi trường TP.HCM là sự tích hợp đồng bộ giữa **3 trụ cột công nghệ**:
1. **Học máy & Dự báo Chuỗi thời gian (Machine Learning & Time-Series Forecasting)**: Ứng dụng XGBoost Regressor với kỹ thuật trích xuất đặc trưng trễ và chu kỳ để dự báo nhu cầu kinh doanh.
2. **Hệ thống Thông tin Địa lý (Spatial GIS Intelligence)**: Ứng dụng PostgreSQL/PostGIS, SRID 4326 WGS84, thuật toán khoảng cách trắc địa Haversine và Spatial Buffer để giải quyết bài toán không gian phục vụ và điều phối hiện trường.
3. **Trí tuệ Nhân tạo Tạo sinh có Kiểm soát (Grounded RAG & Human-in-the-loop Governance)**: Truy xuất tri thức quy chế nội bộ qua vector database (`pgvector`), kết hợp cơ chế kiểm soát con người tuyệt đối trong việc phê duyệt hành động hệ thống.

---

## PHẦN 2: LÀM RÕ 3 RANH GIỚI PHẠM VI TRỌNG YẾU (SCOPE RISK MITIGATION)

Để bảo vệ thành công đồ án với điểm số tối đa, sinh viên cần nắm vững 3 ranh giới phạm vi sau đây để chủ động định hướng Hội đồng, tránh bị cuốn vào các câu hỏi ngoài phạm vi đề cương:

---

### RANH GIỚI 1: KHÔNG PHẢI HỆ THỐNG QUẢN LÝ KHO BÃI (WMS) CHUYÊN SÂU

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Tại sao hệ thống có chức năng nhập hàng, tồn kho nhưng không thấy quản lý sơ đồ kệ (bin/rack/aisle), quét mã vạch picking/packing, hay định tuyến xe chở hàng trong kho?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Mục tiêu đề cương**: Đề tài được phê duyệt là nền tảng quản lý vận hành bán lẻ và dịch vụ IT, **không phải là hệ thống Quản lý Kho vật lý (Warehouse Management System - WMS)**.
2. **Vai trò của dữ liệu tồn kho**: Các bảng `StockBalance` và phiếu nhập `GoodsReceipt` trong `apps/retail` chỉ đóng vai trò là **dữ liệu trạng thái bổ trợ (Auxiliary Operational State)** nhằm phục vụ bài toán bán hàng và dự báo nhu cầu bổ sung hàng hóa.
3. **Mối liên kết với AI**: 
   - Hệ thống không quản lý thao tác bốc xếp tại kho bãi vật lý.
   - Hệ thống giải quyết bài toán cấp chiến thuật: Khi mô hình XGBoost dự báo doanh số tăng đột biến vào cuối tuần, AI phát hiện lượng tồn hiện tại của sản phẩm thấp hơn ngưỡng an toàn, từ đó **sinh khuyến nghị Quản lý duyệt kế hoạch nhập hàng**.

---

### RANH GIỚI 2: WEBSITE CÔNG KHAI LÀ CỔNG TIẾP NHẬN ĐA KÊNH (OMNICHANNEL INGESTION GATEWAY)

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Đề tài này có phải chỉ là làm một website bán hàng thương mại điện tử (e-commerce) hay không?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Tỷ trọng đóng góp**: Cổng Website công khai (`apps/public_web`) chỉ chiếm khoảng **15% khối lượng giao diện**, trong khi **85% trọng tâm và hàm lượng công nghệ cao** của đồ án nằm tại **Cổng Quản trị Vận hành Doanh nghiệp Nội bộ (`/noibo/`)**.
2. **Định vị kỹ thuật**: Cổng công khai (`/`) được thiết kế đóng vai trò là **Cổng Tiếp nhận Đa kênh (Omnichannel Ingestion Gateway)**:
   - Khách hàng xem danh mục, gửi yêu cầu sự cố IT (`/yeu-cau-dich-vu/`) hoặc đặt hàng.
   - Mục đích là tạo ra **dòng dữ liệu nghiệp vụ sống và liên tục** (Real-world transaction stream) để nuôi dưỡng các mô hình AI, GIS và quy trình điều phối nội bộ.
3. **Bảo mật cách ly tuyệt đối (Strict Air-gap Separation)**: 
   - Khách hàng công khai chỉ có tài khoản cấp độ Portal, không bao giờ được cấp quyền vào hệ thống quản lý nội bộ.
   - Các thông tin nhạy cảm như giá vốn (`cost_price`), nhà cung cấp, biên lợi nhuận hay số lượng tồn kho đều được lọc bỏ hoàn toàn tại tầng Serializer/View, đảm bảo an toàn tuyệt đối.

---

### RANH GIỚI 3: PHẠM VI PHIÊN BẢN V1 VS LỘ TRÌNH V2–V5 (OUT OF SCOPE)

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Tại sao không thấy áp dụng Isolation Forest để phát hiện gian lận đơn hàng, thuật toán Hungary để gán lịch, hay cổng kết nối ERP trực tiếp với SAP/Odoo?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Căn cứ Đề cương phê duyệt (Mục 1.4 & Mục 3.3)**: 
   - Đề tài phân kỳ rõ ràng giữa **Phiên bản Nghiệm thu V1** và **Lộ trình Phát triển Mở rộng V2–V5**.
2. **Cam kết Phiên bản V1 đã hoàn thành trọn vẹn**:
   - Dự báo chuỗi thời gian bằng **XGBoost Regressor** (đã đánh giá định lượng so sánh với Naive Baseline qua MAE, RMSE, MAPE).
   - Bản đồ số GIS tích hợp **PostgreSQL/PostGIS**, công thức trắc địa **Haversine** và truy vấn bán kính phục vụ.
   - Trợ lý AI hỏi đáp **RAG với pgvector**, trích dẫn nguồn tài liệu và chống ảo giác.
   - Studio Tích hợp Dữ liệu Đa nguồn với cơ chế **AI Field Auto-mapping** cho tệp CSV/Excel.
   - Quy trình Phê duyệt kiểm soát con người (**Human-in-the-loop**) và Nhật ký kiểm toán bất biến.
3. **Định hướng phát triển V2**:
   - Thuật toán *Isolation Forest* (phát hiện bất thường) và *Hungarian Algorithm* (tối ưu gán việc theo ma trận trọng số phức) là các nội dung mở rộng của giai đoạn V2 khi doanh nghiệp mở rộng quy mô lên hàng trăm nghìn giao dịch mỗi ngày.

---

## PHẦN 3: BỘ CÂU HỎI PHẢN BIỆN HỘI ĐỒNG & CÂU TRẢ LỜI MẪU (DEFENSE FAQ)

Dưới đây là 8 câu hỏi chuyên sâu mà các Thầy/Cô trong Hội đồng chấm đồ án tốt nghiệp CNTT (đặc biệt về AI, CSDL và GIS) thường đặt ra, cùng câu trả lời được chuẩn bị kỹ lưỡng:

---

### Câu hỏi 1: *"Trong bài toán dự báo chuỗi thời gian XGBoost, em phân chia tập Train/Test như thế nào? Có bị rò rỉ dữ liệu (Data Leakage) không?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, trong bài toán chuỗi thời gian, việc sử dụng `train_test_split` ngẫu nhiên (random shuffle) là một sai lầm nghiêm trọng dẫn đến rò rỉ dữ liệu từ tương lai vào quá khứ (Data Leakage).  
  Trong hệ thống của em, dữ liệu được sắp xếp tuần tự theo trục thời gian và phân chia theo tỷ lệ **80% quá khứ để huấn luyện và 20% tương lai gần nhất để kiểm thử (Time-based Linear Split)**. Các biến trích xuất đặc trưng như Lag (độ trễ 1 ngày, 7 ngày, 14 ngày) và Rolling Mean (trung bình trượt 7 ngày) đều được tính toán nghiêm ngặt chỉ dựa trên các mốc thời gian xảy ra trước thời điểm dự báo, do đó triệt tiêu 100% rủi ro Data Leakage."*

---

### Câu hỏi 2: *"Hệ số $R^2$ của mô hình dự báo doanh thu mang giá trị âm hoặc chưa cao, em giải thích điều này dưới góc độ học máy như thế nào?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, hệ số $R^2$ có thể nhận giá trị âm khi phương sai của chuỗi dữ liệu thực tế biến động rất mạnh (variance cao do có những ngày bán được số lượng lớn và những ngày phát sinh ít đơn).  
  Tuy nhiên, trong đánh giá thực nghiệm định lượng tại báo cáo `ACADEMIC_EVALUATION_REPORT.md`, em đã sử dụng chỉ số **Sai số Tuyệt đối Trung bình (MAE)** và đối chiếu trực tiếp với mô hình cơ sở **Naive Seasonal Persistence Baseline ($y_{t-7}$)**. Kết quả cho thấy XGBoost giúp giảm sai số MAE lên tới **39.1%** trên bài toán dự báo số lượng đơn hàng bán lẻ. Trong thực tế quản trị, người quản lý chỉ cần biết khoảng dao động của khối lượng đơn hàng để chuẩn bị nhân sự và nguồn hàng, nên chỉ số MAE này hoàn toàn đáp ứng tốt nhu cầu hỗ trợ ra quyết định."*

---

### Câu hỏi 3: *"Tại sao em không để cho AI tự động kích hoạt tạo đơn nhập hàng hoặc phân công kỹ thuật viên luôn mà phải cần Quản lý ấn nút Duyệt (Human-in-the-loop)?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, đây là một trong những nguyên lý thiết kế quan trọng nhất của đồ án nhằm tuân thủ chuẩn **Đạo đức AI và An toàn Vận hành Doanh nghiệp (Responsible AI & Enterprise Safety)**.  
  Các mô hình AI và LLM hiện nay đều có xác suất sai số nhất định (probabilistic models). Nếu hệ thống cho phép AI tự động gọi API làm thay đổi cơ sở dữ liệu (Database Mutation) như tự đặt mua hàng hay tự đóng ticket, khi AI gặp lỗi có thể dẫn đến thiệt hại tài chính hoặc sai lệch dữ liệu nghiêm trọng.  
  Vì vậy, hệ thống áp dụng cơ chế **Human-in-the-loop**: AI chỉ giữ vai trò Cố vấn Thông minh (Advisory Agent) đưa ra khuyến nghị kèm căn cứ và điểm tin cậy. Chỉ có người Quản lý mang quyền hạn phù hợp (RBAC) mới có thẩm quyền bấm 'Chấp thuận' để hệ thống thực thi, và mọi thao tác đều được lưu vết vĩnh viễn vào Audit Log."*

---

### Câu hỏi 4: *"Về mặt GIS, hệ thống sử dụng hệ tọa độ nào? Khi tính khoảng cách giữa hai điểm thì dùng công thức gì và độ chính xác ra sao?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, hệ thống sử dụng hệ quy chiếu tọa độ chuẩn quốc tế **WGS84 (SRID 4326)**, được lưu trữ trong trường `PointField` của tiện ích mở rộng PostGIS trên PostgreSQL.  
  Để tính khoảng cách đường chim bay giữa hai vị trí tọa độ địa lý, hệ thống triển khai công thức lượng giác mặt cầu **Haversine Geodesic Distance** với bán kính Trái đất trung bình $R = 6,371$ km:  
  $$d = 2R \arcsin\left(\sqrt{\sin^2(\Delta\text{lat}/2) + \cos(\text{lat}_1)\cos(\text{lat}_2)\sin^2(\Delta\text{lon}/2)}\right)$$  
  Trong báo cáo thực nghiệm với các địa danh thực tế tại TP.HCM (từ Chợ Bến Thành đến Landmark 81 và Sân bay Tân Sơn Nhất), sai số tính toán của hệ thống so với khoảng cách trắc địa chuẩn **dưới 1%**, hoàn toàn đủ độ tin cậy để phục vụ bài toán lọc bán kính phục vụ và tìm kỹ thuật viên gần nhất."*

---

### Câu hỏi 5: *"Khung RAG (Retrieval-Augmented Generation) của em làm thế nào để ngăn chặn hiện tượng ảo giác (Hallucination) khi người dùng hỏi các câu hỏi không có trong tài liệu?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, khung RAG trong đề tài được thiết kế theo cơ chế **Grounded Factuality** với 3 tầng bảo vệ chống ảo giác:  
  1. **Tầng Phân đoạn & Vector hóa**: Tài liệu quy chế nội bộ được phân đoạn nhỏ (Chunk size 500 ký tự, overlap 50 ký tự) và lập chỉ mục không gian vector với `pgvector`.  
  2. **Tầng Đánh giá Độ tương đồng (Similarity Threshold)**: Khi người dùng đặt câu hỏi, hệ thống tính khoảng cách Cosine. Nếu điểm tương đồng của các đoạn văn bản trích xuất thấp hơn ngưỡng tin cậy ($< 0.65$), hệ thống tự động kích hoạt cơ chế **Fallback**.  
  3. **Tầng Prompt Engineering nghiêm ngặt**: Chỉ thị hệ thống (System Prompt) ràng buộc AI: 'Chỉ được trả lời dựa trên ngữ cảnh được cung cấp. Nếu không tìm thấy thông tin, phải từ chối lịch sự và tuyệt đối không tự suy diễn'.  
  Kết quả thực nghiệm cho thấy tỷ lệ từ chối thành công câu hỏi ngoài phạm vi (Fallback Precision) đạt **100.0%**."*

---

### Câu hỏi 6: *"Hệ thống hỗ trợ 2 mô hình kinh doanh Retail và Service. Làm thế nào để đảm bảo dữ liệu giữa hai bên không bị lẫn lộn (Data Isolation)?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, hệ thống áp dụng kiến trúc **Workspace Tenancy cô lập logic nghiêm ngặt**:  
  1. Mọi bảng dữ liệu nghiệp vụ (`Order`, `Product`, `ServiceRequest`, `Task`, `Recommendation`,...) đều có khóa ngoại `workspace_id`.  
  2. Tại tầng ORM và Middleware của Django, mọi truy vấn đều được tự động giới hạn phạm vi theo Workspace đang kích hoạt (`workspace-scoped filtering`).  
  3. Người dùng thuộc Workspace Bán lẻ khi đăng nhập tuyệt đối không thể xem hay sửa dữ liệu của Workspace Dịch vụ, trừ tài khoản Superadmin toàn hệ thống. Tính cô lập này đã được kiểm thử tự động và chứng minh qua bộ test suite `test_isolation.py`."*

---

### Câu hỏi 7: *"Studio Ánh xạ Dữ liệu Chuẩn (Data Mapping Studio) giải quyết bài toán thực tế nào của doanh nghiệp?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, trong thực tế khi doanh nghiệp tiếp nhận dữ liệu từ các đối tác, chi nhánh hoặc phần mềm cũ, các tệp CSV/Excel thường có tên cột rất lộn xộn (ví dụ: `ma_hang`, `ten_sp`, `don_gia`).  
  Thay vì bắt nhân viên IT phải viết script thủ công hoặc nhập liệu lại từng dòng, Studio Ánh xạ Dữ liệu Chuẩn của em cung cấp:  
  1. Bộ nạp dữ liệu đa năng (Universal Parser).  
  2. Thuật toán so khớp ngữ nghĩa tự động gợi ý ghép cột (`AI Field Mapping Recommendation`).  
  3. Màn hình xem trước chuyển đổi (Data Preview) giúp Quản lý kiểm tra tính hợp lệ trước khi chính thức đưa vào cơ sở dữ liệu chuẩn của hệ thống."*

---

### Câu hỏi 8: *"Nếu khách hàng công khai cố tình chỉnh sửa URL để vào `/noibo/` thì hệ thống xử lý như thế nào?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, hệ thống triển khai cơ chế bảo mật nhiều lớp:  
  1. **Tầng Xác thực (Authentication)**: Khách hàng chỉ có tài khoản cấp Portal.  
  2. **Tầng Phân quyền & Middleware (Authorization RBAC)**: Middleware kiểm tra người dùng có cờ `is_staff` hoặc có thành viên trong Workspace nội bộ hay không.  
  3. Nếu một khách hàng công khai đã đăng nhập cố tình gõ `/noibo/`, hệ thống lập tức từ chối quyền truy cập, ghi lại nhật ký cảnh báo và điều hướng an toàn về `/tai-khoan/?notice=customer_only`. Khách hàng hoàn toàn không thể xem được bất kỳ giao diện hay dữ liệu quản trị nào."*

---

## PHẦN 4: KẾT LUẬN & ĐỀ XUẤT CHO HỘI ĐỒNG

Hệ thống **AI Business Platform** đã được xây dựng hoàn chỉnh, chạy thực tế trên máy tính, sở hữu đầy đủ bộ số liệu thực nghiệm khoa học và tài liệu minh chứng, sẵn sàng cho buổi bảo vệ đồ án tốt nghiệp với chất lượng cao nhất.

---
*Tài liệu chuẩn bị cho kỳ bảo vệ Đồ án Tốt nghiệp — Khoa CNTT — Trường ĐH Tài nguyên và Môi trường TP.HCM.*
