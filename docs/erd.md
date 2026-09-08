# Entity-Relationship Specification (ERD)

## 1. Domain Model Architecture & Ownership Hierarchy

The database schema is organized into logical subdomains unified by **PostgreSQL 18** with **PostGIS 3.6** (for spatial geometries) and **pgvector** (for document embeddings).

### 1.1 Ownership & Scoping Strategy

The architecture classifies all database entities into three distinct structural tiers:

```text
+-----------------------------------------------------------------------------------+
|                   TIER 1: GLOBAL PLATFORM ENTITIES (No workspace_id)              |
|   - User                                                                          |
|   - Role                                                                          |
|   - Permission                                                                    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|               TIER 2: TENANCY SCOPING & MEMBERSHIP (Scoping Bridge)               |
|   - Workspace                                                                     |
|   - WorkspaceMembership (Maps User <-> Workspace <-> Role)                        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|          TIER 3: WORKSPACE-SCORED DOMAIN & INTELLIGENCE ENTITIES                  |
|   Direct Workspace FK:                                                            |
|     - Retail: Category, Product, Branch, Customer, Order                          |
|     - Service: Service, Employee, SLA, ServiceRequest                             |
|     - Integration: DataSource, ImportJob, MappingRule                             |
|     - AI / Decision: KnowledgeBase, ForecastModelConfig, BusinessRule,            |
|                      Recommendation, ApprovalRequest                              |
|   Hierarchical Child FK (Inherits tenancy via parent):                            |
|     - OrderItem (via Order), Task (via ServiceRequest), Schedule (via Task)       |
|     - Document (via KnowledgeBase), DocumentChunk (via Document)                  |
|     - ForecastRun (via ForecastModelConfig), ForecastResult (via ForecastRun)     |
|   System / Auditing:                                                              |
|     - Notification (Scoped to Recipient User + optional Workspace)                |
|     - AuditLog (workspace_id is Nullable for global auth vs tenant actions)       |
+-----------------------------------------------------------------------------------+
```

---

## 2. Comprehensive Entity Specifications

### 2.1 Tier 1: Global Identity & Access Control (RBAC)

#### `User` (Django Custom User / Auth User)
- `id` (UUID/BigInt, PK): Unique identifier.
- `username` (CharField(150), Unique, Not Null): Login username.
- `email` (EmailField(254), Unique, Not Null): User email.
- `password` (CharField(128), Not Null): Hashed password string.
- `first_name` (CharField(150), Blank): First name.
- `last_name` (CharField(150), Blank): Last name.
- `is_active` (BooleanField, Default True): Active account status.
- `is_staff` (BooleanField, Default False): Django admin access flag.
- `is_superuser` (BooleanField, Default False): Super administrator flag.
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Note*: **Global Entity (No `workspace_id`)**. A single user can belong to multiple workspaces with different roles.

#### `Role`
- `id` (BigInt, PK)
- `name` (CharField(50), Unique, Not Null): Global role identifier (e.g., `Admin`, `Manager`, `Employee`, `Viewer`).
- `description` (TextField, Blank)
- `created_at` (DateTimeField, auto_now_add=True)
- *Note*: **Global Entity (No `workspace_id`)**.

#### `Permission`
- `id` (BigInt, PK)
- `codename` (CharField(100), Unique, Not Null): E.g., `retail.create_order`, `service.assign_task`, `ai.approve_action`.
- `name` (CharField(255), Not Null): Human-readable permission name.
- `module` (CharField(50), Not Null): Domain module tag (e.g., `retail`, `service_ops`, `ai`, `approvals`).
- *Note*: **Global Entity (No `workspace_id`)**.

---

### 2.2 Tier 2: Tenancy & Membership Scoping

#### `Workspace`
- `id` (UUID, PK, Default=uuid4): Unique tenant/workspace identifier.
- `name` (CharField(100), Not Null): E.g., `ABC Tech Store`, `XYZ IT Technical Services`.
- `code` (SlugField(50), Unique, Not Null): E.g., `abc-retail`, `xyz-service`.
- `workspace_type` (CharField(20), Choices: `RETAIL`, `SERVICE`, Not Null).
- `description` (TextField, Blank).
- `is_active` (BooleanField, Default True).
- `created_at` (DateTimeField, auto_now_add=True).
- `updated_at` (DateTimeField, auto_now=True).

