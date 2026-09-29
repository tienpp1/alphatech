> **ĐÍNH CHÍNH 23/09/2026:** Không sử dụng số 97/97 trong bản này để trình bày nghiệm thu. Dùng CHECKLIST_97_PROGRESS.md đính chính; các cổng production còn thiếu bằng chứng.

# HƯỚNG DẪN TRÌNH DIỄN BẢO VỆ TRƯỚC HỘI ĐỒNG CHẤM TỐT NGHIỆP
## (OFFICIAL COMMITTEE DEFENSE LIVE DEMO GUIDE)

> Cập nhật 16/09/2026: đọc `DEMO_IDENTITY_RUNBOOK.md` trước khi thao tác.
> Các kịch bản dưới đây là hướng dẫn cần đối chiếu dữ liệu hiện có, không phải
> biên bản nghiệm thu. Không suy ra quyền từ tên tài khoản hoặc coi mọi khuyến nghị
> là action có thể thực thi. Không chạy seed trên database đã có dữ liệu.

**Đề tài**: Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI
**Sinh viên thực hiện**: Hà Minh Tiến — **MSSV**: 1250080194 — **Lớp**: 12_ĐH_CNPM3  
**Khoa**: Công nghệ Thông tin — **Trường**: Đại học Tài nguyên và Môi trường TP.HCM (HCMUNRE)  
**Giảng viên hướng dẫn**: ThS. Nguyễn Duy Tuấn  
**Căn cứ văn bản**: Bám sát cấu trúc kịch bản Mục 3.6 và cam kết tại Đề cương Đồ án Tốt nghiệp.

---

