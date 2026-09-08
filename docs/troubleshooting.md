# Hướng dẫn Xử lý Sự cố & Khắc phục Sự cố Vận hành
## Các Tình huống Lỗi Thực tế, Quy trình Chẩn đoán & Giải pháp

Tài liệu này cung cấp các bước xử lý sự cố thực tế để giải quyết các vấn đề vận hành và triển khai thực tế gặp phải khi vận hành **Nền tảng Vận hành Doanh nghiệp Thông minh**.

---

## 1. Sự cố Cơ sở Dữ liệu & Tiện ích Không gian (Spatial Extensions)

### 1.1 Từ chối Kết nối PostgreSQL (`OperationalError: could not connect to server`)
- **Triệu chứng**: `psycopg.OperationalError: connection to server at "127.0.0.1", port 5432 failed: Connection refused`.
- **Nguyên nhân gốc rễ**: Dịch vụ cơ sở dữ liệu PostgreSQL đã bị dừng hoặc đang lắng nghe trên một cổng khác.
- **Chẩn đoán & Giải pháp**:
  - **Trên Windows**: Mở `services.msc`, tìm dịch vụ `postgresql-x64-18` (hoặc phiên bản bạn đã cài), nhấp chuột phải và chọn **Start**. Hoặc chạy lệnh trong PowerShell:
    ```powershell
    Start-Service -Name "postgresql-x64-18"
    ```
  - **Trên Linux**: Kiểm tra trạng thái dịch vụ:
    ```bash
    sudo systemctl status postgresql
    sudo systemctl restart postgresql
    ```
  - Kiểm tra xem PostgreSQL có đang mở cổng 5432 hay không:
    ```bash
    netstat -an | grep 5432
    ```

### 1.2 Thiếu Tiện ích mở rộng Không gian PostGIS (`function postgis_version() does not exist`)
- **Triệu chứng**: Lệnh migrate thất bại hoặc các truy vấn không gian báo lỗi do chưa cài PostGIS.
- **Nguyên nhân gốc rễ**: Tiện ích mở rộng `postgis` chưa được kích hoạt trong cơ sở dữ liệu hiện tại.
- **Giải pháp**: Kết nối vào cơ sở dữ liệu qua `psql` hoặc pgAdmin và thực thi câu lệnh:
  ```sql
  \c ai_business_platform_db
  CREATE EXTENSION IF NOT EXISTS postgis;
  SELECT postgis_version();
  ```

### 1.3 Thiếu Tiện ích mở rộng pgvector (`type "vector" does not exist`)
- **Triệu chứng**: Migration của ứng dụng `apps.knowledge` thất bại khi tạo cột `vector(1536)` cho bảng `KnowledgeChunk`.
- **Nguyên nhân gốc rễ**: Tiện ích mở rộng nhị phân `pgvector` chưa được cài đặt trong PostgreSQL hoặc chưa được kích hoạt.
- **Giải pháp**:
  - Cài đặt pgvector vào PostgreSQL (ví dụ qua mã nguồn: `git clone https://github.com/pgvector/pgvector.git && make && make install`).
  - Kích hoạt tiện ích trong cơ sở dữ liệu:
    ```sql
    \c ai_business_platform_db
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

### 1.4 Không tìm thấy thư viện DLL GDAL / GEOS trên Windows (`OSError: [WinError 126] The specified module could not be found`)
- **Triệu chứng**: GeoDjango báo lỗi khi khởi động: `DLL load failed while importing _gdal`.
- **Nguyên nhân gốc rễ**: Hệ điều hành Windows không tìm thấy tệp thư viện `libgdal-35.dll` hoặc `libgeos_c.dll`.
- **Giải pháp**: Trong `config/settings.py`, nền tảng tự động kiểm tra biến môi trường `os.getenv("POSTGRES_BIN_PATH", r"C:\Program Files\PostgreSQL\18\bin")`. Hãy đảm bảo đường dẫn thư mục `bin` của PostgreSQL được chỉ định chính xác trong tệp `.env`:
  ```ini
  POSTGRES_BIN_PATH="C:\Program Files\PostgreSQL\18\bin"
  ```

---

## 2. Sự cố Môi trường & Cấu hình

### 2.1 Xung đột Cổng: Cổng 8000 hoặc 5432 Đang Bị Chiếm dụng
- **Triệu chứng**: `Error: That port is already in use.`
- **Giải pháp**:
  - Chạy Django trên một cổng khác:
    ```bash
    python manage.py runserver 127.0.0.1:8080
    ```
  - Tìm và dừng tiến trình đang chiếm cổng:
    - **Trên Windows**:
      ```powershell
      Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
      Stop-Process -Id <PID> -Force
      ```
    - **Trên Linux / macOS**:
      ```bash
      lsof -i :8000
      kill -9 <PID>
      ```

### 2.2 Thiếu Biến Môi trường trong `.env`
- **Triệu chứng**: Django sử dụng các giá trị mặc định cho môi trường phát triển hoặc phát sinh ngoại lệ `KeyError`.
- **Giải pháp**: Đảm bảo tệp `.env` đã được tạo tại thư mục gốc bằng cách sao chép từ `.env.example`:
  ```bash
  cp .env.example .env
  ```
  Kiểm tra lại các biến `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, và `DB_PORT` sao cho khớp với môi trường của bạn.

