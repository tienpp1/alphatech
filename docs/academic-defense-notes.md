# Ghi chú Bảo vệ Học thuật & Căn cứ Kỹ thuật (Academic Defense Notes)
## Nền tảng Vận hành Doanh nghiệp Thông minh

Tài liệu này cung cấp các câu trả lời kỹ thuật chuẩn mực, có căn cứ vững chắc phục vụ cho việc bảo vệ đồ án và giải trình trước hội đồng chuyên môn. Mọi công nghệ cốt lõi và quyết định kiến trúc lớn đều được giải thích theo khung đánh giá chuẩn hóa, chặt chẽ: **Bản chất là gì? Tại sao chọn? Đầu vào là gì? Quá trình xử lý ra sao? Đầu ra là gì? Đánh giá như thế nào? Giới hạn là gì?**

---

### 1. Framework Django
- **BẢN CHẤT LÀ GÌ?**: Một web framework bậc cao bằng Python tuân thủ mô hình Model-Template-View (MTV), tích hợp sẵn ORM, xác thực người dùng và các middleware bảo mật.
- **TẠI SAO CHỌN?**: Cho phép phát triển nhanh chóng và an toàn một kiến trúc đơn khối dạng mô-đun (modular monolith). Django cung cấp tính toàn vẹn giao dịch nguyên bản, cơ chế phòng chống tấn công CSRF/clickjacking mạnh mẽ, quản lý migration CSDL tích hợp và hỗ trợ GeoDjango không gian tuyệt vời.
- **ĐẦU VÀO LÀ GÌ?**: Các yêu cầu HTTP (JSON của REST API hoặc yêu cầu tải trang HTML của trình duyệt).
- **QUÁ TRÌNH XỬ LÝ?**: Định tuyến URL $\to$ Middleware An ninh $\to$ Xác thực phiên & Không gian làm việc (Tenancy) $\to$ Thực thi View/ViewSet $\to$ Biên dịch truy vấn ORM sang SQL.
- **ĐẦU RA LÀ GÌ?**: Phản hồi HTTP (trang giao diện HTML hoặc cấu trúc JSON chuẩn hóa).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: 276 bài kiểm thử tự động, không có độ trôi migration, lệnh kiểm tra sức khỏe `python manage.py check`.
- **GIỚI HẠN LÀ GÌ?**: Chi phí tài nguyên cho mô hình request-response nguyên khối; xử lý bất đồng bộ phức tạp hơn các framework async nhẹ (như FastAPI), nhưng đối với dữ liệu quan hệ doanh nghiệp và GIS, Django ORM và GeoDjango vượt trội hoàn toàn.

---

### 2. Cơ sở Dữ liệu PostgreSQL
- **BẢN CHẤT LÀ GÌ?**: Hệ quản trị cơ sở dữ liệu quan hệ đối tượng mã nguồn mở (ORDBMS).
- **TẠI SAO CHỌN?**: Tuân thủ chuẩn ACID toàn diện, hỗ trợ xuất sắc cho lược đồ quan hệ, độ chính xác số học Decimal cho tài chính, khóa ngoại liên kết (cascades) và khả năng mở rộng trực tiếp với PostGIS và pgvector trong cùng một động cơ CSDL thống nhất.
- **ĐẦU VÀO LÀ GÌ?**: Các câu truy vấn SQL và lệnh giao dịch được sinh ra bởi Django ORM.
- **QUÁ TRÌNH XỬ LÝ?**: Phân tích cú pháp truy vấn, tối ưu hóa dựa trên chi phí (cost-based optimization), thực thi giao dịch MVCC (Kiểm soát đồng thời đa phiên bản) và ghi nhật ký trước khi ghi dữ liệu (WAL).
- **ĐẦU RA LÀ GÌ?**: Các bản ghi quan hệ, dữ liệu tổng hợp và thực thi ràng buộc toàn vẹn.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Hiệu suất chỉ mục, kiểm thử ràng buộc khóa ngoại và kiểm thử mức độ cô lập giao dịch.
- **GIỚI HẠN LÀ GÌ?**: Giới hạn mở rộng theo chiều dọc so với các kho lưu trữ NoSQL phân tán; cần migration cấu trúc khi thay đổi bảng.

