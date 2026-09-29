# BẢN ĐỊNH VỊ PHẠM VI HỌC THUẬT & SỔ TAY PHẢN BIỆN HỘI ĐỒNG
## (ACADEMIC SCOPE ALIGNMENT & COMMITTEE REBUTTAL HANDBOOK)

Đọc cùng `ACADEMIC_ACCEPTANCE_SCOPE.md` và `ACADEMIC_REQUIREMENTS_MATRIX.md`.
Các phần dưới là hướng dẫn trình bày, không phải chứng nhận đã hoàn thành bản nộp.

**Đề tài**: Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI
**Sinh viên thực hiện**: Hà Minh Tiến — **MSSV**: 1250080194 — **Lớp**: 12_ĐH_CNPM3  
**Khoa**: Công nghệ Thông tin — **Trường**: Đại học Tài nguyên và Môi trường TP.HCM (HCMUNRE)  
**Giảng viên hướng dẫn**: ThS. Nguyễn Duy Tuấn  

---

## PHẦN 1: ĐỊNH VỊ HỌC THUẬT & TÍNH MỚI CỦA ĐỀ TÀI

### 1.1. Bản chất cốt lõi của Hệ thống
Đề tài xây dựng nền tảng quản lý vận hành bán lẻ và dịch vụ kỹ thuật, có hỗ trợ ra quyết định. Việc kết hợp ba nhóm kỹ thuật dưới đây là phạm vi triển khai, không tự chứng minh tính mới học thuật; khoảng trống ứng dụng cần được đối chiếu với nghiên cứu và nhu cầu cụ thể:
1. **Học máy & Dự báo Chuỗi thời gian (Machine Learning & Time-Series Forecasting)**: Ứng dụng XGBoost Regressor với kỹ thuật trích xuất đặc trưng trễ và chu kỳ để dự báo nhu cầu kinh doanh.
2. **Hệ thống Thông tin Địa lý (Spatial GIS Intelligence)**: Ứng dụng PostgreSQL/PostGIS, SRID 4326 WGS84; shared distance/radius dùng khoảng cách spheroid. Đây là khoảng cách địa lý, không phải tuyến đường hay dữ liệu giao thông.
3. **Trợ lý truy xuất và công cụ có kiểm soát**: Truy xuất quy chế qua kho tri thức, kết hợp handler nghiệp vụ và phê duyệt các action được hỗ trợ. Loại embedding và nhánh sinh câu trả lời phải đối chiếu cấu hình/bằng chứng từng lần chạy; không mặc định mọi câu trả lời đến từ LLM.

---

## PHẦN 2: LÀM RÕ 3 RANH GIỚI PHẠM VI TRỌNG YẾU (SCOPE RISK MITIGATION)

Để bảo vệ thành công đồ án với điểm số tối đa, sinh viên cần nắm vững 3 ranh giới phạm vi sau đây để chủ động định hướng Hội đồng, tránh bị cuốn vào các câu hỏi ngoài phạm vi đề cương:

---

### RANH GIỚI 1: KHÔNG PHẢI HỆ THỐNG QUẢN LÝ KHO BÃI (WMS) CHUYÊN SÂU

Hệ thống cũng không được trình bày là ERP hoàn chỉnh. Không tuyên bố đã triển
khai kế toán tổng hợp, quản trị sản xuất hay toàn bộ chuỗi cung ứng chỉ vì có
đơn hàng, nhập hàng và tồn kho. Ví dụ LST/LSTM/GRU/Transformer thầy gửi minh họa
cách lập luận bối cảnh → khoảng trống → giải pháp, không phải yêu cầu thêm model.

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Tại sao hệ thống có chức năng nhập hàng, tồn kho nhưng không thấy quản lý sơ đồ kệ (bin/rack/aisle), quét mã vạch picking/packing, hay định tuyến xe chở hàng trong kho?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Mục tiêu đề cương**: Đề tài được phê duyệt là nền tảng quản lý vận hành bán lẻ và dịch vụ IT, **không phải là hệ thống Quản lý Kho vật lý (Warehouse Management System - WMS)**.
2. **Vai trò của dữ liệu tồn kho**: Các bảng `StockBalance` và phiếu nhập `GoodsReceipt` trong `apps/retail` chỉ đóng vai trò là **dữ liệu trạng thái bổ trợ (Auxiliary Operational State)** nhằm phục vụ bài toán bán hàng và dự báo nhu cầu bổ sung hàng hóa.
3. **Mối liên kết với AI**: 
   - Hệ thống không quản lý thao tác bốc xếp tại kho bãi vật lý.
   - Khuyến nghị bổ sung hàng hỗ trợ người quản lý xem xét. Không diễn giải thành action nhập kho tự động: stock reorder chưa có domain contract/rollback đủ để ánh xạ thực thi qua approval.

