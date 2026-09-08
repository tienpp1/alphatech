# Hướng dẫn Trình diễn Tương tác Trực tiếp (Live Demo Guide)
## Sổ tay Thao tác Từng bước Dành cho Hội đồng Đánh giá & Báo cáo Trực tiếp

Tài liệu này cung cấp kịch bản trình diễn chi tiết từng bước, có khả năng tái lập hoàn toàn để chứng minh năng lực của **Nền tảng Vận hành Doanh nghiệp Thông minh**. Hướng dẫn được thiết kế để bất kỳ người vận hành, giảng viên hoặc thành viên hội đồng nào cũng có thể thực hiện buổi trình diễn trọn vẹn mà không cần phải nắm sâu mã nguồn trước đó.

---

## 0. Thiết lập Ban đầu & Nạp Dữ liệu Mẫu

Trước khi bắt đầu buổi trình diễn trực tiếp, hãy đảm bảo dịch vụ PostgreSQL đang chạy và dữ liệu mẫu đã được nạp:
```bash
# 1. Kiểm tra cấu hình môi trường và migrations cơ sở dữ liệu
python manage.py check
python manage.py migrate

# 2. Khởi tạo người dùng mẫu, không gian làm việc và mô hình XGBoost đã huấn luyện sẵn
python manage.py seed_demo

# 3. Khởi chạy máy chủ phát triển
python manage.py runserver 127.0.0.1:8000
```

### Thông tin Đăng nhập Thử nghiệm (Chỉ áp dụng trong Môi trường Phát triển)
| Vai trò Người dùng | Tên đăng nhập | Mật khẩu | Mục đích Trình diễn |
| :--- | :--- | :--- | :--- |
| **Khách hàng Công khai** | Đăng ký tại `/dang-ky/` | Tự thiết lập | Mua sắm sản phẩm công nghệ, gửi yêu cầu dịch vụ IT, quản lý tài khoản khách hàng (`/tai-khoan/`) |
| **Quản trị viên Hệ thống** | `admin` | `AdminPass123!` | Cổng quản trị `/noibo/`: Cấu hình hệ thống, tích hợp dữ liệu, kiểm toán toàn diện |
| **Quản lý Vận hành** | `manager` | `ManagerPass123!` | Cổng quản trị `/noibo/`: Phê duyệt có con người kiểm duyệt (HITL), điều phối dịch vụ, xem khuyến nghị |
| **Nhân viên Thương mại / Kỹ thuật**| `employee` | `EmployeePass123!` | Cổng quản trị `/noibo/`: Nhập đơn hàng, cập nhật công việc kỹ thuật, hỏi đáp trợ lý AI |
| **Kiểm toán viên / Người xem** | `viewer` | `ViewerPass123!` | Cổng quản trị `/noibo/`: Xem báo cáo chỉ đọc và bản đồ GIS đã che mặt dữ liệu định danh (PII) |

---

## KỊCH BẢN 0 — WEBSITE DOANH NGHIỆP CÔNG KHAI (THEME SÁNG TRẮNG) & XÁC THỰC KHÁCH HÀNG

**Mục tiêu**: Trình diễn giao diện công khai hiện đại (Light / White Theme), quy trình đăng ký/đăng nhập khách hàng, cổng thông tin tài khoản cá nhân và cơ chế bảo mật cô lập hoàn toàn khỏi cổng quản trị nội bộ.

1. **Khám phá Trang chủ Công khai (`/`)**:
   - Truy cập: `http://127.0.0.1:8000/`.
   - Quan sát thiết kế Theme Sáng / Trắng chuẩn mực (nền trắng `#FFFFFF`, thẻ xám nhạt `#F8FAFC`, chữ tối màu `#0F172A`, điểm nhấn xanh `#2563EB`).
   - Khám phá 2 đơn vị kinh doanh: **ABC Tech Store** & **XYZ IT Technical Services**.