---

### 3. PostGIS & GeoDjango
- **BẢN CHẤT LÀ GÌ?**: PostGIS là tiện ích mở rộng không gian cho PostgreSQL. GeoDjango là mô-đun tích hợp sẵn trong Django để làm việc với dữ liệu địa lý GIS.
- **TẠI SAO CHỌN?**: Cho phép thực hiện các phép tính trắc địa mặt cầu thực tế (`ST_Distance`, `ST_Within`, `ST_MakeEnvelope`) trực tiếp trong câu lệnh CSDL thay vì tính toán xấp xỉ Euclid trong bộ nhớ Python.
- **ĐẦU VÀO LÀ GÌ?**: Tọa độ địa lý 2D (Kinh độ, Vĩ độ) theo chuẩn WGS 84 (`SRID 4326`).
- **QUÁ TRÌNH XỬ LÝ?**: PostGIS xây dựng chỉ mục không gian R-Tree (GIST) trên các đối tượng hình học và tính toán khoảng cách trắc địa trên hình cầu elip WGS 84.
- **ĐẦU RA LÀ GÌ?**: Khoảng cách trắc địa theo mét, giá trị boolean kiểm tra nằm trong vùng và cấu trúc GeoJSON FeatureCollection theo RFC 7946.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử truy vấn không gian tự động, xác minh thứ tự khoảng cách, lọc theo bán kính và tính hợp lệ của GeoJSON.
- **GIỚI HẠN LÀ GÌ?**: Tăng tải CPU CSDL khi giao cắt các đa giác phức tạp; yêu cầu các thư viện nhị phân GDAL/GEOS trên hệ điều hành máy chủ.

---

### 4. Động cơ Tiếp nhận Dữ liệu (CSV, Excel, Mock API)
- **BẢN CHẤT LÀ GÌ?**: Đường ống tiếp nhận dữ liệu đưa các tệp dữ liệu bên ngoài không đồng nhất vào bảng đệm staging bất biến (`RawImportRecord`).
- **TẠI SAO CHỌN?**: Dữ liệu doanh nghiệp bên ngoài thường có bảng mã, định dạng và cấu trúc rất đa dạng. Việc phân tích trực tiếp vào các mô hình miền nghiệp vụ sẽ làm ứng dụng sập khi gặp các dòng dữ liệu lỗi.
- **ĐẦU VÀO LÀ GÌ?**: Tệp CSV bên ngoài (UTF-8, Windows-1258), bảng tính Excel `.xlsx`/`.xls`, hoặc JSON từ Mock REST API.
- **QUÁ TRÌNH XỬ LÝ?**: Kiểm tra tệp (dung lượng $\le$ 10MB, đuôi tệp an toàn) $\to$ Tự động nhận diện bảng mã $\to$ Đọc luồng dữ liệu từng dòng $\to$ Lưu vào JSONB kèm theo ghi nhận lỗi ở mức từng dòng.
- **ĐẦU RA LÀ GÌ?**: Bản ghi trạng thái `ImportJob` và các bản ghi staging `RawImportRecord`.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử cô lập dòng lỗi, kiểm thử khôi phục bảng mã tiếng Việt, kiểm thử chặn tấn công SSRF.
- **GIỚI HẠN LÀ GÌ?**: Giới hạn tệp tải lên 10MB để phòng chống cạn kiệt bộ nhớ và tấn công từ chối dịch vụ (DoS).

---