## MỤC LỤC KỊCH BẢN
1. [Khởi tạo Hệ thống & Đăng nhập](#0-khởi-tạo-hệ-thống--đăng-nhập)
2. [Kịch bản 1: Nghiệp vụ Bán lẻ & Dự báo XGBoost (Mục 3.6.1)](#kịch-bản-1-nghiệp-vụ-bán-lẻ--dự-báo-xgboost-mục-361)
3. [Kịch bản 2: Dịch vụ Kỹ thuật & Cảnh báo SLA (Mục 3.6.2)](#kịch-bản-2-dịch-vụ-kỹ-thuật--cảnh-báo-sla-mục-362)
4. [Kịch bản 3: Phân tích Không gian GIS & Điều phối (Mục 3.6.3)](#kịch-bản-3-phân-tích-không-gian-gis--điều-phối-mục-363)
5. [Kịch bản 4: Trợ lý AI RAG & Studio Ánh xạ Dữ liệu (Mục 3.6.4)](#kịch-bản-4-trợ-lý-ai-rag--studio-ánh-xạ-dữ-liệu-mục-364)
6. [Kịch bản Phụ: Cổng Tiếp nhận Đa kênh & Bảo mật Cách ly RBAC](#kịch-bản-phụ-cổng-tiếp-nhận-đa-kênh--bảo-mật-cách-ly-rbac)

---

## 0. KHỞI TẠO HỆ THỐNG & ĐĂNG NHẬP

### 0.1. Lệnh chuẩn bị trên Terminal (Trước giờ bảo vệ)
```bash
# Di chuyển vào thư mục gốc dự án
cd d:\ai_business_platform

# 1. Kiểm tra tính toàn vẹn hệ thống
python manage.py check

# 2. Đồng bộ CSDL PostGIS
python manage.py migrate

# 3. Nạp bộ dữ liệu thực nghiệm mẫu và mô hình AI
python manage.py seed_demo --confirm-empty-demo

# 3b. Kiểm toán toàn vẹn tồn kho và chính sách Strict Fulfillment (Cổng 73)
python manage.py check_fulfillment_stock --workspace abc-retail

# 4. Khởi chạy máy chủ
python manage.py runserver 127.0.0.1:8000
```

### 0.2. Danh sách Tài khoản Trình diễn
| Tài khoản | Tên đăng nhập | Mật khẩu | Phạm vi Phân quyền (RBAC) | Vai trò trong buổi bảo vệ |
| :--- | :--- | :--- | :--- | :--- |
| **Quản trị viên Hệ thống** | `admin` | `AdminPass123!` | Toàn quyền (Superuser), xem tất cả Workspace | Thao tác kịch bản Quản trị, Tích hợp, Duyệt cấp cao |
| **Quản lý Cửa hàng Bán lẻ** | `manager` | `ManagerPass123!` | MANAGER Retail; EMPLOYEE Service | Xem dự báo retail; phê duyệt chỉ với action hợp lệ, không tự duyệt yêu cầu của mình |
| **Nhân viên / Kỹ thuật viên** | `employee` | `EmployeePass123!` | EMPLOYEE Retail; EMPLOYEE Service (Cổng 70) | Xem/tạo đơn retail; xem request/task/lịch trình service và tự ghi nhận giờ công `log_labor` (Bị cấm `manage_request`, `assign_request`, `manage_task`, `view_analytics`) |
| **Khách hàng Mua sắm** | `customer1` | Đăng ký trực tiếp | Chỉ truy cập Cổng công khai (`/`) và Cổng tài khoản (`/tai-khoan/`) | Minh chứng cách ly hoàn toàn khách hàng khỏi `/noibo/` |

---

## KỊCH BẢN 1: NGHIỆP VỤ BÁN LẺ & DỰ BÁO XGBOOST (MỤC 3.6.1)

### 1.1. Mục tiêu chứng minh với Hội đồng
- Phân tích hiệu quả kinh doanh qua bảng điều khiển vận hành tổng hợp (Executive Dashboard).
- Mô hình học máy XGBoost dự báo doanh thu và số lượng đơn hàng theo chuỗi thời gian thực.
- Động cơ sinh khuyến nghị vận hành tự động (AI Recommendation Engine).
- Cơ chế kiểm soát con người (Human-in-the-loop): Đề xuất AI bắt buộc phải qua phê duyệt của Quản lý mới được kích hoạt hành động.
- Ghi vết kiểm toán bất biến (Audit Logging).

### 1.2. Các bước thao tác trên màn hình
1. **Đăng nhập Hệ thống Nội bộ**:
   - Truy cập: `http://127.0.0.1:8000/dang-nhap/`.
   - Đăng nhập với tài khoản `manager` / `ManagerPass123!`.
   - Hệ thống chuyển hướng vào **Cổng Điều hành Doanh nghiệp**: `http://127.0.0.1:8000/noibo/`.

2. **Khảo sát Dashboard Bán lẻ (`ABC Tech Store`)**:
   - Truy cập: `http://127.0.0.1:8000/noibo/retail/`.
   - Quan sát các thẻ KPI thời gian thực: Tổng doanh thu, số lượng đơn hàng, giá trị trung bình đơn (AOV), số lượng khách hàng hoạt động.
   - Nhấp vào tab **"Dự báo XGBoost"** (`/noibo/forecasting/`):
     - Quan sát biểu đồ đường đối chiếu giữa *Doanh thu thực tế (Actual)* và *Dự báo AI (Forecast)* cho 14 ngày kế tiếp.
     - Quan sát các chỉ số sai số định lượng: $MAE$, $RMSE$, $MAPE$ và phần trăm cải thiện so với mô hình cơ sở (*Naive Baseline*).

3. **Xem Đề xuất Khuyến nghị AI (AI Recommendation Engine)**:
   - Truy cập: `http://127.0.0.1:8000/noibo/recommendations/`.
   - Hệ thống hiển thị danh sách các đề xuất vận hành tự động sinh ra từ dự báo:
     - Ví dụ: Đề xuất *"Bổ sung tồn kho cho nhóm sản phẩm Laptop Gaming do dự báo nhu cầu tăng 35% cuối tuần"*.
     - Đề xuất *"Tối ưu hóa giá khuyến mãi phụ kiện bàn phím cơ"*.
   - Nhấp vào chi tiết một Đề xuất: Quan sát phần **Lý do giải trình (AI Explainability / Rationale)** và điểm tin cậy (*Confidence Score*).

4. **Kích hoạt Quy trình Phê duyệt Kiểm soát Con người (Human-in-the-loop)**:
   - Nhấp nút **"Gửi phê duyệt (Submit for Approval)"**.
   - Đăng nhập tài khoản cấp cao hơn `admin` / `AdminPass123!` (hoặc chuyển tài khoản).
   - Truy cập trang Quản lý Phê duyệt: `http://127.0.0.1:8000/noibo/approvals/`.
   - Xem yêu cầu phê duyệt mới: Xem chi tiết tham số thay đổi (*Payload Diff*), người yêu cầu, thời gian.
   - Chỉ duyệt action đã có contract và đủ tham số hợp lệ; không dùng khuyến nghị bổ sung hàng làm ví dụ giao dịch nhập kho tự động.
   - Đọc riêng trạng thái phê duyệt và kết quả thực thi, đối chiếu dữ liệu trước/sau. Không suy ra thực thi thành công chỉ từ nhãn `APPROVED`.

5. **Kiểm chứng Nhật ký Kiểm toán (Audit Log)**:
   - Với tài khoản staff được phép đọc audit, truy cập `http://127.0.0.1:8000/admin/audit/auditlog/`. Không có trang `/noibo/audit/` trong routes hiện tại.
   - Chỉ ra cho Hội đồng bản ghi kiểm toán vừa phát sinh:
     - `Actor`: `admin`
     - `Action`: `APPROVAL_ACTION`
     - `Target`: Mã đề xuất / Đơn hàng
     - `Timestamp`: Thời gian chuẩn xác đến từng giây
     - `Client IP`: Địa chỉ IP truy cập
     - `Changes`: Cấu trúc JSON lưu vết trước và sau thay đổi.

> **Lời thoại sinh viên thuyết minh**:  
> *"Hệ thống tách khuyến nghị, phê duyệt và thực thi. Chỉ action đã có contract được đưa vào quy trình thực thi có kiểm soát. Khuyến nghị nhập hàng chưa chứng minh giao dịch nhập kho tự động; kết quả phải được đối chiếu bằng trạng thái, dữ liệu trước/sau và bản ghi audit của ca trình diễn."*

---

## KỊCH BẢN 2: DỊCH VỤ KỸ THUẬT & CẢNH BÁO SLA (MỤC 3.6.2)

### 2.1. Mục tiêu chứng minh với Hội đồng
- Phân luồng tiếp nhận sự cố kỹ thuật IT (Service Request / Ticket).
- Thuật toán AI chấm điểm ưu tiên tự động (Priority Scoring: Urgent, High, Medium, Low) căn cứ theo loại sự cố và chính sách SLA.
- Giám sát đồng hồ đếm ngược vi phạm cam kết dịch vụ (SLA Breach Alert).
- Điều phối kỹ thuật viên và theo dõi tiến độ hoàn tất.

### 2.2. Các bước thao tác trên màn hình
1. **Truy cập Cổng Vận hành Dịch vụ**:
   - Chọn workspace dịch vụ có quyền phù hợp rồi mở `http://127.0.0.1:8000/noibo/services/`. Dashboard cần `service.view_analytics`; người chỉ có quyền xem request mở `/noibo/services/requests/`.
   - Quan sát Dashboard Dịch vụ: Tổng số sự cố mở, tỷ lệ tuân thủ SLA, số kỹ thuật viên đang trực chiến ngoài hiện trường.

2. **Tạo Sự cố Kỹ thuật Mới (Incident Ticket)**:
   - UI nội bộ hiện chưa có route form tạo request riêng. Chuẩn bị ticket demo trước hoặc dùng API `POST /api/v1/service-ops/requests/` với tài khoản có `service.create_request` và workspace đã được cấp quyền.
   - Customer/Service được chọn phải thuộc đúng workspace. Đọc request mẫu trong `tests/test_service_requests.py`; không nhập ID từ workspace khác hoặc dùng dữ liệu thật cho buổi demo.

3. **Kiểm tra AI Phân loại & Chấm điểm Mức độ Ưu tiên**:
   - Đối chiếu priority và SLA thực tế trên ticket. Enum hiện có LOW/MEDIUM/HIGH/CRITICAL, không có URGENT.
   - Hạn phản hồi/giải quyết phụ thuộc SLA được cấu hình và thời điểm tạo; không gán trước kết quả 30 phút/2 giờ hoặc khẳng định phân loại văn bản bằng AI khi chưa kiểm chứng.

4. **Phân công Kỹ thuật viên & Cập nhật Tiến độ**:
   - Nhấp vào nút **"Điều phối kỹ thuật viên"**.
   - Chọn Kỹ thuật viên Nguyễn Văn An (chuyên môn Database, trạng thái sẵn sàng).
   - Với tài khoản `employee` (vai trò EMPLOYEE tại `xyz-service` theo Cổng 70): Kỹ thuật viên có quyền xem task được phân công (`service.view_task`), xem lịch trình (`service.view_schedule`), và tự ghi nhận giờ công lao động thực tế (`POST /api/v1/service-ops/tasks/{id}/labor/` với quyền `log_labor`).
   - Nếu muốn chuyển trạng thái task (`PENDING` -> `IN_PROGRESS` -> `COMPLETED`) cần quyền `service.manage_task`; chuyển trạng thái request cần `service.manage_request` (được cấp cho `manager` hoặc `admin`).
   - Kiểm tra dữ liệu/trạng thái và timestamp trước/sau. Tỷ lệ SLA phải tính từ sự kiện thực tế của bộ dữ liệu; không gán sẵn kết luận tuân thủ 100%.

---

## KỊCH BẢN 3: PHÂN TÍCH KHÔNG GIAN GIS & ĐIỀU PHỐI (MỤC 3.6.3)

### 3.1. Mục tiêu chứng minh với Hội đồng
- Ứng dụng công nghệ Hệ thông tin địa lý (GIS) trên nền CSDL không gian PostGIS kết hợp thư viện Leaflet.js.
- Trực quan hóa đa lớp dữ liệu không gian: Chi nhánh bán lẻ, khách hàng, vị trí kỹ thuật viên, địa điểm phát sinh sự cố.
- Tính khoảng cách spheroid WGS84 bằng PostGIS và lọc bán kính theo cùng thước đo (xem `GIS_REFERENCE_EVIDENCE.md`); không phải khoảng cách đường bộ.
- Đề xuất điều phối nhân sự tối ưu dựa trên khoảng cách địa lý.

### 3.2. Các bước thao tác trên màn hình
1. **Truy cập Bản đồ Không gian Số GIS**:
   - Bản đồ retail: `http://127.0.0.1:8000/noibo/retail/gis/`; bản đồ service: `http://127.0.0.1:8000/noibo/services/gis/`. Hai trang tách theo workspace, không có trang bản đồ tổng hợp chung trong route hiện tại.
   - Bản đồ trung tâm TP.HCM hiển thị với nền OpenStreetMap trực quan.

2. **Thao tác Bật/Tắt Lớp Dữ liệu (Spatial Layers Control)**:
   - Tại hộp điều khiển lớp (Layer Control) góc trên bên phải bản đồ:
     - Tích chọn **Lớp Chi nhánh Cửa hàng (Retail Branches)**: Hiển thị các icon cửa hàng tại Quận 1, Quận 10, Bình Thạnh.
     - Tích chọn **Lớp Khách hàng (Customers)**: Hiển thị mật độ phân bố khách hàng trên địa bàn thành phố.
     - Tích chọn **Lớp Kỹ thuật viên Hiện trường (Field Technicians)**: Hiển thị vị trí thực tế của nhân sự.
     - Tích chọn **Lớp Sự cố đang mở (Pending Incidents)**: Các điểm đánh dấu cảnh báo màu đỏ.

3. **Tương tác Điểm & Xem Bán kính Phục vụ (Buffer Radius)**:
   - Nhấp vào Chi nhánh Quận 1 (Chợ Bến Thành):
     - Popup hiển thị tên cửa hàng, địa chỉ, số điện thoại, doanh số trong ngày.
   - Nhấp vào nút **"Vẽ bán kính giao hàng 5km"**:
     - Bản đồ vẽ đường tròn đệm (Buffer Circle) bán kính 5.000m xung quanh cửa hàng.
     - Hệ thống lọc tự động danh sách các khách hàng nằm trong vùng phủ phục vụ của chi nhánh.

4. **Điều phối Kỹ thuật viên theo Khoảng cách Địa lý (Spatial Nearest Assignment)**:
   - Nhấp vào một điểm Sự cố đang chờ tại Landmark 81 (Quận Bình Thạnh).
   - Nhấp nút **"Tìm Kỹ thuật viên gần nhất"**:
     - Thuật toán GIS chạy phép tính khoảng cách trắc địa Geodesic Haversine từ tọa độ sự cố `(10.7950, 106.7219)` tới toàn bộ kỹ thuật viên đang trực tuyến.
     - Hệ thống đề xuất: Kỹ thuật viên Trần Minh Đức (vị trí Quận 1, khoảng cách 3.62 km, thời gian di chuyển dự kiến 12 phút).
     - Nhấp nút **"Xác nhận Điều phối"** để gửi nhiệm vụ cho kỹ thuật viên.

> **Lời thoại sinh viên thuyết minh**:  
> *"Hệ thống dùng PostGIS và WGS84 SRID 4326 để hỗ trợ truy vấn địa lý trong nghiệp vụ. Đợt 27 đối chiếu một số phép đo với GeographicLib và cung xích đạo giải tích; đây không phải đo đạc thực địa hoặc chứng nhận sai số dưới 1% trên mọi vị trí. Khoảng cách địa lý khác quãng đường giao thông; xem GIS_REFERENCE_EVIDENCE.md để biết ca đo và giới hạn."*

---

## KỊCH BẢN 4: TRỢ LÝ AI RAG & STUDIO ÁNH XẠ DỮ LIỆU (MỤC 3.6.4)

### 4.1. Mục tiêu chứng minh với Hội đồng
- Cơ chế Hỏi đáp Thông minh bám sát sự thật (Grounded RAG - Retrieval-Augmented Generation).
- Chống ảo giác (Anti-hallucination): Trả lời chính xác có trích dẫn tài liệu quy chế nội bộ, từ chối an toàn với câu hỏi ngoài phạm vi.
- Studio Ánh xạ Dữ liệu Chuẩn (Universal Ingestion & AI Field Mapping Studio): Chuyển đổi dữ liệu CSV/Excel phi chuẩn thành Chuẩn Dữ liệu Doanh nghiệp thống nhất.

### 4.2. Các bước thao tác trên màn hình

#### Phần A: Trợ lý AI RAG Hỏi đáp Quy chế Nội bộ
1. **Khảo sát Kho Tri thức (Knowledge Base)**:
   - Truy cập: `http://127.0.0.1:8000/noibo/knowledge/`.
   - Xem danh mục tài liệu đã nạp vào hệ thống:
     - *Quy chế Bảo hành & Đổi trả Hàng hóa 2026 (Retail SOP)*
     - *Quy trình Khắc phục Sự cố & Cam kết Thời gian Phản hồi SLA (Service SOP)*.
   - Bấm vào tài liệu để xem các đoạn trích (Chunks) đã được vector hóa lưu trữ trong `pgvector`.

2. **Thực hiện Hỏi đáp Tương tác với Trợ lý AI**:
   - Truy cập trợ lý nội bộ: `http://127.0.0.1:8000/noibo/ai/`. Copilot trên website công khai là luồng khác, không thay thế trợ lý nội bộ và không có cùng quyền dữ liệu.
   - **Thử nghiệm 1 (Tra cứu nghiệp vụ có trích dẫn nguồn)**:
     - *Nhập câu hỏi*: `"Khách hàng mua laptop tại cửa hàng có được đổi trả trong 7 ngày đầu không và điều kiện là gì?"`
     - *Kết quả mong đợi*: Trợ lý AI trích xuất đúng Điều 3 của Quy chế Bán hàng, trả lời rõ ràng: Khách hàng được đổi trả 1-đổi-1 trong 7 ngày nếu lỗi phần cứng từ nhà sản xuất, giữ nguyên hộp và phụ kiện. Cuối câu trả lời có **Thẻ trích dẫn (Citation)**: `[Quy_che_Bao_hanh_2026.pdf - Mục 3.1]`.
   - **Thử nghiệm 2 (Tra cứu SLA dịch vụ)**:
     - *Nhập câu hỏi*: `"Thời gian cam kết phản hồi cho sự cố mức độ Khẩn cấp là bao nhiêu lâu?"`
     - *Kết quả mong đợi*: AI trả lời cam kết phản hồi tối đa 30 phút và xử lý dứt điểm trong 2 giờ theo Bảng SLA cấp độ 1.
   - **Thử nghiệm 3 (Kiểm chứng chống ảo giác - Anti-hallucination)**:
     - *Nhập câu hỏi ngoài phạm vi*: `"Công ty có bán vé máy bay đi du lịch Đà Nẵng không?"`
     - *Kết quả mong đợi*: Trợ lý AI từ chối lịch sự: *"Xin lỗi, thông tin này không nằm trong tài liệu và dữ liệu vận hành nội bộ của công ty. Tôi chỉ có thể hỗ trợ các nghiệp vụ liên quan đến bán lẻ thiết bị công nghệ và dịch vụ kỹ thuật IT."*

#### Phần B: Studio Tích hợp & Ánh xạ Dữ liệu Chuẩn
1. **Truy cập Studio Tích hợp**:
   - Bấm vào thẻ thứ 5 trên Dashboard hoặc truy cập: `http://127.0.0.1:8000/noibo/integration/`.
   - Xem danh sách các Nguồn Dữ liệu (Data Sources) và Lịch sử nạp tệp (Import Jobs).

2. **Nạp tệp Dữ liệu Thô (CSV/Excel)**:
   - Mở trình nhập tệp: `/noibo/integration/import/`.
   - Chọn tệp dữ liệu mẫu từ đối tác hoặc chi nhánh cũ (ví dụ: file CSV có tiêu đề cột không chuẩn như `ma_sp`, `ten_hang`, `gia_tien`, `so_luong_kho`).
   - Chọn đối tượng đích: `Product (Sản phẩm)`.

3. **AI Gợi ý Ánh xạ Tự động (AI Auto-mapping)**:
   - Truy cập: `http://127.0.0.1:8000/noibo/mapping/`.
   - Mở Hồ sơ Ánh xạ (Mapping Profile).
   - Hệ thống tự động phân tích độ tương đồng ngữ nghĩa và gợi ý:
     - `ma_sp` $\rightarrow$ `sku` (Độ tin cậy: 98%)
     - `ten_hang` $\rightarrow$ `name` (Độ tin cậy: 95%)
     - `gia_tien` $\rightarrow$ `price` (Độ tin cậy: 99%)
     - `so_luong_kho` $\rightarrow$ `stock_quantity` (Độ tin cậy: 94%)
   - Bấm **"Xem trước chuyển đổi (Preview Ingestion)"**: Hệ thống hiển thị bảng dữ liệu sau khi ánh xạ thử nghiệm.
   - Bấm **"Thực thi Nạp vào CSDL Chuẩn (Execute Import)"**: Dữ liệu được làm sạch, xác thực và lưu vào bảng nghiệp vụ chính thức.

---

## KỊCH BẢN PHỤ: CỔNG TIẾP NHẬN ĐA KÊNH & BẢO MẬT CÁCH LY RBAC

### 1. Ý nghĩa Nghiệp vụ
- Minh chứng vai trò của Cổng Website Công khai (`/`) là **Cổng Tiếp nhận Đa kênh (Omnichannel Ingestion Gateway)**, phát sinh đơn hàng và sự cố tự nhiên từ khách hàng.
- Trình diễn ca tài khoản khách hàng bị từ chối truy cập `/noibo/`; đây là bằng chứng cho ca đã chạy, không chứng minh hệ thống bất khả xâm phạm.

### 2. Các bước chứng minh
1. **Trải nghiệm Mua hàng & Gửi Sự cố từ Cổng Công khai**:
   - Mở cửa sổ ẩn danh (Incognito Window) tại: `http://127.0.0.1:8000/`.
   - Vào `/san-pham/`, xem danh mục thiết bị công nghệ với giao diện sáng hiện đại.
   - Cho sản phẩm vào giỏ hàng, mở Drawer giỏ hàng, nhấp xem chi tiết giỏ hàng tại `/gio-hang/`.
   - Gửi yêu cầu dịch vụ cứu hộ IT tại `/yeu-cau-dich-vu/`.
2. **Kiểm chứng Hàng rào Bảo mật (Security Isolation Enforcement)**:
   - Tại cửa sổ trình duyệt của khách hàng, cố tình gõ trực tiếp URL quản trị: `http://127.0.0.1:8000/noibo/`.
   - **Kết quả bảo mật**: Hệ thống lập tức kích hoạt Middleware bảo vệ, chặn đứng truy cập và chuyển hướng về `/tai-khoan/?notice=customer_only`.
   - Không xuất hiện bất kỳ thông tin nội bộ nào (giá vốn, biên lợi nhuận, lương nhân viên).

---

## TỔNG KẾT BẢNG ĐỐI CHIẾU TIÊU CHÍ NGHIỆM THU CỦA HỘI ĐỒNG
*(Trạng thái nghiệm thu: xem CHECKLIST_97_PROGRESS.md. Kết luận 97/97 trước đây đã bị thu hồi; bản hướng dẫn demo không thay bằng chứng nghiệm thu.)*

| STT | Nhóm Tiêu chí Nghiệm thu | Trạng thái Đóng | Vị trí Mã nguồn & Hồ sơ Minh chứng |
| :---: | :--- | :---: | :--- |
| **1** | Bảng điều khiển quản trị 2 Workspace Retail & Service | **Theo bằng chứng từng mục** | `apps/retail`, `apps/service_ops`, `templates/dashboard/` |
| **2** | Dự báo chuỗi thời gian XGBoost đối chiếu Baseline | **Theo bằng chứng từng mục** | `apps/forecasting`, `docs/HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md` |
| **3** | Khuyến nghị AI có người quản lý duyệt (HITL) | **Theo bằng chứng từng mục** | `apps/recommendations`, `apps/approvals`, `apps/audit` |
| **4** | Bản đồ số GIS Leaflet & PostGIS, tính khoảng cách | **Theo bằng chứng từng mục** | `apps/gis`, phép tính trắc địa geodesic WGS84, khóa Nominatim cache |
| **5** | Trợ lý RAG hỏi đáp có trích dẫn và đối chiếu tài liệu | **Theo bằng chứng từng mục** | `apps/knowledge`, `pgvector`, Gold Chunks, bộ chấm số liệu ngoại tuyến (không phải runtime guard) |
| **6** | Studio Ánh xạ Dữ liệu Chuẩn (ETL phi cấu trúc) | **Theo bằng chứng từng mục** | `apps/integration`, `apps/mapping`, xác thực dữ liệu nguồn SDM |
| **7** | Bảo mật RBAC & Phân lập Cổng Khách hàng / Cổng Nội bộ | **Theo bằng chứng từng mục** | `apps/accounts`, `middleware.py`, Kết quả thực chạy: TEST_EXECUTION_EVIDENCE.md |
| **8** | Phân quyền Kỹ thuật viên & Tác vụ `log_labor` (Cổng 70) | **Theo bằng chứng từng mục** | `docs/HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md`, `test_role_acceptance_matrix.py` |
| **9** | Kiểm soát Tồn kho Đa kênh & Strict Fulfillment (Cổng 73) | **Theo bằng chứng từng mục** | `docs/HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md`, `check_fulfillment_stock` |
| **10**| Rà soát Danh mục SOP & Ranh giới Nghiệp vụ (Cổng 47) | **Theo bằng chứng từng mục** | `docs/HO_SO_RA_SOAT_TAI_LIEU_SOP_VA_TRONG_TAM_NGHIEP_VU.md`, 7 Primary vs 17 Benchmark |
| **11**| Lịch trình Hành chính & Lộ trình Hậu Tốt nghiệp (Cổng 3, 6)| **Theo bằng chứng từng mục** | `docs/HO_SO_LICH_TRINH_HANH_CHINH_VA_LO_TRINH_PHAT_TRIEN.md`, Tuần 15-19, 5 Roadmap items |
| **12**| Hồ sơ Vận hành Hạ tầng Production Runbook (Cổng 90–97) | **Theo bằng chứng từng mục** | `docs/HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md` |

---
*Tài liệu được chuẩn bị phục vụ kỳ bảo vệ Đồ án Tốt nghiệp Đại học — Khóa 12 CNTT — Trường Đại học Tài nguyên và Môi trường TP.HCM (HCMUNRE).*