2. **Khám phá Danh mục Sản phẩm Bán lẻ (`/san-pham/`)**:
   - Tìm kiếm từ khóa, lọc theo nhóm danh mục công nghệ (Laptop, Điện thoại, Chuột, Bàn phím,...).
   - Xem chi tiết sản phẩm (`/san-pham/1/`): giá niêm yết bán lẻ, mô tả, nút "Liên hệ mua hàng".
   - *Bảo mật*: Tuyệt đối không để lộ giá vốn (`cost_price`), số lượng tồn kho hay dữ liệu nhà cung cấp.
3. **Khám phá Dịch vụ Kỹ thuật IT (`/dich-vu/`)**:
   - Xem 4 nhóm dịch vụ: Cài đặt hệ thống, Bảo trì hệ thống, Tư vấn quản trị CSDL, Sửa chữa thiết bị.
   - Gửi yêu cầu dịch vụ an toàn tại `/yeu-cau-dich-vu/`.
4. **Quy trình Đăng ký Tài khoản Khách hàng (`/dang-ky/`)**:
   - Nhấp **"Đăng nhập"** trên header -> chọn tab **"Đăng ký"** (hoặc truy cập `/dang-ky/`).
   - Điền thông tin: Họ tên, Email, Số điện thoại, Địa chỉ, Mật khẩu $\ge 8$ ký tự, tích chọn Đồng ý Điều khoản.
   - Nút **"Đăng ký bằng Google"** tuân thủ nhận diện thương hiệu Google Identity Services.
   - Đăng ký thành công -> Tự động chuyển hướng vào **Cổng Tài khoản Khách hàng (`/tai-khoan/`)**.
5. **Cổng Tài khoản Khách hàng (`/tai-khoan/`)**:
   - Xem thông tin hồ sơ khách hàng, mã định danh, lịch sử các yêu cầu dịch vụ IT đã gửi và đơn hàng đã mua.
   - *Cô lập quyền hạn*: Khách hàng cố tình truy cập `http://127.0.0.1:8000/noibo/` sẽ bị chặn và điều hướng an toàn về `/tai-khoan/?notice=customer_only`.
6. **Quy trình Quên mật khẩu (`/quen-mat-khau/`)**:
   - Truy cập `/quen-mat-khau/`, nhập email để nhận liên kết đặt lại mật khẩu với token an toàn qua console email backend.

---

## KỊCH BẢN 1 — MIỀN VẬN HÀNH THƯƠNG MẠI BÁN LẺ & PHÂN TÍCH KHÔNG GIAN GIS


**Mục tiêu**: Trình diễn quy trình bán lẻ thương mại, mạng lưới chi nhánh không gian, phân tích doanh thu và các khuyến nghị vận hành có khả năng giải trình.

1. **Đăng nhập**:
   - Mở trình duyệt truy cập: `http://127.0.0.1:8000/accounts/login/`.
   - Đăng nhập với tài khoản: `manager` / `ManagerPass123!`.
2. **Chọn Không gian làm việc Bán lẻ**:
   - Sử dụng bộ chuyển đổi không gian làm việc hoặc truy cập trực tiếp `http://127.0.0.1:8000/retail/dashboard/`.
   - Đảm bảo không gian làm việc đang chọn là **Cửa hàng Bán lẻ ABC** (`abc-retail`).
3. **Kiểm tra Danh mục Sản phẩm Thương mại**:
   - Truy cập **Sản phẩm** (`http://127.0.0.1:8000/retail/products/`).
   - Quan sát 40 sản phẩm kinh doanh thuộc 6 danh mục bán lẻ (Điện tử, Phụ kiện, Phần mềm,...) với giá tiền định dạng Decimal chuẩn bằng VND.
4. **Kiểm tra Đơn hàng & Bảng điều khiển Bán hàng**:
   - Truy cập **Đơn hàng** (`http://127.0.0.1:8000/retail/orders/`).
   - Xem các đơn hàng gồm nhiều mặt hàng, liên kết khách hàng, phương thức thanh toán và huy hiệu trạng thái vòng đời (`HOÀN THÀNH`, `CHỜ XỬ LÝ`).
   - Kiểm tra **Bảng điều khiển Bán lẻ** (`http://127.0.0.1:8000/retail/dashboard/`) hiển thị chỉ số doanh thu thời gian thực, giá trị đơn hàng trung bình (AOV) và các chi nhánh có doanh số hàng đầu.
