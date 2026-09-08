# Standard Data Model (Canonical Domain Contracts)

## 1. Motivation & Purpose

Enterprises and SMEs ingest data from diverse legacy systems: old POS software, spreadsheets, ERP exports, and third-party CRMs. In the wild, column headers vary wildly (`tong_tien`, `DoanhThu`, `total`, `amount_paid`, `ma_kh`, `CustomerID`, `client_id`).

### The Core Problem
If business analytics, GIS queries, ML forecasting pipelines, and RAG prompts depend directly on arbitrary external column names, the platform becomes brittle, unmaintainable, and impossible to scale across different clients.

### The Solution: The Standard Data Model (SDM)
The **Standard Data Model** acts as the universal canonical language of the platform. External data is never consumed raw by domain modules; it is translated through the **Data Mapping Engine** into canonical SDM entities before entering the database.

$$\text{Messy External Data (CSV/Excel/API)} \xrightarrow{\text{Data Mapping Engine}} \mathbf{Standard\ Data\ Model} \xrightarrow{\text{Validated Insertion}} \text{Platform Business \& AI}$$

---

## 2. Canonical Entity Definitions

### 2.1 Canonical `Customer`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `customer_id` (`code`) | `string` | Max 50 chars, unique per workspace | Unique customer reference identifier |
| `name` | `string` | Max 200 chars, not empty | Full customer or business name |
| `email` | `string (email)` | Valid email format, nullable | Primary email contact |
| `phone` | `string` | E.164 or cleaned numeric format | Phone number |
| `address` | `string` | Max 255 chars | Street address |
| `latitude` | `float` | $-90.0 \le \text{lat} \le 90.0$, nullable | WGS84 Latitude coordinate |
| `longitude` | `float` | $-180.0 \le \text{lon} \le 180.0$, nullable | WGS84 Longitude coordinate |
| `segment` | `enum` | `STANDARD`, `VIP`, `ENTERPRISE` | Customer tier |

**Legacy Field Mappings**:
- `ma_kh`, `id_khach_hang`, `CustID` $\to$ `customer_id`
- `ten_khach_hang`, `ho_ten`, `CustomerName` $\to$ `name`
- `sdt`, `dien_thoai`, `Telephone` $\to$ `phone`
- `dia_chi`, `street_address` $\to$ `address`
- `vi_do`, `lat` $\to$ `latitude`
- `kinh_do`, `lng`, `lon` $\to$ `longitude`

---

### 2.2 Canonical `Product`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `sku` | `string` | Max 50 chars, unique per workspace | Stock keeping unit / product barcode |
| `name` | `string` | Max 255 chars, not empty | Product title / description |
| `category_code` | `string` | References standard category | Category identifier |
| `unit` | `string` | Measurement unit, default `cái` | Unit of measure (`cái`, `chai`, `hộp`, etc.) |
| `unit_price` | `decimal` | Precision 12, scale 2, $> 0.00$ | Standard retail selling price |
| `cost_price` | `decimal` | Precision 12, scale 2, $\ge 0.00$ | Unit acquisition / production cost |
| `stock_quantity` | `integer` | Optional non-core external metadata | Supplier stock metadata (non-core) |
| `is_active` | `boolean` | `true` or `false` | Active in catalog indicator |

> [!NOTE]
> **Domain Scope**: The platform is an intelligent business operations and sales analytics system, **NOT** an inventory or warehouse management system (WMS). Inventory tracking workflows, bin allocations, and warehouse stock levels are outside the core business domain. External feeds providing stock levels (`stock_quantity`, `so_luong_ton`) are classified as optional non-core data. The canonical Retail domain remains strictly centered on `Product`, `Category`, `Customer`, `Branch`, `Order`, `OrderItem`, and sales/revenue analytics.

**Legacy Field Mappings**:
- `ma_sp`, `ma_hang`, `ItemCode` $\to$ `sku`
- `ten_san_pham`, `ten_hang`, `ItemName` $\to$ `name`
- `gia_ban`, `don_gia`, `SalePrice` $\to$ `unit_price`
- `gia_von`, `gia_nhap`, `Cost` $\to$ `cost_price`
- `so_luong_ton`, `ton_kho` $\to$ `stock_quantity` (optional non-core)

---

