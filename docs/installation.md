# Hướng dẫn Cài đặt & Triển khai Hệ thống
## Thiết lập Môi trường, Yêu cầu Hệ thống & Cấu hình

Tài liệu này cung cấp hướng dẫn đầy đủ, chi tiết và có thể tái lập để cài đặt, cấu hình và khởi chạy **Nền tảng Vận hành Doanh nghiệp Thông minh** trên cả máy trạm cục bộ và môi trường container Docker.

---

## 1. Yêu cầu Hệ thống

### Yêu cầu Phần cứng
- **CPU**: Khuyến nghị tối thiểu 4 nhân (kiến trúc x86_64).
- **RAM**: Tối thiểu 8 GB RAM (khuyến nghị 16 GB RAM để xử lý vector embeddings và huấn luyện mô hình XGBoost mượt mà).
- **Ổ đĩa**: Tối thiểu 5 GB dung lượng trống trên ổ SSD.

### Yêu cầu Phần mềm
- **Hệ điều hành**: Windows 11 (64-bit), Ubuntu 22.04/24.04 LTS, hoặc macOS (Sonoma trở lên).
- **Python**: Phiên bản 3.11, 3.12, 3.13, hoặc 3.14.
- **Cơ sở dữ liệu**: PostgreSQL 16 trở lên (khuyến nghị PostgreSQL 18).
- **Tiện ích mở rộng CSDL (Extensions)**:
  - `postgis` (phiên bản 3.3 trở lên)
  - `vector` (pgvector phiên bản 0.5 trở lên)

---

## 2. Lựa chọn A: Cài đặt Cục bộ trên Máy trạm (Khuyến nghị cho Phát triển & Thử nghiệm)

### Bước 1: Nhân bản Repository & Tạo Môi trường Ảo
```bash
# Nhân bản repository
git clone https://github.com/your-org/ai_business_platform.git
cd ai_business_platform

# Tạo môi trường ảo Python venv
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Trên Linux / macOS:
source venv/bin/activate
```

### Bước 2: Cài đặt Thư viện Python Phụ thuộc
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 3: Cài đặt & Thiết lập PostgreSQL, PostGIS & pgvector
Đảm bảo máy chủ PostgreSQL đã được cài đặt và đang chạy cục bộ trên cổng 5432.
Đăng nhập vào PostgreSQL với quyền quản trị viên (superuser) và khởi tạo cơ sở dữ liệu kèm các tiện ích mở rộng:
```sql
CREATE DATABASE ai_business_platform_db;
\c ai_business_platform_db

-- Bật tiện ích mở rộng không gian PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Bật tiện ích mở rộng tìm kiếm tương đồng vector pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Cấu hình Đường dẫn DLL GDAL / GEOS trên Windows
Trên Windows, GeoDjango cần các thư viện liên kết động GDAL và GEOS DLL. Nếu PostgreSQL được cài đặt tại `C:\Program Files\PostgreSQL\18\bin`, nền tảng đã tự động kích hoạt nạp thư mục DLL qua lệnh `os.add_dll_directory` trong `config/settings.py`. Ngoài ra, bạn có thể chỉ định rõ trong tệp `.env`:
```ini
POSTGRES_BIN_PATH="C:\Program Files\PostgreSQL\18\bin"
```

### Bước 4: Cấu hình Biến Môi trường
Sao chép tệp mẫu môi trường để tạo tệp cấu hình `.env`:
```bash
cp .env.example .env
```
Đảm bảo thông tin đăng nhập CSDL trong `.env` khớp với máy chủ PostgreSQL của bạn:
```ini
DEBUG=True
SECRET_KEY=local-dev-insecure-key-change-in-production-2026
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

DB_ENGINE=django.contrib.gis.db.backends.postgis
DB_NAME=ai_business_platform_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432

# Khóa API LLM / Embeddings tùy chọn (Nếu để trống, hệ thống tự động chuyển sang chế độ mô phỏng synthetic fallback an toàn)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### Bước 5: Thực thi Migration & Kiểm tra Toàn vẹn Hệ thống
```bash
# Kiểm tra cấu hình hệ thống
python manage.py check

# Áp dụng tất cả các migrations vào CSDL
python manage.py migrate

# Xác nhận không có migration nào bị thiếu sót
python manage.py makemigrations --check
python manage.py migrate --plan
```

### Bước 6: Khởi tạo Dữ liệu Thử nghiệm Mẫu (Demo Data)
Nạp dữ liệu mẫu đầy đủ gồm: tài khoản người dùng, vai trò, không gian làm việc, chi nhánh, đơn hàng bán lẻ, phiếu yêu cầu kỹ thuật, chính sách SLA, tài liệu cơ sở tri thức và mô hình dự báo XGBoost đã huấn luyện sẵn:
```bash
python manage.py seed_demo
```

### Bước 7: Khởi chạy Máy chủ Phát triển Web
```bash
python manage.py runserver 127.0.0.1:8000
```
Mở trình duyệt và truy cập hệ thống tại: `http://127.0.0.1:8000/`.

---

## 3. Lựa chọn B: Triển khai với Docker & Docker Compose (Tùy chọn)

Docker cung cấp môi trường container cô lập, đóng gói sẵn PostgreSQL, PostGIS, pgvector và ứng dụng Django.

> [!IMPORTANT]
> **Trạng thái Xác thực Môi trường**: Cài đặt Cục bộ trên Máy trạm (Lựa chọn A) trên Windows/Linux với Python 3.14 và PostgreSQL 18 là môi trường chạy chính thức đã được kiểm chứng thực tế và vượt qua toàn bộ 276 bài kiểm thử tự động. Cấu hình Docker Compose (Lựa chọn B) được cung cấp như một tài liệu tham khảo chuẩn hóa.

### Khởi chạy với Docker Compose
```bash
# Xây dựng hình ảnh và khởi động các dịch vụ ở chế độ chạy nền
docker-compose up --build -d

# Kiểm tra trạng thái sức khỏe của các containers
docker-compose ps

# Thực thi migrations CSDL bên trong container web
docker-compose exec web python manage.py migrate

# Khởi tạo dữ liệu mẫu bên trong container web
docker-compose exec web python manage.py seed_demo

# Chạy kiểm thử tự động bên trong container
docker-compose exec web python manage.py test
```
Truy cập ứng dụng tại địa chỉ: `http://localhost:8000/`.

---

## 4. Xác nhận Chất lượng Cài đặt & Bộ Kiểm thử Hồi quy

Chạy toàn bộ bộ kiểm thử tự động (276 bài test) để kiểm chứng tính toàn vẹn của hệ thống:
```bash
python manage.py test
```
Kết quả mong đợi:
```text
Ran 276 tests in ~...s
OK
System check identified no issues (0 silenced).
```