5. **Kiểm tra Phân tích Không gian GIS Bán lẻ**:
   - Truy cập **GIS Bán lẻ** (`http://127.0.0.1:8000/retail/gis/`).
   - **Lớp Bản đồ Chi nhánh**: Quan sát các chi nhánh vật lý tại Hà Nội/TP.HCM với popup tương tác Leaflet hiển thị quản lý cửa hàng và doanh thu chi nhánh.
   - **Lớp Phân bố Khách hàng**: Bật/tắt điểm khách hàng để xem mật độ nhu cầu theo không gian.
   - **Xác thực Bảo vệ Quyền riêng tư (Privacy Guardrail)**: Đăng xuất và đăng nhập lại bằng tài khoản `viewer` $\to$ mở lại GIS Bán lẻ $\to$ quan sát thấy tên khách hàng đã được che mặt (`Khách hàng CUST-X`) và các trường số điện thoại/email bị ẩn hoàn toàn.

---

## KỊCH BẢN 2 — MIỀN VẬN HÀNH DỊCH VỤ KỸ THUẬT CNTT

**Mục tiêu**: Trình diễn quản lý sự cố dịch vụ kỹ thuật CNTT, giám sát cam kết SLA, điều phối kỹ sư hiện trường và tính toán chi phí nhân công.

1. **Chuyển sang Không gian Dịch vụ Kỹ thuật**:
   - Chuyển không gian làm việc sang **Công ty Dịch vụ Kỹ thuật XYZ** (`xyz-service`) qua thanh điều hướng hoặc truy cập `http://127.0.0.1:8000/services/dashboard/`.
2. **Kiểm tra Danh mục Dịch vụ CNTT**:
   - Truy cập **Danh mục Dịch vụ** (`http://127.0.0.1:8000/services/services/`).
   - Xác nhận 4 danh mục dịch vụ CNTT chuẩn mực:
     - `INSTALLATION` (Cài đặt hệ thống - Lắp đặt tủ rack, triển khai hạ tầng mạng)
     - `MAINTENANCE` (Bảo trì hệ thống - Bảo trì định kỳ, cập nhật firmware)
     - `DATABASE_CONSULTING` (Tư vấn CSDL - Tối ưu hóa PostgreSQL, chẩn đoán chỉ mục)
     - `DEVICE_REPAIR` (Sửa chữa thiết bị - Hàn mạch phần cứng, sửa chữa bo mạch chủ)
3. **Kiểm tra Phiếu Yêu cầu Dịch vụ & Giám sát SLA**:
   - Truy cập **Phiếu Yêu cầu** (`http://127.0.0.1:8000/services/requests/`).
   - Chọn một phiếu có mức ưu tiên `KHẨN CẤP` hoặc `CAO`.
   - Quan sát đồng hồ đếm ngược SLA: thời hạn phản hồi và giải quyết mục tiêu dựa trên cấp độ chính sách SLA.
4. **Kiểm tra Ghi nhận Giờ công & Chi phí Thực tế**:
   - Mở trang chi tiết phiếu yêu cầu.
   - Xem các **Mục Giờ công Kỹ thuật**: số giờ làm việc của kỹ sư $\times$ `employee.hourly_labor_rate` được tính toán tự động trên máy chủ với tính toàn vẹn giao dịch.
5. **Kiểm tra Phân tích GIS Dịch vụ Hiện trường**:
   - Truy cập **GIS Dịch vụ** (`http://127.0.0.1:8000/services/gis/`).
   - Xem vị trí các phiếu sự cố được vẽ cùng tọa độ thời gian thực của các kỹ sư hiện trường.
   - Thử nghiệm tìm kiếm bán kính PostGIS: tìm kiếm tất cả kỹ sư đạt yêu cầu kỹ thuật trong phạm vi 25 km tính từ phiếu sự cố đang mở.

