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
| `unit_price` | `decimal` | Precision 12, scale 2, $> 0.00$ | Standard retail selling price |
| `cost_price` | `decimal` | Precision 12, scale 2, $\ge 0.00$ | Unit acquisition / production cost |
| `is_active` | `boolean` | `true` or `false` | Active in catalog indicator |

**Legacy Field Mappings**:
- `ma_sp`, `ma_hang`, `ItemCode` $\to$ `sku`
- `ten_san_pham`, `ten_hang`, `ItemName` $\to$ `name`
- `gia_ban`, `don_gia`, `SalePrice` $\to$ `unit_price`
- `gia_von`, `gia_nhap`, `Cost` $\to$ `cost_price`

---

### 2.3 Canonical `Order` & `Revenue`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `order_number` | `string` | Max 50 chars, unique per workspace | Canonical invoice / receipt ID |
| `customer_id` | `string` | References valid customer | Customer placing the transaction |
| `branch_code` | `string` | References valid branch, nullable | Branch fulfilling the sale |
| `order_date` | `date` | `YYYY-MM-DD` | Transaction calendar date |
| `order_timestamp`| `datetime` | ISO-8601 with timezone | Precise transaction timestamp |
| `revenue` (`total_amount`) | `decimal` | Precision 14, scale 2, $\ge 0.00$ | Gross or net recognized revenue |
| `status` | `enum` | `PENDING`, `COMPLETED`, `CANCELLED` | Order lifecycle status |
| `payment_method`| `enum` | `CASH`, `BANK_TRANSFER`, `CARD`, `WALLET` | Payment channel |

**Legacy Field Mappings**:
- `so_hoa_don`, `ma_don_hang`, `ReceiptNo` $\to$ `order_number`
- `ngay_ban`, `ngay_tao`, `TxnDate` $\to$ `order_date`
- `tong_tien`, `thanh_tien`, `doanh_thu`, `GrossAmount` $\to$ `revenue`
- `trang_thai`, `OrderStatus` $\to$ `status`

---

### 2.4 Canonical `OrderItem`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `order_number` | `string` | References parent order | Associated transaction |
| `sku` | `string` | References product | Product purchased |
| `quantity` | `integer` | Positive integer $> 0$ | Units sold |
| `unit_price` | `decimal` | Precision 12, scale 2 | Price per unit for this line |
| `subtotal` | `decimal` | Calculated: $\text{quantity} \times \text{unit\_price}$ | Line total before discounts |

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

### 2.6 Canonical `ServiceRequest`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `request_number` | `string` | Max 50 chars, unique per workspace | Incident/ticket number |
| `customer_id` | `string` | References valid customer | Requesting client |
| `service_code` | `string` | References catalog service | Service category requested |
| `title` | `string` | Max 255 chars | Short summary of incident |
| `priority` | `enum` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Severity level |
| `status` | `enum` | `NEW`, `SCHEDULED`, `IN_PROGRESS`, `RESOLVED`, `CANCELLED` | Operational status |
| `latitude` | `float` | Valid WGS84 coordinate | Location of on-site service |
| `longitude` | `float` | Valid WGS84 coordinate | Location of on-site service |
| `deadline_at` | `datetime` | ISO-8601 timestamp | Calculated SLA deadline |

**Legacy Field Mappings**:
- `ma_yeu_cau`, `so_phieu`, `TicketID` $\to$ `request_number`
- `muc_do_uu_tien`, `Severity` $\to$ `priority`
- `han_chot`, `DueDate` $\to$ `deadline_at`

---

### 2.7 Canonical `Employee`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `employee_code` | `string` | Max 50 chars, unique per workspace | Technician / staff ID |
| `full_name` | `string` | Max 200 chars | Employee full name |
| `phone` | `string` | Phone format | Direct contact number |
| `skills` | `list[string]` | List of certified skill codes | Competencies for dispatching |
| `latitude` | `float` | Nullable coordinate | Last known GPS latitude |
| `longitude` | `float` | Nullable coordinate | Last known GPS longitude |
| `is_available` | `boolean` | `true` or `false` | Duty availability |

---

### 2.8 Canonical `Task`
| Canonical Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `task_id` | `string/int` | Unique task identifier | Work order task unit |
| `request_number` | `string` | References parent request | Associated service ticket |
| `assigned_employee_code`| `string` | References employee, nullable | Assigned field technician |
| `status` | `enum` | `PENDING`, `ASSIGNED`, `STARTED`, `COMPLETED` | Execution state |
| `estimated_duration` | `integer` | Minutes $> 0$ | Expected labor time |
