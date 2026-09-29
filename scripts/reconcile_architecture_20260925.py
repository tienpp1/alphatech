"""Replace invented diagram fields/steps with source-backed contracts."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md'
t = p.read_text(encoding='utf-8')
start, end = t.index('### 2.2'), t.index('### 2.3')
contract = ROOT / 'output/model_contract_20260925_v2'
section = ['### 2.2 ERD theo model hiện hành', '',
    'Bản ERD viết tay trước đây có field không tồn tại (ví dụ `quantity_reserved`) và đã được thay bằng sơ đồ trích xuất từ ORM. Đây là schema khai báo, không chứng minh database deploy đã chạy migration.', '',
    'Nguồn máy đọc đầy đủ 48 model, field, null, unique, on_delete, constraint: `output/model_contract_20260925_v2/model_contract.json`. Danh mục route/view: `routes.json` cùng thư mục. Script tái xuất: `scripts/export_model_contract.py <thư-mục-mới>`.', '',
    'Các sơ đồ theo module bên dưới không liệt kê chi tiết constraint tổ hợp/điều kiện; phải đọc JSON kèm theo. Quan hệ giữa module không có nghĩa được phép truy vấn chéo workspace.', '']
for diagram in sorted(contract.glob('*.mmd')):
    section += ['#### ' + diagram.stem, '', '```mermaid', diagram.read_text(encoding='utf-8'), '```', '']
t = t[:start] + '\n'.join(section) + '\n' + t[end:]
start, end = t.index('#### Sơ đồ 1:'), t.index('#### Sơ đồ 3:')
t = t[:start] + '''#### Sơ đồ 1: Nhánh giao hàng strict

Nguồn: `apps/public_web/fulfillment.py::allocate_home_delivery_stock` và checkout
trong `apps/public_web/views.py`. Đây là nhánh strict opt-in, không đại diện mọi
checkout. Hàm trừ `quantity_on_hand`, không tăng field `quantity_reserved`.
Thứ tự khóa giảm một nguồn deadlock, không chứng minh loại bỏ mọi deadlock.

```mermaid
sequenceDiagram
    actor Customer as Khách hàng
    participant View as Checkout
    participant Allocate as allocate_home_delivery_stock
    participant DB as PostgreSQL
    Customer->>View: POST giỏ hàng và thông tin nhận hàng
    View->>Allocate: Workspace và các dòng đã chọn
    Allocate->>Allocate: Kiểm số lượng và tọa độ tùy chọn
    Allocate->>DB: Atomic; khóa Product, Branch, StockBalance theo thứ tự
    Allocate->>Allocate: Chọn một chi nhánh đủ toàn bộ giỏ hàng
    alt Không đủ hoặc dữ liệu không hợp lệ
        Allocate-->>View: FulfillmentError; không giữ cập nhật dở dang
        View-->>Customer: Thông báo thiếu hàng/lỗi cấu hình
    else Đủ hàng
        Allocate->>DB: Trừ quantity_on_hand từng dòng
        Allocate-->>View: Chi nhánh thực hiện
        View->>DB: Lưu đơn/items/snapshot trong giao dịch checkout
        Note over View,DB: Email delivery sau commit; lỗi email không đổi thành đơn thất bại
        View-->>Customer: Kết quả nghiệp vụ và trạng thái gửi email
    end
```

#### Sơ đồ 2: Dịch vụ và phân công theo quyền

Nguồn: `apps/service_ops/services.py::create_service_request`,
`assign_service_request`, `create_task`, `apps/gis/services.py`.
Tra cứu GIS và phân công là các thao tác riêng; tạo phiếu không mặc nhiên gọi GIS.
Phân công tạo hoặc cập nhật task chính đang hoạt động và tính lại tải nhân viên.
Truy vấn khoảng cách dùng spheroid, không phải road routing.

```mermaid
sequenceDiagram
    actor Staff as Nhân viên có quyền
    participant API as Service UI/API
    participant Svc as Service operations
    participant GIS as GIS selector
    participant DB as PostgreSQL/PostGIS
    Staff->>API: Tạo yêu cầu dịch vụ
    API->>Svc: Workspace, user, dữ liệu đã kiểm
    Svc->>DB: Lưu phiếu và deadline theo SLA nếu có
    API-->>Staff: Phiếu đã tạo
    opt Tra cứu vị trí riêng
        Staff->>GIS: Vị trí và bộ lọc trong workspace có quyền
        GIS->>DB: Distance/radius trên spheroid WGS84
        GIS-->>Staff: Các ứng viên và khoảng cách địa lý
    end
    Staff->>API: Chọn nhân viên để phân công
    API->>Svc: assign_service_request sau kiểm quyền
    Svc->>DB: Kiểm cùng workspace và nhân viên active; cập nhật phiếu
    Svc->>DB: Tạo hoặc cập nhật task chính; tính lại workload; ghi audit
    opt Tạo task bằng thao tác tương ứng
        API->>Svc: create_task
        Svc->>DB: Lưu task theo phiếu được phép
    end
```

''' + t[end:]
start, end = t.index('#### Sơ đồ 4:'), t.index('## PHẦN 3:')
t = t[:start] + '''#### Sơ đồ 4: Bản tin và chat polling

Nguồn: `apps/notifications/bulletin_service.py`, `chat_service.py`,
`bulletin_edit_views.py`, `views.py`, `ui_views.py`. Không có WebSocket hay
tự tăng `views_count` khi đọc danh sách trong các service đã rà soát.

```mermaid
sequenceDiagram
    actor Manager as ADMIN/MANAGER đang hoạt động
    actor Member as Thành viên workspace
    participant UI as UI/API cộng tác
    participant Svc as Bulletin/chat services
    participant DB as PostgreSQL
    Manager->>UI: Đăng hoặc cập nhật bản tin
    UI->>UI: Kiểm quyền workspace
    UI->>Svc: Tạo hoặc update_bulletin
    Svc->>DB: Lưu dữ liệu theo workspace
    Note over Svc,DB: Update khóa bản tin; chỉ title/content/priority/updated_at
    Member->>UI: Đọc bản tin
    UI->>Svc: Chọn bản tin published, ưu tiên pinned còn hiệu lực
    Svc-->>Member: Danh sách theo workspace
    Member->>UI: POST chat/send
    UI->>Svc: send_team_message
    Svc->>Svc: Active membership hoặc superuser
    Svc->>DB: Lưu message
    loop Polling 3 giây ở trình duyệt
        Member->>UI: GET chat/messages với since_id
        UI->>Svc: Lấy tin mới trong workspace
        Svc-->>Member: Danh sách tin nhắn
    end
```

**Giới hạn UI phát hiện 25/09:** lựa workspace không hợp lệ ở màn hình chat/bản tin
còn fallback; sửa và test riêng trước khi coi contract chọn workspace đã đạt.
Ma trận use case chi tiết: ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md.

---

''' + t[end:]
p.write_text(t, encoding='utf-8')