---

### RANH GIỚI 2: WEBSITE CÔNG KHAI LÀ CỔNG TIẾP NHẬN ĐA KÊNH (OMNICHANNEL INGESTION GATEWAY)

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Đề tài này có phải chỉ là làm một website bán hàng thương mại điện tử (e-commerce) hay không?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Trọng tâm đề tài**: Cổng nội bộ (`/noibo/`) phục vụ quản lý vận hành; cổng công khai (`apps/public_web`) tiếp nhận nhu cầu khách hàng. Không quy đổi hai phần thành tỷ lệ phần trăm khối lượng hoặc hàm lượng công nghệ vì chưa có phương pháp đo.
2. **Định vị kỹ thuật**: Cổng công khai (`/`) được thiết kế đóng vai trò là **Cổng Tiếp nhận Đa kênh (Omnichannel Ingestion Gateway)**:
   - Khách hàng xem danh mục, gửi yêu cầu sự cố IT (`/yeu-cau-dich-vu/`) hoặc đặt hàng.
   - Các sự kiện đặt hàng và yêu cầu dịch vụ cung cấp dữ liệu cho quy trình nội bộ. Dữ liệu seed là dữ liệu mô phỏng, không chứng minh lưu lượng giao dịch thực tế.
3. **Cách ly logic bằng workspace và RBAC**:
   - Đăng ký khách hàng công khai không tự cấp WorkspaceMembership hay quyền quản lý nội bộ. Đây không phải cách ly vật lý hoặc mạng (air-gap).
   - Kiểm soát trường dữ liệu và quyền truy cập phụ thuộc từng serializer/view/service. Chỉ kết luận trên các đường thực thi đã kiểm thử; không tuyên bố an toàn tuyệt đối.

---

### RANH GIỚI 3: PHẠM VI PHIÊN BẢN V1 VS LỘ TRÌNH V2–V5 (OUT OF SCOPE)

> [!IMPORTANT]
> **Rủi ro Hội đồng có thể đặt câu hỏi**:  
> *"Tại sao không thấy áp dụng Isolation Forest để phát hiện gian lận đơn hàng, thuật toán Hungary để gán lịch, hay cổng kết nối ERP trực tiếp với SAP/Odoo?"*

#### Lập luận phản biện chuẩn xác của Sinh viên:
1. **Phạm vi làm việc**:
   - Danh sách bắt buộc/mở rộng nằm trong ACADEMIC_ACCEPTANCE_SCOPE.md. Không khẳng định thầy đã duyệt phụ lục V2–V5 khi chưa đối chiếu comment trong Word mới nhất.
2. **Các nhóm đã có mã nguồn, cần đọc kèm bằng chứng và giới hạn**:
   - Dự báo chuỗi thời gian bằng **XGBoost Regressor** (đã đánh giá định lượng so sánh với Naive Baseline qua MAE, RMSE, MAPE).
   - Bản đồ số GIS tích hợp **PostgreSQL/PostGIS**, công thức trắc địa **Haversine** và truy vấn bán kính phục vụ.
   - Trợ lý AI hỏi đáp **RAG với pgvector**, có nguồn và kiểm tra fallback; chưa chứng minh mọi câu trả lời đúng, ca tài liệu mâu thuẫn còn chưa đạt.
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
  Dữ liệu được chia theo thời gian; tỷ lệ và mốc train/holdout phải đọc từ cấu hình, provenance của run đang báo cáo. Lag/rolling và baseline cần cùng điều kiện thông tin quá khứ. Kiểm thử hiện có kiểm tra các ca cụ thể, không chứng minh triệt tiêu mọi khả năng rò rỉ; backtest một bước không thay thế đánh giá dự báo đệ quy nhiều ngày."*

---