### 2.3 Canonical `Order` & `Revenue`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `order_number` | `string` | Max 50 chars, unique per workspace | Canonical invoice / receipt ID |
| `customer_id` | `string` | References valid customer | Customer placing the transaction |
| `branch_code` | `string` | References valid branch, nullable | Branch fulfilling the sale |
| `order_date` | `date` | `YYYY-MM-DD` | Transaction calendar date |
| `order_timestamp`| `datetime` | ISO-8601 with timezone | Precise transaction timestamp |
| `total_amount` | `decimal` | Precision 14, scale 2, $\ge 0.00$ | Transaction amount stored on the order |
| `revenue` | `decimal` | Precision 14, scale 2, $\ge 0.00$ | Canonical alias mapping directly to `total_amount` |
| `discount_amount`| `decimal` | Precision 12, scale 2, default 0.00 | Order-level discount deduction |
| `tax_amount` | `decimal` | Precision 12, scale 2, default 0.00 | Order tax / VAT amount |
| `status` | `enum` | `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `COMPLETED`, `CANCELLED`, `REFUNDED` | Order lifecycle status |
| `payment_method`| `enum` | `CASH`, `BANK_TRANSFER`, `CREDIT_CARD`, `E_WALLET` | Payment channel |

> [!IMPORTANT]
> **Order Money Semantics**:
> - `Order.total_amount`: The discrete transaction monetary amount physically stored on each order record.
> - `Revenue`: A business analytics metric derived from valid/completed orders (`qs.exclude(status=OrderStatus.CANCELLED).aggregate(Sum("total_amount"))`), **not** an independent duplicated transactional value unless explicitly required by an external source schema.
> - In data mapping, incoming monetary transaction fields (`tong_tien`, `thanh_tien`, `tong_thanh_toan`, `doanh_thu`, `total_amount`) populate `Order.total_amount` directly.

**Legacy Field Mappings**:
- `so_hoa_don`, `ma_don_hang`, `ReceiptNo` $\to$ `order_number`
- `ngay_ban`, `ngay_tao`, `TxnDate` $\to$ `order_date`
- `tong_tien`, `thanh_tien`, `tong_thanh_toan`, `GrossAmount` $\to$ `total_amount`
- `doanh_thu`, `sales_revenue` $\to$ `revenue` (maps to `total_amount`)
- `trang_thai`, `OrderStatus` $\to$ `status`

---

### 2.4 Canonical `OrderItem`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `order_number` | `string` | References parent order | Associated transaction |
| `sku` | `string` | References product | Product purchased |
| `quantity` | `integer` | Positive integer $> 0$ | Units sold |
| `unit_price` | `decimal` | Precision 12, scale 2 | Price per unit for this line |
| `discount` | `decimal` | Precision 12, scale 2, default 0.00 | Line-level discount |
| `subtotal` | `decimal` | Calculated: $\text{quantity} \times \text{unit\_price} - \text{discount}$ | Line total |

---

### 2.5 Canonical `Branch` / `Location`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `branch_code` | `string` | Max 50 chars, unique per workspace | Branch/store code |
| `name` | `string` | Max 200 chars | Name of branch/store |
| `region` | `string` | Max 100 chars | Administrative or sales territory |
| `latitude` | `float` | $-90.0 \le \text{lat} \le 90.0$ | Latitude coordinate |
| `longitude` | `float` | $-180.0 \le \text{lon} \le 180.0$ | Longitude coordinate |

---

### 2.6 Canonical `Service`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `code` | `string` | Max 50 chars, unique per workspace | Standardized service identifier |
| `name` | `string` | Max 200 chars, not empty | Service title |
| `category` | `enum` | `INSTALLATION`, `MAINTENANCE`, `DATABASE_CONSULTING`, `DEVICE_REPAIR` | Approved IT / technical service category |
| `standard_duration_minutes` | `integer` | Minutes $> 0$, default 60 | Baseline labor duration |
| `base_fee` | `decimal` | Precision 12, scale 2, $\ge 0.00$ | Standard service baseline fee |
| `is_active` | `boolean` | `true` or `false` | Active in catalog indicator |

> [!NOTE]
> **Approved Service Categories**: The approved Service domain categories are strictly:
> 1. `INSTALLATION` (System Installation & Hardening)
> 2. `MAINTENANCE` (System Maintenance & Audit)
> 3. `DATABASE_CONSULTING` (Database Design & Optimization)
> 4. `DEVICE_REPAIR` (Hardware Diagnostics & Repair)
> Stale categories such as `INSPECTION` have been removed and are strictly prohibited.

---

### 2.7 Canonical `ServiceRequest` (Incident Ticket)
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `request_number` | `string` | Max 50 chars, unique per workspace | Incident/ticket number (`SR-YYYYMMDD-XXXX`) |
| `customer_id` | `string` | References valid customer | Requesting client |
| `service_code` | `string` | References catalog service | Service category requested |
| `title` | `string` | Max 255 chars | Short summary of incident |
| `priority` | `enum` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Severity level |
| `status` | `enum` | `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`, `CANCELLED` | Operational status |
| `latitude` | `float` | Valid WGS84 coordinate | Location of on-site service |
| `longitude` | `float` | Valid WGS84 coordinate | Location of on-site service |
| `response_deadline_at` | `datetime` | ISO-8601 timestamp | Calculated SLA first-response deadline |
| `resolution_deadline_at` | `datetime` | ISO-8601 timestamp | Calculated SLA resolution deadline |

**Legacy Field Mappings**:
- `ma_yeu_cau`, `so_phieu`, `TicketID` $\to$ `request_number`
- `muc_do_uu_tien`, `Severity` $\to$ `priority`
- `han_chot`, `DueDate` $\to$ `resolution_deadline_at`

---

### 2.8 Canonical `Employee` (Technical Staff)
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `employee_code` | `string` | Max 50 chars, unique per workspace | Technician / staff ID |
| `full_name` | `string` | Max 200 chars | Employee full name |
| `phone` | `string` | Phone format | Direct contact number |
| `skills` | `list[string]` | List of certified skill codes | Competencies for dispatching (`SERVER`, `DATABASE`, etc.) |
| `hourly_labor_rate` | `decimal` | Precision 12, scale 2, $\ge 0.00$ | Standard technician hourly labor rate in VND |
| `latitude` | `float` | Nullable coordinate | Last known GPS latitude |
| `longitude` | `float` | Nullable coordinate | Last known GPS longitude |
| `is_available` | `boolean` | `true` or `false` | Duty availability |
| `current_workload_score`| `float` | Deterministic $\ge 0.0$ | `active_tasks + (overdue_tasks * 1.5)` |

---

### 2.9 Canonical `Task`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `task_id` | `string/int` | Unique task identifier | Work order task unit |
| `request_number` | `string` | References parent request | Associated service ticket |
| `assigned_employee_code`| `string` | References employee, nullable | Assigned field technician |
| `status` | `enum` | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Execution state |
| `estimated_duration` | `integer` | Minutes $> 0$ | Expected labor time |
| `actual_duration` | `integer` | Minutes, nullable | Realized labor execution time |

---

### 2.10 Canonical `LaborEntry` (Labor Time & Cost Realization)
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `entry_id` | `string/int` | Unique labor record identifier | Discrete labor log item |
| `task_id` | `string/int` | References parent task | Associated work item |
| `employee_code` | `string` | References employee | Technician executing the work |
| `started_at` | `datetime` | ISO-8601 timestamp | Work commencement timestamp |
| `ended_at` | `datetime` | ISO-8601 timestamp, $> \text{started\_at}$ | Work completion timestamp |
| `duration_minutes` | `integer` | Positive integer $> 0$ | Duration in minutes |
| `hourly_rate_snapshot` | `decimal` | Precision 12, scale 2 | Immutable hourly rate at log time |
| `labor_cost` | `decimal` | Server calculated | $(\text{duration\_minutes} / 60) \times \text{hourly\_rate\_snapshot}$ |

---

## 3. Implementation in `apps.mapping`

The Standard Data Model contracts are implemented as python ontology contracts in `apps.mapping.canonical`:
- `CANONICAL_MODELS`: Defines target entities, field specifications, data types, required constraints, choice options, and common Vietnamese/English aliases for automated discovery.
- `validate_canonical_record()`: Enforces data type sanitization, required fields, choices, coordinate ranges, and active workspace foreign key resolution prior to domain insertion.
- `MappingProfile` & `MappingRule`: Stores workspace-scoped transformation pipelines.
- `apply_mapping_to_domain()`: Atomically commits validated canonical records into underlying domain tables (`apps.retail` and `apps.service_ops`).