### 5. Xưởng Ánh xạ Dữ liệu (Mapping Studio) & Bộ Đánh giá AST An toàn
- **BẢN CHẤT LÀ GÌ?**: Động cơ chuẩn hóa lược đồ, chuyển đổi các trường dữ liệu thô trong vùng đệm thành lược đồ nghiệp vụ chuẩn hóa thông qua các quy tắc khai báo và công thức Abstract Syntax Tree (AST).
- **TẠI SAO CHỌN?**: Tách rời hoàn toàn lược đồ nguồn bên ngoài (ví dụ: `ma_kh`, `tong_tien`) khỏi các mô hình miền cốt lõi mà không cần sử dụng các hàm nguy hiểm như `eval()` hay `exec()`.
- **ĐẦU VÀO LÀ GÌ?**: Từ điển dữ liệu thô trong staging và các cấu hình `MappingRule` đang kích hoạt.
- **QUÁ TRÌNH XỬ LÝ?**: Đổi tên trường $\to$ Chuyển đổi kiểu dữ liệu $\to$ Đánh giá an toàn các biểu thức số học/nối chuỗi bằng AST $\to$ Kiểm tra tính hợp lệ của lược đồ.
- **ĐẦU RA LÀ GÌ?**: Từ điển thực thể miền chuẩn hóa đã được kiểm duyệt, sẵn sàng ghi vào CSDL qua giao dịch nguyên tử.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử tiêm mã độc (cố tình gọi `__import__`, `open()`), kiểm thử chuyển đổi kiểu dữ liệu và kiểm thử ghi nhận vào CSDL.
- **GIỚI HẠN LÀ GÌ?**: Danh sách trắng AST loại trừ vòng lặp, rẽ nhánh điều kiện và gọi hàm tùy tiện; các chuyển đổi phức tạp đòi hỏi viết hàm chuyển đổi Python định nghĩa trước.

---

### 6. Mô hình Dữ liệu Chuẩn hóa (Standard Data Model - SDM)
- **BẢN CHẤT LÀ GÌ?**: Bản đặc tả bản thể học (ontology) chuẩn hóa, định nghĩa các kiểu trường, ràng buộc và tập lựa chọn nghiêm ngặt cho 10 thực thể cốt lõi trên cả hai miền Bán lẻ và Dịch vụ.
- **TẠI SAO CHỌN?**: Ngăn chặn ô nhiễm lược đồ nghiệp vụ. Mọi phân tích hạ nguồn (Dự báo, GIS, Khuyến nghị) đều dựa trên giao diện nhất quán, có thể đoán trước bất kể sự khác biệt của dữ liệu nguồn ban đầu.
- **ĐẦU VÀO LÀ GÌ?**: Các bản ghi dữ liệu sau khi ánh xạ.
- **QUÁ TRÌNH XỬ LÝ?**: Kiểm tra kiểu ở mức trường, kiểm tra biểu thức chính quy (regex), giải quyết khóa ngoại và kiểm tra tập giá trị hợp lệ theo `apps/mapping/canonical.py`.
- **ĐẦU RA LÀ GÌ?**: Các mô hình miền có kiểu dữ liệu mạnh và hợp lệ.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Bộ kiểm thử tính nhất quán chuẩn hóa và kiểm tra toàn vẹn mô hình.
- **GIỚI HẠN LÀ GÌ?**: Đòi hỏi thiết kế lược đồ cẩn trọng từ đầu; việc thay đổi trường chuẩn hóa đòi hỏi cập nhật lại các hồ sơ ánh xạ.

---

### 7. RAG (Retrieval-Augmented Generation)
- **BẢN CHẤT LÀ GÌ?**: Kiến trúc neo đậu tri thức giúp truy xuất các đoạn trích tài liệu liên quan và đưa chúng vào ngữ cảnh prompt của mô hình ngôn ngữ lớn (LLM).
- **TẠI SAO CHỌN?**: Loại bỏ hiện tượng ảo giác (hallucination), đảm bảo câu trả lời phản ánh chính xác chính sách/quy trình của doanh nghiệp và cung cấp trích dẫn nguồn có thể kiểm chứng mà không tốn chi phí fine-tune mô hình.
- **ĐẦU VÀO LÀ GÌ?**: Câu hỏi bằng ngôn ngữ tự nhiên của người dùng (ví dụ: "Chính sách đổi trả hàng là gì?").
- **QUÁ TRÌNH XỬ LÝ?**: Vector hóa câu hỏi $\to$ Tìm kiếm vector tương đồng cosine $\to$ Lắp ghép ngữ cảnh $\to$ Tổng hợp prompt có căn cứ cho LLM $\to$ Trích xuất trích dẫn nguồn.
- **ĐẦU RA LÀ GÌ?**: Câu trả lời bằng ngôn ngữ tự nhiên kèm theo tiêu đề tài liệu, mã đoạn trích và điểm tương đồng.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Độ chính xác truy xuất (85.7%), Độ đúng đắn có căn cứ (100%), Trích dẫn nguồn (100%), Độ chính xác câu dự phòng chống ảo giác (100%).
- **GIỚI HẠN LÀ GÌ?**: Phụ thuộc vào chất lượng phân đoạn (chunking) và mô hình embedding; không thể suy diễn các thông tin hoàn toàn không có trong tài liệu.