---

## KỊCH BẢN 3 — TIẾP NHẬN DỮ LIỆU & XƯỞNG ÁNH XẠ (MAPPING STUDIO)

**Mục tiêu**: Trình diễn tiếp nhận dữ liệu hàng loạt từ bảng tính bên ngoài và chuyển đổi khai báo thành lược đồ chuẩn hóa.

1. **Truy cập Giao diện Tích hợp Dữ liệu**:
   - Truy cập **Tích hợp Dữ liệu** (`http://127.0.0.1:8000/integration/`).
   - Xem các nguồn dữ liệu đã đăng ký và các lô nhập thô.
2. **Kiểm tra Vùng đệm Staging Thô**:
   - Nhấp vào một `ImportJob` đã có (ví dụ: `Lô Nhập Đơn hàng Bán lẻ`).
   - Nhấn mạnh rằng các tiêu đề thô bên ngoài (`ma_kh`, `tong_thanh_toan`, `ngay_dat_hang`) được lưu nguyên bản trong các dòng JSONB của `RawImportRecord` mà không từ chối các định dạng chưa hoàn hảo.
3. **Trình diễn Xưởng Ánh xạ (Mapping Studio)**:
   - Truy cập **Xưởng Ánh xạ** (`http://127.0.0.1:8000/mapping/`).
   - Chọn **Hồ sơ Ánh xạ Đơn hàng Bán lẻ** đang hoạt động.
   - Xem các quy tắc ánh xạ mang tính khai báo:
     - `ma_kh` $\longrightarrow$ `customer_id` (Ánh xạ Trường)
     - `tong_thanh_toan` $\longrightarrow$ `total_amount` (Chuyển đổi Kiểu: Decimal)
     - `ngay_dat_hang` $\longrightarrow$ `order_date` (Chuyển đổi Kiểu: Date)
4. **Xem trước Công thức An toàn Trực tiếp**:
   - Chứng minh các quy tắc chuyển đổi được đánh giá qua **Bộ Đánh giá AST An toàn (Safe AST Evaluator)**.
   - Chỉ ra rằng các hành vi thực thi mã tùy ý (như `__import__` hoặc `eval`) đều bị chặn đứng và vượt qua các bài kiểm thử bảo mật nghiêm ngặt.

---

## KỊCH BẢN 4 — TRỢ LÝ TRI THỨC DOANH NGHIỆP CÓ CĂN CỨ (RAG ASSISTANT)

**Mục tiêu**: Trình diễn tiếp nhận tài liệu, truy xuất vector ngữ nghĩa, trích dẫn nguồn và cơ chế chống ảo giác xác định.

1. **Truy cập Trợ lý Cơ sở Tri thức**:
   - Truy cập **Cơ sở Tri thức** (`http://127.0.0.1:8000/knowledge/`) hoặc **Trợ lý AI** (`http://127.0.0.1:8000/ai/assistant/`).
   - Xem các tài liệu đã được đánh chỉ mục (Chính sách Cửa hàng Bán lẻ, Quy trình Kỹ thuật CNTT, Tiêu chuẩn SLA).
2. **Câu hỏi 1: Chính sách Doanh nghiệp Được Hỗ trợ (Có Trích dẫn Nguồn)**:
   - Trong khung chat AI, nhập câu hỏi:
     > *"Chính sách đổi trả sản phẩm lỗi tại cửa hàng bán lẻ như thế nào?"*
   - **Kết quả Quan sát**: Trợ lý trả về lời giải thích chính xác, có căn cứ, trích dẫn rõ tiêu đề tài liệu `"Chính Sách Đổi Trả Và Bảo Hành Sản Phẩm"`, hiển thị mã đoạn trích (chunk ID) và điểm tương đồng vector.