#### `WorkspaceMembership` (User $\leftrightarrow$ Workspace $\leftrightarrow$ Role Scoping Bridge)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `user_id` (FK $\to$ `User`, OnDelete=CASCADE)
- `role_id` (FK $\to$ `Role`, OnDelete=RESTRICT)
- `is_default` (BooleanField, Default False): Indicates default workspace on login.
- `joined_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, user_id)`

---

### 2.3 Tier 3: Retail Domain (Workspace Scoped)

#### `Category`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null)
- `code` (CharField(50), Not Null)
- `parent_id` (FK $\to$ `Category`, Nullable, OnDelete=SET_NULL)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Product`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `category_id` (FK $\to$ `Category`, OnDelete=RESTRICT)
- `sku` (CharField(50), Not Null): Product SKU / barcode.
- `name` (CharField(255), Not Null)
- `description` (TextField, Blank)
- `unit` (CharField(30), Default="cái"): Measurement unit.
- `unit_price` (DecimalField(12, 2), Not Null)
- `cost_price` (DecimalField(12, 2), Default=0.00)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Scope Note*: Commercial sales catalog only. Warehouse stock tracking (`stock_quantity`) is non-core external metadata.
- *Constraint*: `Unique(workspace_id, sku)`

#### `Branch` (Retail Physical Outlet)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): Branch identifier.
- `name` (CharField(200), Not Null): Branch title.
- `address` (CharField(255), Not Null)
- `region` (CharField(100), Not Null): E.g., `District 1, HCMC`, `Ba Dinh, Hanoi`.
- `location` (PointField(srid=4326, spatial_index=True), Not Null): PostGIS coordinates (Longitude, Latitude).
- `phone` (CharField(20), Blank)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Customer`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): Canonical `customer_id`.
- `name` (CharField(200), Not Null)
- `email` (EmailField(254), Blank, Nullable)
- `phone` (CharField(20), Blank)
- `address` (CharField(255), Blank)
- `location` (PointField(srid=4326, spatial_index=True), Nullable): PostGIS coordinate.
- `customer_segment` (CharField(50), Choices: `STANDARD`, `VIP`, `ENTERPRISE`, Default=`STANDARD`).
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Order`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `order_number` (CharField(50), Not Null): Canonical invoice / order identifier.
- `customer_id` (FK $\to$ `Customer`, OnDelete=RESTRICT)
- `branch_id` (FK $\to$ `Branch`, Nullable, OnDelete=SET_NULL)
- `order_date` (DateField, Not Null)
- `order_timestamp` (DateTimeField, Not Null)
- `status` (CharField(30), Choices: `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `COMPLETED`, `CANCELLED`, `REFUNDED`, Default=`COMPLETED`)
- `total_amount` (DecimalField(14, 2), Not Null): Discrete transaction amount physically stored on the order. Realized revenue is the aggregate business metric derived from completed orders (`Sum(total_amount)` where `status != CANCELLED`).
- `subtotal_amount` (DecimalField(14, 2), Default=0.00)
- `tax_amount` (DecimalField(12, 2), Default=0.00)
- `discount_amount` (DecimalField(12, 2), Default=0.00)
- `payment_method` (CharField(50), Choices: `CASH`, `BANK_TRANSFER`, `CREDIT_CARD`, `E_WALLET`)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Constraint*: `Unique(workspace_id, order_number)`

#### `OrderItem` (Child Entity)
- `id` (BigInt, PK)
- `order_id` (FK $\to$ `Order`, OnDelete=CASCADE, RelatedName=`items`): Inherits workspace scope through Order.
- `product_id` (FK $\to$ `Product`, OnDelete=RESTRICT)
- `quantity` (IntegerField, Not Null)
- `unit_price` (DecimalField(12, 2), Not Null)
- `subtotal` (DecimalField(14, 2), Not Null): Computed: `quantity * unit_price`.
- `discount` (DecimalField(12, 2), Default=0.00)

---

### 2.4 Tier 3: Service Operations Domain (Workspace Scoped)