---

### 8. Text Embeddings & pgvector
- **BẢN CHẤT LÀ GÌ?**: Vector embeddings chuyển đổi các đoạn văn bản thành các vector số thực 1536 chiều. `pgvector` là tiện ích mở rộng của PostgreSQL cung cấp tính năng đánh chỉ mục và tìm kiếm tương đồng vector.
- **TẠI SAO CHỌN?**: Tránh việc phải sử dụng các CSDL vector bên ngoài rời rạc (như Pinecone, Milvus). Lưu vector ngay trong PostgreSQL duy trì tính nhất quán giao dịch, sao lưu hợp nhất và lọc không gian làm việc trong cùng một câu lệnh truy vấn.
- **ĐẦU VÀO LÀ GÌ?**: Các đoạn trích văn bản (tối đa 500 tokens).
- **QUÁ TRÌNH XỬ LÝ?**: Vector hóa văn bản $\to$ Lưu vào cột `vector(1536)` $\to$ Truy vấn bằng toán tử khoảng cách cosine (`<=>`).
- **ĐẦU RA LÀ GÌ?**: Danh sách đoạn trích được xếp hạng theo điểm tương đồng ($1 - \text{khoảng cách}$).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Độ thu hồi (recall) của láng giềng gần nhất và độ chính xác truy xuất trên các cặp câu hỏi - tài liệu chuẩn.
- **GIỚI HẠN LÀ GÌ?**: Vector chiều cao tiêu tốn bộ nhớ RAM; các chỉ mục láng giềng gần đúng (HNSW/IVFFlat) đòi hỏi tính toán lại khi lượng dữ liệu cực lớn.

---

### 9. Tích hợp Mô hình Ngôn ngữ Lớn (LLM)
- **BẢN CHẤT LÀ GÌ?**: Mô hình ngôn ngữ tạo sinh được sử dụng chặt chẽ cho việc suy luận, phân loại ý định (intent classification) và tổng hợp câu trả lời có căn cứ.
- **TẠI SAO CHỌN?**: Cung cấp giao diện đàm thoại trực quan để người vận hành doanh nghiệp truy vấn dữ liệu phức tạp và diễn đạt các yêu cầu vận hành một cách tự nhiên.
- **ĐẦU VÀO LÀ GÌ?**: System prompt với chỉ dẫn quản trị nghiêm ngặt, các đoạn tài liệu được truy xuất, danh sách công cụ được phép gọi và tin nhắn của người dùng.
- **QUÁ TRÌNH XỬ LÝ?**: Sinh token bị ràng buộc bởi system prompt; ý định thay đổi trạng thái được trích xuất thành tham số gọi công cụ có cấu trúc.
- **ĐẦU RA LÀ GÌ?**: Lời giải thích có căn cứ hoặc gói dữ liệu gọi công cụ có cấu trúc.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Đảm bảo 100% không có lệnh ghi CSDL trực tiếp, độ chính xác của trích dẫn và tuân thủ câu dự phòng khi câu hỏi nằm ngoài phạm vi.
- **GIỚI HẠN LÀ GÌ?**: Độ trễ suy luận, chi phí token và câu từ có thể thay đổi nhẹ giữa các lần gọi.

---