3. **Câu hỏi 2: Quy trình Vận hành Tiêu chuẩn Kỹ thuật CNTT**:
   - Trong không gian Dịch vụ, nhập câu hỏi:
     > *"Quy trình bảo dưỡng phòng máy chủ định kỳ gồm những bước nào?"*
   - **Kết quả Quan sát**: Trợ lý nêu rõ các bước phòng chống tĩnh điện ESD, lịch vệ sinh và kiểm tra sao lưu trực tiếp từ tài liệu quy trình SOP đã nạp.
4. **Câu hỏi 3: Câu hỏi Ngoài Phạm vi (Cơ chế Chống Ảo giác)**:
   - Nhập một câu hỏi hoàn toàn ngoài nghiệp vụ hoặc bịa đặt:
     > *"Quy trình phóng tàu vũ trụ lên mặt trăng của công ty là gì?"*
   - **Kết quả Quan sát**: Hệ thống không tìm thấy đoạn trích nào vượt qua ngưỡng tin cậy và lập tức phản hồi thông điệp dự phòng bất biến chính xác:
     > *"Không tìm thấy thông tin đủ tin cậy trong tài liệu của doanh nghiệp."*

---

## KỊCH BẢN 5 — PHÂN TÍCH DỰ BÁO CHUỖI THỜI GIAN VỚI XGBOOST

**Mục tiêu**: Trình diễn mô hình XGBoost, đánh giá theo trình tự thời gian chống rò rỉ dữ liệu (zero data leakage) và dự báo chu kỳ 14 ngày.

1. **Truy cập Bảng điều khiển Dự báo**:
   - Truy cập **Dự báo & Phân tích Xu hướng** (`http://127.0.0.1:8000/forecasting/`).
2. **Xem xét Các Chỉ số Đánh giá Hiệu năng (KPIs)**:
   - Kiểm tra các thẻ tóm tắt hiệu năng mô hình:
     - **MAE**: Sai số Tuyệt đối Trung bình (độ lệch giá trị thực tế theo VND)
     - **RMSE**: Căn bậc hai Sai số Trung bình Bình phương
     - **MAPE**: Sai số Phần trăm Tuyệt đối Trung bình (tính toán nghiêm ngặt trên các giá trị thực tế khác 0)
     - **Cải thiện (Improvement)**: Mức tăng phần trăm tương đối so với Đường cơ sở Naive Persistence
3. **Kiểm tra Biểu đồ Tương tác**:
   - Quan sát biểu đồ Chart.js trực quan hiển thị:
     - Doanh số thực tế lịch sử (đường liền nét)
     - Dự báo tương lai 14 ngày (đường nét đứt)
     - Vùng dải dự báo xấp xỉ 95% có đổ bóng mờ
4. **Mức độ Quan trọng của Đặc trưng (Feature Importance)**:
   - Cuộn xuống biểu đồ tầm quan trọng đặc trưng hiển thị các yếu tố chi phối lớn nhất (ví dụ: `lag_7`, `rolling_mean_7`, `day_of_week`).
   - Nhấn mạnh phần khuyến cáo giải trình rằng dải dự báo đệ quy thể hiện phương sai dư sai lịch sử chứ không phải là khoảng xác suất tuyệt đối.

---

## KỊCH BẢN 6 — KHUYẾN NGHỊ VẬN HÀNH CÓ TÍNH XÁC ĐỊNH

**Mục tiêu**: Trình diễn hệ thống hỗ trợ ra quyết định minh bạch với cấu trúc giải trình rõ ràng.

1. **Truy cập Trung tâm Khuyến nghị**:
   - Truy cập **Khuyến nghị Vận hành** (`http://127.0.0.1:8000/recommendations/`).