#### `Service` (Catalog of IT & Technical Services)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): Service code.
- `name` (CharField(200), Not Null)
- `category` (CharField(50), Choices: `INSTALLATION`, `MAINTENANCE`, `DATABASE_CONSULTING`, `DEVICE_REPAIR`, Default=`INSTALLATION`)
- `description` (TextField, Blank)
- `standard_duration_minutes` (IntegerField, Default=60)
- `base_fee` (DecimalField(12, 2), Default=0.00)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Employee` (Technical Staff / Field Engineer)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `user_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL): Optional link to login account.
- `code` (CharField(50), Not Null): Staff identifier.
- `full_name` (CharField(200), Not Null)
- `phone` (CharField(20), Blank)
- `skills` (JSONField, Default=list): E.g., `["SERVER", "DATABASE", "NETWORK", "DEVICE_REPAIR"]`.
- `hourly_labor_rate` (DecimalField(12, 2), Default=150000.00): Hourly labor rate in VND.
- `current_location` (PointField(srid=4326, spatial_index=True), Nullable): Last known coordinates.
- `location_updated_at` (DateTimeField, Nullable)
- `is_available` (BooleanField, Default True)
- `current_workload_score` (FloatField, Default=0.0): Deterministic score: `active_tasks + (overdue_tasks * 1.5)`.
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `SLA` (Service Level Agreement)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null): E.g., `Critical Priority SLA (2h/4h)`.
- `priority` (CharField(20), Choices: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `response_time_hours` (IntegerField, Not Null)
- `resolution_time_hours` (IntegerField, Not Null)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, priority)`

#### `ServiceRequest` (Incident Ticket)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `request_number` (CharField(50), Not Null): Unique ticket identifier (`SR-YYYYMMDD-XXXX`).
- `customer_id` (FK $\to$ `Customer`, OnDelete=RESTRICT)
- `service_id` (FK $\to$ `Service`, OnDelete=RESTRICT)
- `sla_id` (FK $\to$ `SLA`, Nullable, OnDelete=SET_NULL)
- `assigned_employee_id` (FK $\to$ `Employee`, Nullable, OnDelete=SET_NULL)
- `title` (CharField(255), Not Null)
- `description` (TextField, Not Null)
- `location` (PointField(srid=4326, spatial_index=True), Nullable): Incident coordinates.
- `priority` (CharField(20), Choices: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, Default=`MEDIUM`)
- `status` (CharField(30), Choices: `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`, `CANCELLED`, Default=`OPEN`)
- `response_deadline_at` (DateTimeField, Nullable)
- `resolution_deadline_at` (DateTimeField, Nullable)
- `responded_at` (DateTimeField, Nullable)
- `resolved_at` (DateTimeField, Nullable)
- `closed_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Constraint*: `Unique(workspace_id, request_number)`

