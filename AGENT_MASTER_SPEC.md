# Intelligent Business Operations Platform
## PROJECT MASTER SPECIFICATION & AGENT PLAYBOOK
**Single Source of Truth for Architecture, Scope, and Implementation**

---

### 0. MỤC ĐÍCH CỦA TÀI LIỆU
Tài liệu này hợp nhất các quyết định đã chốt cho đồ án và chuyển chúng thành một “nguồn sự thật duy nhất” (single source of truth) cho các AI coding agents.
- Nền tảng quản lý vận hành doanh nghiệp tích hợp AI, không phải hệ thống quản lý kho chuyên sâu và không phải chatbot đơn thuần.
- Hiểu phạm vi V1 phải hoàn thành trong học kỳ và phân biệt rõ với kiến trúc sản phẩm tương lai.
- Biết kiến trúc, module, database, API, AI pipeline, GIS, quy tắc bảo mật và thứ tự triển khai.
- Không tự ý thêm framework, microservice hoặc thuật toán làm tăng độ phức tạp khi chưa có lý do kỹ thuật.
- Mọi tính năng mới phải quay về bài toán nghiệp vụ, kiểm thử được và giải thích được khi bảo vệ.

---

### 1. ĐỊNH DANH VÀ TẦM NHÌN DỰ ÁN
- **Tên đề tài**: Xây dựng nền tảng quản lý vận hành doanh nghiệp thông minh tích hợp AI hỗ trợ phân tích, dự báo và ra quyết định.
- **Tên tiếng Anh**: Intelligent Business Operations Platform with AI-Powered Analytics, Forecasting and Decision Support.
- **Identity cốt lõi**:
  $$\text{Data} \to \text{Integration} \to \text{Data Mapping} \to \text{Standard Data Model} \to \text{GIS/Knowledge} \to \text{AI Intelligence} \to \text{Recommendation} \to \text{Human Approval} \to \text{Tool Action} \to \text{Audit}$$

Trong học kỳ, hệ thống được minh họa bằng hai workspace: **Retail** và **Service**.

---

### 2. PHẠM VI CỨNG CỦA V1 - SCOPE LOCK

| Vùng | V1 bắt buộc | Không làm trong V1 |
|---|---|---|
| **Business** | Retail + Service trên 1 platform | Không xây 2 sản phẩm độc lập |
| **AI** | RAG + LLM, XGBoost, Recommendation/Rules, Tool Calling | Không triển khai Isolation Forest, Hungarian, Multi-Agent |
| **GIS** | GeoDjango + PostGIS + bản đồ + spatial query + business analytics | Không làm raster/viễn thám/routing engine phức tạp |
| **Integration** | CSV/Excel + API giả lập + Data Mapping | Không tích hợp SAP/Salesforce/ERP thương mại thật |
| **Architecture** | Django modular monolith | Không microservices nhiều tầng |
| **Deployment** | Local/Docker phục vụ demo | Không production multi-region/private-cloud hoàn chỉnh |
| **AI action** | Tool + permission + human approval | Không cho AI tự do sửa/xóa dữ liệu |

---

### 3. BÀI TOÁN NGHIỆP VỤ

#### 3.1 Retail - Trọng tâm Sales và Customer (Không phải Kho)
- Products / Categories
- Orders / Order Items
- Customers
- Employees
- Branches / Locations
- Revenue / KPI
- GIS theo chi nhánh/khu vực
- AI hỏi đáp và dự báo doanh thu / số đơn

#### 3.2 Service - Trọng tâm Workflow và Không gian
- Customers
- Services
- Service Requests
- Tasks
- Employees
- Schedules
- SLA
- Customer / employee locations
- GIS service coverage
- AI hỗ trợ phân tích workload và workflow

---

### 4. KIẾN TRÚC TỔNG THỂ V1
```text
Browser / Web UI
       ↓
Django + Django REST Framework
├── Authentication + RBAC
├── Business Modules (Retail & Service)
├── Workflow + Approval
├── Data Integration + Mapping
├── GIS (GeoDjango)
├── AI Assistant + RAG
├── Forecasting (XGBoost)
└── Tool Calling + Audit
       ↓
PostgreSQL + PostGIS + pgvector
       ↓
LLM API / Python ML libraries
```

---

### 5. TRÌNH TỰ TRIỂN KHAI TỐI ƯU (PHASES)

- **Phase 0**: Khởi tạo repo, xác nhận Python/Django/PostgreSQL/Docker, tạo docs/AGENTS.md, cấu trúc project, Git, smoke tests.
- **Phase 1**: Kiến trúc + ERD, chốt models, relations, API conventions, workspace scope.
- **Phase 2**: Django Core, settings, accounts, RBAC, workspace, common utilities, migrations.
- **Phase 3**: Retail (Products, orders, customers, branches, revenue dashboard).
- **Phase 4**: Service (Customers, services, requests, tasks, schedules, SLA).
- **Phase 5**: GIS (GeoDjango/PostGIS, location models, map API, Leaflet dashboard, spatial query).
- **Phase 6**: Data Integration (CSV/Excel importer + API giả lập + ImportJob).
- **Phase 7**: Data Mapping (MappingRule, transformations, validation, standard model).
- **Phase 8**: RAG (Document upload, parsing, chunking, embedding, pgvector retrieval, answer grounding).
- **Phase 9**: XGBoost (Dataset, feature engineering, baseline, training, evaluation, prediction API).
- **Phase 10**: Recommendation + Tools (Business rules, recommendation, safe tool calling, approval flow).
- **Phase 11**: Testing + Hardening (Unit/integration/system/permission tests, bug fixing, audit, performance).
- **Phase 12**: Demo + Docs (Seed data, demo scripts Retail/Service/GIS/RAG/Forecast, architecture docs, report).

---

### 6. QUY TẮC BẮT BUỘC CHO MỌI AGENT
1. Đọc tài liệu này và docs hiện có trước khi sửa code.
2. Luôn xác định phase hiện tại và không tự nhảy sang phase sau nếu phase hiện tại chưa đạt gate.
3. Không tự ý thêm framework, microservice, thuật toán hoặc dependency lớn.
4. Không đổi tên model/API/public interface nếu không có lý do migration rõ ràng.
5. Sau khi sửa: chạy formatter/lint/test phù hợp và kiểm tra migration.
6. Nếu test fail, ưu tiên sửa nguyên nhân thay vì bỏ qua hoặc làm test yếu đi.
7. Không commit secret / API key.
8. Không hard-code demo data vào business logic.
9. Không cho AI sinh SQL tùy ý để truy cập database trong production path; dùng tool/service được định nghĩa.
10. Mọi thay đổi AI có side effect phải đi qua permission + validation + approval + audit khi cần.
