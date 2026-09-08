# Nền tảng Vận hành Doanh nghiệp Thông minh với Phân tích Dữ liệu AI, Dự báo & Hỗ trợ Ra Quyết định

> **Hệ thống Nền tảng Hợp nhất xây dựng trên Django với Không gian làm việc Kép (Bán lẻ & Dịch vụ Kỹ thuật), Phân tích Không gian GIS, Truy xuất Tri thức RAG, Dự báo Chuỗi Thời gian XGBoost, và Hỗ trợ Ra Quyết định Có Con người Kiểm duyệt (Human-in-the-Loop).**

---

## 📌 1. Tổng quan Dự án & Sứ mệnh

Các doanh nghiệp hiện đại thường vận hành với dữ liệu phân mảnh (silos) giữa bán hàng, quản lý khách hàng, hoạt động dịch vụ tại hiện trường và tài liệu quy trình vận hành tĩnh (SOPs). Nền tảng này kết nối các luồng dữ liệu rời rạc thành một hệ thống hỗ trợ ra quyết định thông minh, minh bạch và có khả năng giải trình cao.

### Đường ống Giá trị Cốt lõi (Core Value Pipeline)
$$\text{Tiếp nhận Dữ liệu} \longrightarrow \text{Ánh xạ Dữ liệu} \longrightarrow \text{Mô hình Chuẩn hóa} \longrightarrow \text{Phân tích Không gian GIS} \longrightarrow \text{Dự báo AI} \longrightarrow \text{Khuyến nghị Vận hành} \longrightarrow \text{Con người Phê duyệt} \longrightarrow \text{Thực thi Công cụ} \longrightarrow \text{Nhật ký Kiểm toán}$$

### Không gian làm việc Kép (Dual Workspaces)
1. **Khối Vận hành Bán lẻ (Retail Operations)**:
   - Quản lý Sản phẩm, Danh mục, Đơn hàng, Khách hàng, Chi nhánh, Doanh thu & chỉ số KPIs.
   - Phân tích kinh doanh không gian GIS (vùng ảnh hưởng chi nhánh, doanh thu theo khu vực, mật độ khách hàng).
   - Dự báo doanh thu và lượng đơn hàng hàng ngày/hàng tuần bằng mô hình XGBoost.
2. **Khối Vận hành Dịch vụ Kỹ thuật CNTT (Service Operations)**:
   - Khách hàng doanh nghiệp, Dịch vụ kỹ thuật (Cài đặt hệ thống, Bảo trì hệ thống, Tư vấn CSDL, Sửa chữa thiết bị), Phiếu Yêu cầu, Công việc, Lịch trình điều phối, Giám sát cam kết SLA.
   - Phân tích vận hành GIS (vị trí khách hàng/kỹ sư, điều phối theo bán kính, truy vấn kỹ sư gần nhất).
   - Phân tích tải công việc và đưa ra khuyến nghị điều phối nhân sự tối ưu.

---

## 🛠️ 2. Ngăn xếp Công nghệ (Technology Stack)

| Tầng | Công nghệ | Vai trò & Mục đích |
|---|---|---|
| **Backend** | Python 3.12+, Django 6.0, Django REST Framework | Nền tảng web, ORM, REST API, RBAC, Tầng dịch vụ nghiệp vụ |
| **Cơ sở dữ liệu** | PostgreSQL 18, PostGIS 3.6, pgvector | Lưu trữ quan hệ cốt lõi, hình học không gian, vector embeddings |
| **Không gian / GIS** | GeoDjango, PostGIS, Leaflet.js | Truy vấn nhận biết vị trí địa lý, tìm kiếm theo khoảng cách/bán kính, hiển thị bản đồ |
| **Học máy (ML)** | XGBoost, pandas, NumPy, scikit-learn | Dự báo chuỗi thời gian dạng bảng, kỹ thuật đặc trưng (feature engineering) |
| **AI & Truy xuất** | RAG, LLM API, Vector Embeddings | Hỏi đáp có căn cứ trên tài liệu quy trình chuẩn (SOP), định tuyến công cụ có kiểm soát |
| **Frontend** | Django Templates, Vanilla HTML/CSS/JS, Chart.js | Giao diện tối ưu chế độ Dark mode, trực quan hóa biểu đồ và bản đồ tương tác |
| **Đóng gói ứng dụng**| Docker, Docker Compose | Môi trường triển khai chuẩn hóa và có thể tái lập |