### 10. Dự báo Chuỗi Thời gian với XGBoost
- **BẢN CHẤT LÀ GÌ?**: Thuật toán cây quyết định tăng cường gradient (Gradient Boosted Decision Trees) tối ưu hóa, dùng cho hồi quy dạng bảng và dự báo chuỗi thời gian nhiều bước.
- **TẠI SAO CHỌN?**: Vượt trội hơn hẳn so với các mô hình tuyến tính và trung bình trượt trên dữ liệu có tính mùa vụ phi tuyến kèm đặc trưng lịch, đồng thời không đòi hỏi lượng dữ liệu khổng lồ hay bất ổn định trong huấn luyện như mạng nơ-ron hồi quy sâu (LSTM).
- **ĐẦU VÀO LÀ GÌ?**: Chuỗi thời gian lịch sử theo ngày (doanh thu, đơn hàng, phiếu sự cố), độ trễ tự hồi quy ($t-1, t-7, t-14$), thống kê trượt ($\mu_7, \sigma_7$), và các đặc trưng ngày trong tuần/tháng.
- **QUÁ TRÌNH XỬ LÝ?**: Tạo đặc trưng trượt an toàn (chống rò rỉ dữ liệu) $\to$ Chia tập dữ liệu theo thời gian (80% train / 20% test) $\to$ Huấn luyện ensemble cây gradient-boosted $\to$ Dự báo đệ quy chu kỳ 14 ngày tới.
- **ĐẦU RA LÀ GÌ?**: Dự báo điểm, chặn giá trị không âm, dải dự báo xấp xỉ 95% ($\pm 1.96 \cdot \sigma_{\text{residuals}} \cdot \sqrt{1 + 0.05(h-1)}$).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: MAE, RMSE, MAPE, và tỷ lệ cải thiện so với mô hình đường cơ sở Naive Persistence.
- **GIỚI HẠN LÀ GÌ?**: Dự báo đệ quy tích lũy sai số khi chu kỳ dự báo quá dài; dải dự báo mang tính kinh nghiệm dựa trên phần dư chứ không phải phân phối xác suất Bayes calibrated tuyệt đối.

---

### 11. Các Chỉ số Đánh giá Dự báo: MAE, RMSE & MAPE
- **BẢN CHẤT LÀ GÌ?**:
  - **MAE (Mean Absolute Error)**: Độ lệch tuyệt đối trung bình; ít bị ảnh hưởng bởi điểm ngoại lai.
  - **RMSE (Root Mean Squared Error)**: Căn bậc hai của sai số bình phương trung bình; phạt rất nặng các lỗi dự báo có độ lệch lớn.
  - **MAPE (Mean Absolute Percentage Error)**: Sai số phần trăm tuyệt đối trung bình ($\frac{|y - \hat{y}|}{y} \times 100$).
- **TẠI SAO CHỌN?**: Cung cấp góc nhìn toàn diện cả về giá trị tiền tệ thực tế và tỷ lệ phần trăm. MAE phản ánh sai số thông thường hàng ngày, RMSE cảnh báo các sai lệch nghiêm trọng, và so sánh với baseline chứng minh giá trị của thuật toán.
- **GIỚI HẠN & ĐIỂM CẦN LƯU Ý**: MAPE có nhược điểm chí mạng đối với dữ liệu đếm hoặc giá trị gần 0 (ví dụ những ngày chỉ có 0 hoặc 1 phiếu sự cố), việc chia cho số thực tế quá nhỏ sẽ thổi phồng MAPE lên hàng trăm phần trăm. Trong dự án này, MAPE được tính toán nghiêm ngặt trên các ngày có giá trị khác 0, đồng thời ưu tiên MAE và RMSE cho dữ liệu phiếu kỹ thuật.

---