#### `Task` (Child Entity)
- `id` (BigInt, PK)
- `service_request_id` (FK $\to$ `ServiceRequest`, OnDelete=CASCADE, RelatedName=`tasks`): Inherits workspace tenancy via ServiceRequest.
- `assigned_to_id` (FK $\to$ `Employee`, Nullable, OnDelete=SET_NULL)
- `title` (CharField(255), Not Null)
- `status` (CharField(30), Choices: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, Default=`PENDING`)
- `estimated_duration_minutes` (IntegerField, Default=60)
- `actual_duration_minutes` (IntegerField, Nullable)
- `started_at` (DateTimeField, Nullable)
- `completed_at` (DateTimeField, Nullable)
- `due_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)

#### `Schedule` (Child Entity)
- `id` (BigInt, PK)
- `task_id` (FK $\to$ `Task`, OnDelete=CASCADE, RelatedName=`schedules`)
- `employee_id` (FK $\to$ `Employee`, OnDelete=CASCADE, RelatedName=`schedules`)
- `start_time` (DateTimeField, Not Null)
- `end_time` (DateTimeField, Not Null)
- `status` (CharField(20), Choices: `SCHEDULED`, `IN_PROGRESS`, `DONE`, `CANCELLED`, Default=`SCHEDULED`)
- `notes` (TextField, Blank)
- `created_at` (DateTimeField, auto_now_add=True)

#### `LaborEntry` (Child Entity - Labor Time & Realized Cost Tracking)
- `id` (BigInt, PK)
- `task_id` (FK $\to$ `Task`, OnDelete=CASCADE, RelatedName=`labor_entries`): Inherits workspace tenancy via Task $\to$ ServiceRequest.
- `employee_id` (FK $\to$ `Employee`, OnDelete=PROTECT, RelatedName=`labor_entries`)
- `started_at` (DateTimeField, Not Null)
- `ended_at` (DateTimeField, Not Null)
- `duration_minutes` (PositiveIntegerField, Not Null)
- `hourly_rate_snapshot` (DecimalField(12, 2), Not Null): Immutable snapshot of technician hourly rate at entry time.
- `labor_cost` (DecimalField(14, 2), Not Null): Server-calculated: `(duration_minutes / 60) * hourly_rate_snapshot`.
- `notes` (TextField, Blank)
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.5 Tier 3: Ingestion & Mapping Domain (Workspace Scoped)

#### `DataSource`
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null)
- `source_type` (CharField(20), Choices: `CSV`, `EXCEL`, `MOCK_API`, Not Null)
- `connection_config` (JSONField, Default=dict)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)

#### `ImportJob`
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `data_source_id` (FK $\to$ `DataSource`, OnDelete=CASCADE)
- `status` (CharField(20), Choices: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`, Default=`PENDING`)
- `total_rows` (IntegerField, Default=0)
- `processed_rows` (IntegerField, Default=0)
- `error_rows` (IntegerField, Default=0)
- `error_summary` (JSONField, Default=list)
- `uploaded_file` (FileField, Nullable)
- `started_at` (DateTimeField, Nullable)
- `completed_at` (DateTimeField, Nullable)
- `created_by_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)

#### `MappingRule`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `data_source_id` (FK $\to$ `DataSource`, OnDelete=CASCADE)
- `target_model` (CharField(50), Choices: `Order`, `Product`, `Customer`, `ServiceRequest`, Not Null)
- `mapping_definitions` (JSONField, Not Null): Declarative mapping rules.
- `is_active` (BooleanField, Default True)
- `confidence_score` (FloatField, Default=1.0)
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.6 Tier 3: Knowledge Base & RAG Domain

#### `KnowledgeBase` (Workspace Scoped)
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null)
- `description` (TextField, Blank)
- `embedding_model` (CharField(100), Default=`text-embedding-004`): Name of embedding model.
- `embedding_dimension` (IntegerField, Default=768): Dimension derived from model config.
- `created_at` (DateTimeField, auto_now_add=True)

#### `Document` (Child Entity)
- `id` (UUID, PK, Default=uuid4)
- `knowledge_base_id` (FK $\to$ `KnowledgeBase`, OnDelete=CASCADE, RelatedName=`documents`)
- `title` (CharField(255), Not Null)
- `file_path` (FileField, Not Null)
- `file_type` (CharField(20), Choices: `PDF`, `DOCX`, `TXT`, `MARKDOWN`)
- `file_size_bytes` (BigIntegerField, Default=0)
- `total_chunks` (IntegerField, Default=0)
- `status` (CharField(20), Choices: `PENDING`, `INDEXED`, `FAILED`, Default=`PENDING`)
- `created_at` (DateTimeField, auto_now_add=True)

#### `DocumentChunk` (Child Entity with Dynamic Vector Embedding)
- `id` (BigInt, PK)
- `document_id` (FK $\to$ `Document`, OnDelete=CASCADE, RelatedName=`chunks`)
- `chunk_index` (IntegerField, Not Null)
- `content` (TextField, Not Null): Chunked text.
- `token_count` (IntegerField, Default=0)
- `embedding` (VectorField(dim=settings.EMBEDDING_DIMENSION), Nullable): pgvector embedding.
- `metadata` (JSONField, Default=dict): Page number, section header, token bounds.
- *Index*: `HNSW/IVFFlat` vector index using Cosine Distance.

---

### 2.7 Tier 3: AI, Forecasting, Recommendations & Approvals

#### `ForecastModelConfig` (Workspace Scoped)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `target_domain` (CharField(30), Choices: `RETAIL_REVENUE`, `RETAIL_ORDERS`, `SERVICE_REQUESTS`)
- `algorithm` (CharField(50), Default=`XGBoostRegressor`)
- `hyperparameters` (JSONField, Default=dict)
- `feature_set` (JSONField, Default=list)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)

#### `ForecastRun` (Child Entity)
- `id` (UUID, PK, Default=uuid4)
- `model_config_id` (FK $\to$ `ForecastModelConfig`, OnDelete=CASCADE)
- `trained_at` (DateTimeField, auto_now_add=True)
- `train_start_date` (DateField, Not Null)
- `train_end_date` (DateField, Not Null)
- `mae` (FloatField, Not Null)
- `rmse` (FloatField, Not Null)
- `baseline_mae` (FloatField, Not Null)
- `artifact_path` (CharField(255), Not Null)

#### `ForecastResult` (Child Entity)
- `id` (BigInt, PK)
- `forecast_run_id` (FK $\to$ `ForecastRun`, OnDelete=CASCADE, RelatedName=`predictions`)
- `prediction_date` (DateField, Not Null)
- `predicted_value` (DecimalField(14, 2), Not Null)
- `lower_bound` (DecimalField(14, 2), Nullable)
- `upper_bound` (DecimalField(14, 2), Nullable)
- `actual_value` (DecimalField(14, 2), Nullable)

#### `BusinessRule` (Workspace Scoped)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `rule_name` (CharField(100), Not Null)
- `domain` (CharField(30), Choices: `RETAIL`, `SERVICE`, `DISPATCH`, `PRICING`)
- `conditions` (JSONField, Not Null)
- `action_template` (JSONField, Not Null)
- `is_active` (BooleanField, Default True)

#### `Recommendation` (Workspace Scoped)
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `title` (CharField(255), Not Null)
- `domain` (CharField(30), Choices: `RETAIL`, `SERVICE`)
- `rationale` (TextField, Not Null)
- `action_type` (CharField(50), Not Null)
- `action_payload` (JSONField, Not Null)
- `confidence_score` (FloatField, Default=1.0)
- `status` (CharField(30), Choices: `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `EXECUTED`, Default=`PENDING_REVIEW`)
- `created_at` (DateTimeField, auto_now_add=True)