---

## 📁 3. Cấu trúc Thư mục Dự án

```text
ai_business_platform/
├── manage.py                # Kịch bản quản trị dòng lệnh Django
├── config/                  # Cài đặt cốt lõi, định tuyến URL, WSGI/ASGI, kiểm tra sức khỏe
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                    # Các ứng dụng Django nghiệp vụ dạng mô-đun
│   ├── accounts/            # Quản lý người dùng, vai trò, phân quyền RBAC
│   ├── workspaces/          # Bộ chuyển đổi không gian làm việc kép (Bán lẻ & Dịch vụ)
│   ├── retail/              # Bán lẻ, sản phẩm, đơn hàng, khách hàng
│   ├── service_ops/         # Phiếu dịch vụ, công việc kỹ thuật, kỹ sư, SLA
│   ├── gis/                 # Mô hình không gian, truy vấn GeoDjango, giao diện Leaflet
│   ├── integration/         # Động cơ tiếp nhận dữ liệu CSV/Excel/Mock API vào staging
│   ├── mapping/             # Động cơ ánh xạ dữ liệu & Mô hình Chuẩn hóa (SDM)
│   ├── knowledge/           # Tiếp nhận tài liệu, phân đoạn (chunks), embeddings, pgvector
│   ├── ai_assistant/        # Trợ lý AI chat, mẫu prompt, định nghĩa công cụ kiểm soát
│   ├── forecasting/         # Đường ống XGBoost, tạo đặc trưng, huấn luyện & đánh giá
│   ├── recommendations/     # Động cơ quy tắc kinh doanh xác định, khuyến nghị vận hành
│   ├── approvals/           # Quy trình phê duyệt có con người kiểm duyệt (Human-in-the-loop)
│   └── audit/               # Nhật ký kiểm toán bất biến cho hành động người dùng & AI
├── templates/               # Giao diện HTML Django Templates (Việt hóa 100%)
├── static/                  # Hệ thống thiết kế CSS thuần, JavaScript & biểu tượng
├── ml_models/               # Tệp mô hình huấn luyện đã tuần tự hóa (.pkl/.json)
├── tests/                   # Bộ kiểm thử tự động (Unit, Integration, Smoke tests)
├── docs/                    # Tài liệu kiến trúc, sơ đồ ERD, hướng dẫn demo & bảo vệ
├── requirements.txt         # Danh sách thư viện Python phụ thuộc
├── Dockerfile               # Tệp cấu hình Docker image
├── docker-compose.yml       # Điều phối đa container (Web + PostGIS DB)
├── PROJECT_STATUS.md        # Bảng theo dõi tiến độ các giai đoạn & cổng nghiệm thu
├── AGENT_MASTER_SPEC.md     # Tài liệu đặc tả kỹ thuật chuẩn nguồn (Single Source of Truth)
└── .env.example             # Mẫu cấu hình biến môi trường
```

---

## 🚀 4. Hướng dẫn Khởi động Nhanh

### Yêu cầu Tiên quyết
- Python 3.12+ (Đã kiểm thử hoạt động tốt trên Python 3.14)
- PostgreSQL 18 kèm tiện ích mở rộng PostGIS đã được cài đặt
- Git

### Cài đặt trên Môi trường Cục bộ
1. **Mở thư mục dự án**:
   ```bash
   cd ai_business_platform
   ```

2. **Cấu hình Biến môi trường**:
   ```bash
   cp .env.example .env
   # Cập nhật thông tin kết nối CSDL trong tệp .env nếu cần
   ```

3. **Cài đặt Thư viện Phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Áp dụng Migration vào Cơ sở dữ liệu**:
   ```bash
   python manage.py migrate
   ```