---

## 3. Sự cố AI, RAG & Vector Embeddings

### 3.1 Không có Khóa API LLM / Embedding
- **Triệu chứng**: Truy vấn tri thức AI hoặc tiếp nhận tài liệu cảnh báo thiếu API key.
- **Nguyên nhân gốc rễ**: `OPENAI_API_KEY` hoặc `ANTHROPIC_API_KEY` chưa được định nghĩa trong `.env`.
- **Cơ chế Hoạt động & Dự phòng (Fallback)**: Nền tảng được thiết kế với **bộ sinh embedding dự phòng cục bộ có tính xác định (deterministic synthetic fallback)**. Nếu không cung cấp khóa API từ xa trong `.env`, hệ thống sẽ tự động sinh các vector embedding 1536 chiều chuẩn hóa có khả năng tái lập, cho phép kiểm thử, đánh giá và trình diễn ngoại tuyến đầy đủ mà không cần tài khoản API trả phí.

### 3.2 Lỗi Tiếp nhận Tài liệu (Định dạng Tệp Không Hỗ trợ)
- **Triệu chứng**: `ValidationError: Unsupported file format`.
- **Nguyên nhân gốc rễ**: Phần mở rộng của tệp tải lên không phải là `.pdf`, `.docx`, hoặc `.txt`.
- **Giải pháp**: Đảm bảo tệp tài liệu được lưu dưới dạng PDF chuẩn, Microsoft Word (`.docx`), hoặc văn bản thuần (`.txt`). Hệ thống không hỗ trợ các tệp PDF có mật khẩu bảo vệ hoặc mã hóa.

---

## 4. Sự cố Huấn luyện & Dự báo XGBoost

### 4.1 Không Đủ Dữ liệu Lịch sử (`ValueError: Insufficient historical records`)
- **Triệu chứng**: Khi cố gắng huấn luyện mô hình XGBoost, hệ thống báo lỗi không đủ điểm dữ liệu.
- **Nguyên nhân gốc rễ**: Không gian làm việc hiện tại có ít hơn 30 ngày giao dịch lịch sử liên tục.
- **Giải pháp**: Chạy lại lệnh `python manage.py seed_demo` để tạo 90 ngày lịch sử đơn hàng và phiếu yêu cầu mẫu, hoặc nạp tệp CSV doanh số lịch sử thông qua đường ống Tích hợp Dữ liệu.

### 4.2 Chỉ số Sai số MAPE Cao trên Lượng Phiếu Yêu cầu Kỹ thuật
- **Triệu chứng**: Chỉ số đánh giá mô hình XGBoost hiển thị MAPE trên 50% đối với chỉ số `SERVICE_TICKET_VOLUME`.
- **Giải thích Học thuật**: Đây là đặc tính toán học cố hữu của dữ liệu đếm với mẫu số là các số nguyên nhỏ (ví dụ các ngày chỉ có 0 hoặc 1 phiếu yêu cầu). Khi lượng thực tế $y_t = 1$ và dự báo $\hat{y}_t = 1.6$, sai số phần trăm là 60%, mặc dù sai số tuyệt đối chỉ là 0.6 phiếu yêu cầu. Nền tảng tính toán MAPE nghiêm ngặt trên các ngày có giá trị khác 0 và ưu tiên các chỉ số **MAE** (0.94 phiếu) và **RMSE** (1.21 phiếu) để đánh giá vận hành thực tế.

---

## 5. Lệnh Seed Dữ liệu & Phục hồi Trạng thái Demo

### 5.1 Lệnh `seed_demo` Thất bại hoặc Tạo Dữ liệu Không Nhất quán
- **Triệu chứng**: Lệnh `seed_demo` phát sinh `IntegrityError` hoặc dừng giữa chừng.
- **Giải pháp**:
  - Làm mới cấu trúc cơ sở dữ liệu:
    ```bash
    python manage.py migrate --run-syncdb
    python manage.py migrate
    python manage.py seed_demo
    ```
  - Đảm bảo tất cả các kết nối CSDL khác đã được đóng trước khi thiết lập lại bảng.

---

## 6. Xử lý Sự cố Docker

### 6.1 Docker Daemon Không Khả dụng
- **Triệu chứng**: Lệnh `docker-compose up` trả về `Cannot connect to the Docker daemon`.
- **Giải pháp**: Khởi động ứng dụng Docker Desktop trên Windows/macOS hoặc chạy lệnh bật dịch vụ docker trên Linux (`sudo systemctl start docker`). Nếu máy trạm không có Docker, hãy sử dụng **Hướng dẫn Cài đặt Cục bộ** trong `docs/installation.md`.