2. **Kiểm tra Cấu trúc Giải trình (Explainability Contract)**:
   - Chọn một khuyến nghị đang chờ (ví dụ: `SERVICE_SLA_AT_RISK` hoặc `SERVICE_NEARBY_TECHNICIAN`).
   - Quan sát cấu trúc giải trình 4 phần hoàn chỉnh:
     - **WHAT (Đề xuất hành động)**: Khuyến nghị vận hành cụ thể (ví dụ: "Điều phối kỹ thuật viên Nguyễn Văn A xử lý phiếu yêu cầu #12").
     - **WHY (Lý do & Căn cứ logic)**: Lập luận nhân quả (ví dụ: "Phiếu sắp vượt hạn SLA 2 giờ; kỹ thuật viên ở khoảng cách 3.2 km với khối lượng công việc hiện tại thấp").
     - **EVIDENCE (Bằng chứng số liệu / GIS)**: Khoảng cách trắc địa PostGIS, số công việc đang thực hiện, đánh giá kỹ năng và mức ưu tiên sự cố.
     - **EXPECTED EFFECT (Tác động kỳ vọng)**: Giảm thiểu nguy cơ vi phạm cam kết SLA và cân bằng tải làm việc cho kỹ sư hiện trường.

---

## KỊCH BẢN 7 — HÀNH ĐỘNG CÔNG CỤ CÓ KIỂM SOÁT, PHÊ DUYỆT & KIỂM TOÁN

**Mục tiêu**: Trình diễn Cơ chế Quản trị AI có Con người Kiểm duyệt (HITL), Phân tách Trách nhiệm (Separation of Duties) và Nhật ký Kiểm toán Bất biến chống can thiệp.

1. **Khởi tạo Hành động qua Trợ lý AI Assistant**:
   - Trong khung chat AI, nhập một lệnh thay đổi trạng thái hệ thống:
     > *"Phân công kỹ thuật viên 1 cho ticket 1"*
2. **Xác nhận Hành động Đột biến Bị chặn Trực tiếp**:
   - Quan sát thấy phiếu yêu cầu **không bị sửa đổi trực tiếp ngay trong cơ sở dữ liệu**.
   - Trợ lý AI phản hồi rằng một đề xuất thay đổi đã được gửi lên hệ thống phê duyệt, trả về mã theo dõi `#AR-<id>`.
3. **Xác thực Cơ chế Phân tách Trách nhiệm (Separation of Duties)**:
   - Với tài khoản `employee`, nếu cố gắng phê duyệt yêu cầu này qua API $\to$ hệ thống lập tức trả về lỗi `403 Forbidden` / `ToolPermissionDenied`. Người tạo yêu cầu không thể tự phê duyệt hành động của chính mình.
4. **Người Quản lý Phê duyệt**:
   - Đăng nhập bằng tài khoản `manager` $\to$ truy cập **Trung tâm Phê duyệt** (`http://127.0.0.1:8000/approvals/`).
   - Kiểm tra yêu cầu đang chờ, xem xét các tham số thay đổi được đề xuất và nhấn **Phê duyệt**.
   - Máy chủ thực thi xử lý nguyên tử (atomic transaction): cập nhật `ServiceRequest.assigned_employee`, tạo `Task` tương ứng và chuyển trạng thái yêu cầu phê duyệt thành `ĐÃ THỰC HIỆN` (`EXECUTED`).
5. **Xác thực Chống Trùng lặp (Idempotency Replay Protection)**:
   - Gửi lại cùng một yêu cầu phê duyệt $\to$ hệ thống trả về kết quả đã lưu đệm với cờ `"idempotent_replay": true` và không tạo ra bất kỳ tác dụng phụ trùng lặp nào.
6. **Kiểm tra Nhật ký Kiểm toán Bất biến (Audit Log)**:
   - Mở Django Admin hoặc truy vấn mô hình `apps.audit.models.AuditLog`.
   - Xác nhận từng giai đoạn trong vòng đời (`AI_MUTATION_REQUESTED`, `APPROVAL_REQUEST_CREATED`, `APPROVAL_DECISION_MADE`, `TOOL_EXECUTED`) đều được lưu trữ vĩnh viễn kèm định danh người thực hiện, dấu thời gian và toàn bộ dữ liệu tham số đầu vào.