5. **Khởi tạo Dữ liệu Mẫu (Demo Workspaces & Users)**:
   ```bash
   python manage.py seed_demo
   ```
   *Lệnh này khởi tạo 2 không gian làm việc (`Cửa hàng Bán lẻ ABC`, `Công ty Dịch vụ Kỹ thuật XYZ`), 4 vai trò chuẩn (`Quản trị viên`, `Quản lý`, `Nhân viên`, `Người xem`), cùng các tài khoản mẫu (`admin`, `manager`, `employee`, `viewer`).*

6. **Chạy Bộ Kiểm thử Tự động**:
   ```bash
   python manage.py test
   ```

7. **Khởi chạy Máy chủ Phát triển (Development Server)**:
   ```bash
   python manage.py runserver
   ```
   * Trang Trạng thái & Sức khỏe Nền tảng: `http://127.0.0.1:8000/`
   * Bảng điều khiển Bán lẻ (Retail): `http://127.0.0.1:8000/retail/`
   * Bản đồ Không gian GIS Bán lẻ: `http://127.0.0.1:8000/retail/gis/`
   * Danh mục Sản phẩm: `http://127.0.0.1:8000/retail/products/`
   * Quản lý Đơn hàng: `http://127.0.0.1:8000/retail/orders/`
   * Danh bạ Khách hàng: `http://127.0.0.1:8000/retail/customers/`
   * Chi nhánh Cửa hàng: `http://127.0.0.1:8000/retail/branches/`
   * Bảng điều khiển Dịch vụ Kỹ thuật: `http://127.0.0.1:8000/services/`
   * Bản đồ Điều phối GIS Dịch vụ: `http://127.0.0.1:8000/services/gis/`
   * Phiếu Yêu cầu Dịch vụ: `http://127.0.0.1:8000/services/requests/`
   * Bảng Công việc Kỹ thuật: `http://127.0.0.1:8000/services/tasks/`
   * Danh bạ Kỹ sư Hiện trường: `http://127.0.0.1:8000/services/employees/`
   * Lịch trình Điều phối: `http://127.0.0.1:8000/services/schedules/`
   * Chính sách Cam kết SLA: `http://127.0.0.1:8000/services/slas/`
   * Bảng điều khiển Tích hợp Dữ liệu: `http://127.0.0.1:8000/integration/`
   * Danh mục Nguồn Dữ liệu: `http://127.0.0.1:8000/integration/sources/`
   * Trình Hướng dẫn Nhập Dữ liệu: `http://127.0.0.1:8000/integration/import/`
   * Lịch sử Các Lô Nhập: `http://127.0.0.1:8000/integration/jobs/`
   * Xưởng Ánh xạ Dữ liệu (Mapping Studio): `http://127.0.0.1:8000/mapping/`
   * Quản lý Cơ sở Tri thức: `http://127.0.0.1:8000/knowledge/`
   * Trợ lý Trò chuyện AI Assistant: `http://127.0.0.1:8000/ai/assistant/`
   * Phân tích & Dự báo XGBoost: `http://127.0.0.1:8000/forecasting/`
   * Khuyến nghị Vận hành: `http://127.0.0.1:8000/recommendations/`
   * Trung tâm Phê duyệt: `http://127.0.0.1:8000/approvals/`
   * JSON Health API: `http://127.0.0.1:8000/api/health/`
   * Trang Quản trị Django Admin: `http://127.0.0.1:8000/admin/`

---