### 12. Động cơ Khuyến nghị Vận hành Xác định & Tính điểm
- **BẢN CHẤT LÀ GÌ?**: Hệ thống khuyến nghị vận hành dựa trên quy tắc (Rule-based), kết hợp các chỉ số KPI, khoảng cách GIS và khối lượng công việc.
- **TẠI SAO CHỌN?**: Tính minh bạch và xác định tuyệt đối. Trong quản trị doanh nghiệp, người vận hành cần hiểu rõ lý do đề xuất để tin tưởng, thay vì các quyết định tự động kiểu hộp đen.
- **ĐẦU VÀO LÀ GÌ?**: Phiếu sự cố đang mở, trạng thái sẵn sàng của kỹ sư, khoảng cách trắc địa PostGIS, số công việc đang xử lý và xu hướng doanh số lịch sử.
- **QUÁ TRÌNH XỬ LÝ?**: Tổ hợp tuyến tính có trọng số đa tiêu chí:
  $$\text{Điểm} = 0.40 \times S_{\text{khoảng\_cách}} + 0.40 \times S_{\text{tải\_công\_việc}} + 0.20 \times S_{\text{kỹ\_năng}}$$
  kèm theo cổng điều kiện bắt buộc ($S = 0$ nếu kỹ sư đang bận hoặc ngừng hoạt động).
- **ĐẦU RA LÀ GÌ?**: Bản ghi khuyến nghị được xếp hạng ưu tiên kèm cấu trúc JSON giải trình (`what`, `why`, `evidence`, `expected_effect`).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử kịch bản xác minh thứ hạng ứng viên, loại trừ người không sẵn sàng và tuân thủ cấu trúc giải trình.
- **GIỚI HẠN LÀ GÌ?**: Các trọng số được cấu hình cố định; không tự động thích ứng nếu quản trị viên không điều chỉnh.

---

### 13. Công cụ Gọi Có Kiểm soát (Tool Calling) & Quy trình Phê duyệt
- **BẢN CHẤT LÀ GÌ?**: Cổng kết nối API tập trung, phân biệt rõ ràng giữa truy vấn `ĐỌC` (`READ`) an toàn và các thao tác `THAY ĐỔI` (`MUTATION`) dữ liệu.
- **TẠI SAO CHỌN?**: Đây là nguyên tắc cốt lõi của Quản trị AI có Con người Kiểm duyệt (HITL). Loại bỏ hoàn toàn rủi ro LLM tự ý phá hoại dữ liệu kinh doanh hoặc tự động đưa ra các quyết định tài chính/vận hành trái phép.
- **ĐẦU VÀO LÀ GÌ?**: Tên công cụ và các tham số JSON đã được xác thực qua lược đồ JSON Schema.
- **QUÁ TRÌNH XỬ LÝ?**: Kiểm tra lược đồ $\to$ Kiểm tra quyền RBAC $\to$ Kiểm tra không gian làm việc $\to$ Công cụ ĐỌC thực thi ngay; Công cụ THAY ĐỔI tự động tạo bản ghi `ApprovalRequest` ở trạng thái `CHỜ XỬ LÝ`.
- **ĐẦU RA LÀ GÌ?**: Dữ liệu viễn trắc tức thì hoặc Mã định danh theo dõi phê duyệt (`#AR-<id>`).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử xác thực lược đồ, kiểm thử từ chối quyền và thực thi cơ chế phân tách trách nhiệm.
- **GIỚI HẠN LÀ GÌ?**: Đòi hỏi phải có người vận hành kiểm tra và duyệt yêu cầu thì hành động mới diễn ra trên thực tế.

---

### 14. Có Con người Kiểm duyệt (HITL) & Phân tách Trách nhiệm (SoD)
- **BẢN CHẤT LÀ GÌ?**: Chính sách quản trị yêu cầu người quản lý phê duyệt các thay đổi trạng thái quan trọng, kết hợp với sự phân tách tuyệt đối giữa người yêu cầu và người phê duyệt.
- **TẠI SAO CHỌN?**: Ngăn ngừa gian lận đơn phương hoặc tự động, hạn chế sai sót vô tình và tránh điều phối nhân sự tùy tiện.
- **ĐẦU VÀO LÀ GÌ?**: Bản ghi `ApprovalRequest` ở trạng thái `CHỜ XỬ LÝ` và thông tin xác thực của người duyệt.
- **QUÁ TRÌNH XỬ LÝ?**: Hệ thống xác minh `người_duyệt != người_yêu_cầu` (trừ superuser) và kiểm tra người duyệt có quyền `approvals.manage_approval`.
- **ĐẦU RA LÀ GÌ?**: Chuyển trạng thái yêu cầu sang `ĐÃ PHÊ DUYỆT` $\to$ `ĐÃ THỰC HIỆN` (hoặc `TỪ CHỐI`).
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử tự động bắt lỗi `ToolPermissionDenied` khi người tạo yêu cầu tự cố tình phê duyệt chính mình.
- **GIỚI HẠN LÀ GÌ?**: Có thể tạo ra độ trễ vận hành nếu người quản lý không trực tuyến để duyệt kịp thời.