#### `ApprovalRequest` (Workspace Scoped Human-in-the-Loop Barrier)
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `recommendation_id` (FK $\to$ `Recommendation`, Nullable, OnDelete=SET_NULL)
- `requested_by_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `action_type` (CharField(50), Not Null)
- `payload` (JSONField, Not Null)
- `status` (CharField(20), Choices: `PENDING`, `APPROVED`, `REJECTED`, Default=`PENDING`)
- `reviewed_by_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `review_comment` (TextField, Blank)
- `reviewed_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.8 System, Notifications & Auditing

#### `Notification` (Scoped to User + Optional Workspace)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, Nullable, OnDelete=CASCADE)
- `recipient_id` (FK $\to$ `User`, OnDelete=CASCADE, RelatedName=`notifications`)
- `title` (CharField(200), Not Null)
- `message` (TextField, Not Null)
- `level` (CharField(20), Choices: `INFO`, `WARNING`, `CRITICAL`, `SUCCESS`, Default=`INFO`)
- `is_read` (BooleanField, Default False)
- `target_link` (CharField(255), Blank)
- `created_at` (DateTimeField, auto_now_add=True)

#### `AuditLog` (Append-Only Immutable System Trail)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, Nullable, OnDelete=SET_NULL): **Nullable** (Null for global user auth events, populated for tenant business events).
- `actor_user_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `actor_type` (CharField(20), Choices: `USER`, `AI_ASSISTANT`, `SYSTEM_JOB`, Not Null)
- `action` (CharField(100), Not Null): E.g., `USER_LOGIN`, `ORDER_CREATED`, `TOOL_EXECUTED`.
- `entity_type` (CharField(50), Not Null)
- `entity_id` (CharField(50), Not Null)
- `changes` (JSONField, Default=dict)
- `ip_address` (GenericIPAddressField, Nullable)
- `timestamp` (DateTimeField, auto_now_add=True)
- *Constraint*: Immutable; update and delete operations are forbidden.