### 📚 Bộ Tài liệu Kỹ thuật Đi kèm
Tài liệu hướng dẫn kỹ thuật và vận hành chi tiết được lưu trong thư mục `docs/`:
- [Tổng quan Dự án & Kiến trúc](file:///docs/project-summary.md): Kiến trúc toàn diện từ đầu đến cuối, người dùng mục tiêu và phân tích công nghệ.
- [Ghi chú Bảo vệ Học thuật & Đồ án](file:///docs/academic-defense-notes.md): Bộ câu hỏi & trả lời chuẩn hóa (What, Why, Input, Process, Output, Evaluation, Limitations) cho tất cả công nghệ cốt lõi.
- [Hướng dẫn Bảo vệ & Quản trị AI](file:///docs/ai-defense-guide.md): Phân biệt rõ các khái niệm (RAG vs LLM vs XGBoost vs Business Rules) và cơ chế rào chắn an toàn (guardrails).
- [Kịch bản Trình diễn Trực tiếp (Demo Guide)](file:///docs/demo-guide.md): Hướng dẫn từng bước cho 7 quy trình trình diễn thực tế.
- [Hướng dẫn Cài đặt & Triển khai](file:///docs/installation.md): Thiết lập máy trạm (Cài đặt Cục bộ & Docker) cùng các bước cấu hình.
- [Hướng dẫn Xử lý Sự cố (Troubleshooting)](file:///docs/troubleshooting.md): Quy trình chẩn đoán và khắc phục lỗi cho PostgreSQL, PostGIS, pgvector và đường dẫn DLL.

---

### ⚠️ Tài khoản Thử nghiệm Cục bộ
> [!IMPORTANT]
> **CHỈ SỬ DỤNG CHO MÔI TRƯỜNG PHÁT TRIỂN & KIỂM THỬ**: Các thông tin đăng nhập dưới đây được tạo tự động bởi lệnh `python manage.py seed_demo` nhằm mục đích thử nghiệm cục bộ. **TUYỆT ĐỐI KHÔNG sử dụng thông tin hoặc mật khẩu mặc định này trong môi trường staging hoặc production.**
> 
> Mã xác thực API DRF Token được **sinh động tại thời điểm chạy** (`<generated-at-runtime>`) khi khởi tạo dữ liệu hoặc khi đăng nhập. Người dùng có thể lấy mã token động qua API `POST /api/v1/auth/login/` hoặc xem trong trang Django Admin.

| Tên người dùng | Mật khẩu Cục bộ | Vai trò theo Không gian làm việc | Không gian Mặc định | API Token |
|---|---|---|---|---|
| `admin` | `AdminPass123!` | Quản trị viên (Superuser) tại Bán lẻ & Dịch vụ | Cửa hàng Bán lẻ ABC | `<generated-at-runtime>` |
| `manager` | `ManagerPass123!` | Quản lý tại Bán lẻ, Nhân viên tại Dịch vụ | Cửa hàng Bán lẻ ABC | `<generated-at-runtime>` |
| `employee` | `EmployeePass123!` | Nhân viên tại Bán lẻ, Người xem tại Dịch vụ | Cửa hàng Bán lẻ ABC | `<generated-at-runtime>` |
| `viewer` | `ViewerPass123!` | Người xem tại Bán lẻ & Dịch vụ | Cửa hàng Bán lẻ ABC | `<generated-at-runtime>` |

### Triển khai bằng Docker
```bash
docker-compose up --build
```

---

## 🧪 5. Kiểm thử & Đảm bảo Chất lượng
Chạy toàn bộ bộ kiểm thử tự động bất kỳ lúc nào:
```bash
python manage.py test tests/
```

---

## 📜 6. Nguyên tắc Phát triển & Quản trị Hệ thống
- **Kiểm soát Phạm vi Nghiêm ngặt**: Phiên bản hiện tại giới hạn thuật toán gồm: RAG + XGBoost + Quy tắc Kinh doanh Xác định + Công cụ Kiểm soát (Controlled Tools). Không sử dụng hệ thống multi-agent tự do không kiểm soát hoặc thực thi SQL tùy ý.
- **Có Con người Giám sát (Human-in-the-Loop)**: Tất cả các hành động tác động lớn đến dữ liệu kinh doanh đều bắt buộc kiểm tra quyền hạn, kiểm tra logic quy tắc xác định và được người quản lý phê duyệt rõ ràng.
- **Tính Độc lập của Các Giai đoạn**: Các giai đoạn từ Phase 0 đến Phase 12 được hoàn thành tuần tự và tuân thủ chặt chẽ định nghĩa nghiệm thu (Definition of Done).