### Câu hỏi 2: *"Hệ số $R^2$ của mô hình dự báo doanh thu mang giá trị âm hoặc chưa cao, em giải thích điều này dưới góc độ học máy như thế nào?"*
- **Trả lời của Sinh viên**:  
  *"R² âm cho biết tổng sai số bình phương lớn hơn cách dự đoán bằng trung bình của tập đánh giá, khi phương sai khác 0. Không thể chỉ từ chỉ số này kết luận nguyên nhân là chuỗi biến động mạnh. Cần đối chiếu MAE/RMSE với baseline trên cùng tập, cùng horizon và đúng run. Phải giữ các target kém baseline; cải thiện trên một target của dữ liệu seed chưa chứng minh hiệu quả vận hành thực tế."*

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
  Shared service dùng `Distance(..., spheroid=True)` của PostGIS; lọc bán kính dùng cùng thước đo. Đây là khoảng cách trắc địa ellipsoid, không phải tuyến đường giao thông. `GIS_REFERENCE_EVIDENCE.md` ghi nguồn tham chiếu, tọa độ và dung sai của các ca đã kiểm tra; không suy rộng sai số dưới 1% cho mọi vị trí hoặc mọi chức năng GIS."*

---

### Câu hỏi 5: *"Khung RAG (Retrieval-Augmented Generation) của em làm thế nào để ngăn chặn hiện tượng ảo giác (Hallucination) khi người dùng hỏi các câu hỏi không có trong tài liệu?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, khung RAG trong đề tài được thiết kế theo cơ chế **Grounded Factuality** với 3 tầng bảo vệ chống ảo giác:  
  1. **Tầng Phân đoạn & Vector hóa**: Tài liệu quy chế nội bộ được phân đoạn nhỏ (Chunk size 500 ký tự, overlap 50 ký tự) và lập chỉ mục không gian vector với `pgvector`.  
  2. **Tầng Đánh giá Độ tương đồng (Similarity Threshold)**: Retrieval dùng ngưỡng có thể cấu hình và ghi ngưỡng thực dùng trong metadata. Không có tài liệu và không có dữ liệu tool thì trả fallback; không coi một ngưỡng cố định là bảo đảm đúng ngữ nghĩa.
  3. **Tầng Prompt Engineering nghiêm ngặt**: Chỉ thị hệ thống (System Prompt) ràng buộc AI: 'Chỉ được trả lời dựa trên ngữ cảnh được cung cấp. Nếu không tìm thấy thông tin, phải từ chối lịch sự và tuyệt đối không tự suy diễn'.  
  Precision/recall phải lấy từ run có TP/FP/FN và mẫu số rõ; kết quả lịch sử không chứng minh khả năng từ chối mọi câu hỏi ngoài phạm vi. Đợt 35 chỉ là pipeline offline với fixture, không phải đánh giá model live."*

---

### Câu hỏi 6: *"Hệ thống hỗ trợ 2 mô hình kinh doanh Retail và Service. Làm thế nào để đảm bảo dữ liệu giữa hai bên không bị lẫn lộn (Data Isolation)?"*
- **Trả lời của Sinh viên**:  
  *"Dạ thưa Thầy/Cô, hệ thống áp dụng kiến trúc **Workspace Tenancy cô lập logic nghiêm ngặt**:  
  1. Các thực thể gốc như `Order`, `Product`, `ServiceRequest` có workspace. `OrderItem` lấy phạm vi qua `order`, `Task` qua `service_request`; `User` và `Role` không phải bảng dữ liệu riêng của một workspace.
  2. Resolver/middleware xác minh workspace được chọn; truy vấn chỉ được giới hạn khi view/service áp dụng `.for_workspace(ws)` hoặc điều kiện tương đương qua đối tượng cha. ORM không tự lọc mọi truy vấn.
  3. Một người có thể có membership ở nhiều workspace với vai trò khác nhau. Truy cập cần membership đang hoạt động và quyền tương ứng, ngoại trừ bypass superuser được quy định. Các test isolation là bằng chứng cho ca đã chạy, không phải chứng minh mọi đường thực thi không có lỗi."*

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

Hệ thống có các luồng nghiệp vụ và kiểm thử local được ghi theo từng batch.
Chưa thể kết luận hoàn thành toàn bộ: chat realtime/bản tin nội bộ chưa có bằng
chứng triển khai, RAG conflict và thực nghiệm sâu còn thiếu, Word/IEEE và các
cổng production chưa nghiệm thu đầy đủ. Dùng ma trận yêu cầu để trình bày đúng
phần đã làm và phần còn hạn chế.

---
*Tài liệu chuẩn bị cho kỳ bảo vệ Đồ án Tốt nghiệp — Khoa CNTT — Trường ĐH Tài nguyên và Môi trường TP.HCM.*