---

### 15. Nhật ký Kiểm toán Bất biến (Audit Log)
- **BẢN CHẤT LÀ GÌ?**: Bảng cơ sở dữ liệu chỉ ghi nối tiếp (`AuditLog`), ghi lại người thực hiện, loại hành động, mã thực thể, dấu thời gian, không gian làm việc và toàn bộ tham số thay đổi dạng JSON.
- **TẠI SAO CHỌN?**: Chống chối bỏ (non-repudiation), đáp ứng tiêu chuẩn tuân thủ doanh nghiệp và phục vụ điều tra sau sự cố.
- **ĐẦU VÀO LÀ GÌ?**: Người thực hiện, không gian làm việc, hành động, thực thể đích và siêu dữ liệu thay đổi.
- **QUÁ TRÌNH XỬ LÝ?**: Ghi nhận trong cùng một giao dịch cơ sở dữ liệu nguyên tử với hành động chính.
- **ĐẦU RA LÀ GÌ?**: Bản ghi kiểm toán bất biến.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Xác minh nhật ký kiểm toán được sinh ra trên mọi sự kiện nạp dữ liệu, ánh xạ, gọi công cụ, phê duyệt và hỏi đáp AI; không có bất kỳ API nào cho phép sửa hoặc xóa nhật ký này.
- **GIỚI HẠN LÀ GÌ?**: Tăng dung lượng lưu trữ CSDL theo thời gian; trong môi trường lớn cần có chiến lược phân vùng lưu trữ (table partitioning).

---

### 16. Phân tách Ranh giới Đa Không gian làm việc (Multi-Tenant Workspaces)
- **BẢN CHẤT LÀ GÌ?**: Mẫu kiến trúc cô lập dữ liệu trong đó mọi mô hình nghiệp vụ đều kế thừa `WorkspaceScopedModel` và chứa khóa ngoại trỏ tới `Workspace`.
- **TẠI SAO CHỌN?**: Cho phép nhiều đơn vị kinh doanh (ví dụ Cửa hàng Bán lẻ và Công ty Dịch vụ Kỹ thuật) cùng hoạt động an toàn trên một hạ tầng dùng chung mà không xảy ra rò rỉ dữ liệu chéo.
- **ĐẦU VÀO LÀ GÌ?**: Yêu cầu của người dùng đã xác thực kèm ngữ cảnh không gian làm việc đang chọn.
- **QUÁ TRÌNH XỬ LÝ?**: `WorkspaceMiddleware` xác thực tư cách thành viên; Custom Model Manager `.for_workspace(ws)` lọc tự động mọi truy vấn ORM.
- **ĐẦU RA LÀ GÌ?**: Tập dữ liệu (queryset) được cô lập tuyệt đối theo không gian làm việc.
- **ĐÁNH GIÁ NHƯ THẾ NÀO?**: Kiểm thử thâm nhập chéo không gian làm việc, đảm bảo trả về lỗi `403 Forbidden` hoặc `404 Not Found` khi cố truy cập dữ liệu của tenant khác.
- **GIỚI HẠN LÀ GÌ?**: Kiến trúc CSDL dùng chung (cô lập mức dòng) đòi hỏi lập trình viên phải kỷ luật luôn sử dụng scoped queryset thay vì phụ thuộc vào việc chia tách vật lý CSDL.
