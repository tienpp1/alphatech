# Entity-Relationship Specification (ERD)

## 1. Domain Model Architecture Overview

The database schema is structured into logical subdomains unified by **PostgreSQL 18** and extended with **PostGIS 3.6** (for spatial geometries) and **pgvector** (for document embeddings).

All domain entities strictly enforce **Workspace Isolation** via a mandatory foreign key to `Workspace`, ensuring strict logical tenancy.

---

## 2. Comprehensive Entity Specifications

### 2.1 Identity & Access Control (RBAC)

#### `User` (Django Custom User / Auth User)
- `id` (UUID/BigInt, PK): Unique identifier.
- `username` (CharField(150), Unique, Not Null): Login username.
- `email` (EmailField(254), Unique, Not Null): User email.
- `password` (CharField(128), Not Null): Hashed password.
- `first_name` (CharField(150), Blank): First name.
- `last_name` (CharField(150), Blank): Last name.
- `is_active` (BooleanField, Default True): Active account indicator.
- `is_staff` (BooleanField, Default False): Django admin access.
- `is_superuser` (BooleanField, Default False): Super administrator.
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)

#### `Role`
- `id` (BigInt, PK)
- `name` (CharField(50), Unique, Not Null): E.g., `Admin`, `Manager`, `Employee`, `Viewer`.
- `description` (TextField, Blank)
- `created_at` (DateTimeField, auto_now_add=True)

#### `Permission`
- `id` (BigInt, PK)
- `codename` (CharField(100), Unique, Not Null): E.g., `retail.create_order`, `service.assign_task`, `ai.approve_action`.
- `name` (CharField(255), Not Null): Human-readable permission name.
- `module` (CharField(50), Not Null): E.g., `retail`, `service_ops`, `ai`, `approvals`.

#### `UserRole` (Through Table with Workspace Scoping)
- `id` (BigInt, PK)
- `user_id` (FK $\to$ `User`, OnDelete=CASCADE)
- `role_id` (FK $\to$ `Role`, OnDelete=CASCADE)
- `workspace_id` (FK $\to$ `Workspace`, Nullable, OnDelete=CASCADE): Scopes role to specific workspace (or null for global platform admin).
- *Constraint*: `Unique(user_id, role_id, workspace_id)`

---

### 2.2 Workspace Domain

#### `Workspace`
- `id` (UUID, PK, Default=uuid4): Unique tenant/workspace identifier.
- `name` (CharField(100), Not Null): E.g., `ABC Retail Store`, `XYZ Field Service`.
- `code` (SlugField(50), Unique, Not Null): E.g., `abc-retail`, `xyz-service`.
- `workspace_type` (CharField(20), Choices: `RETAIL`, `SERVICE`, Not Null).
- `description` (TextField, Blank).
- `is_active` (BooleanField, Default True).
- `created_at` (DateTimeField, auto_now_add=True).
- `updated_at` (DateTimeField, auto_now=True).

#### `WorkspaceMembership`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `user_id` (FK $\to$ `User`, OnDelete=CASCADE)
- `role_id` (FK $\to$ `Role`, OnDelete=RESTRICT)
- `is_default` (BooleanField, Default False)
- `joined_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, user_id)`

---

### 2.3 Retail Domain

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
- `sku` (CharField(50), Not Null): Stock keeping unit / code.
- `name` (CharField(255), Not Null)
- `description` (TextField, Blank)
- `unit_price` (DecimalField(12, 2), Not Null)
- `cost_price` (DecimalField(12, 2), Default=0.00)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Constraint*: `Unique(workspace_id, sku)`

#### `Branch` (Retail Store / Physical Outlet)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): Branch identifier.
- `name` (CharField(200), Not Null): Branch name.
- `address` (CharField(255), Not Null)
- `region` (CharField(100), Not Null): E.g., `District 1, HCMC`, `Ba Dinh, Hanoi`.
- `location` (PointField(srid=4326, spatial_index=True), Not Null): Geographic coordinates (Longitude, Latitude).
- `phone` (CharField(20), Blank)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Customer` (Shared Base Pattern for Retail / Service)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): Canonical `customer_id`.
- `name` (CharField(200), Not Null)
- `email` (EmailField(254), Blank, Nullable)
- `phone` (CharField(20), Blank)
- `address` (CharField(255), Blank)
- `location` (PointField(srid=4326, spatial_index=True), Nullable): Geographic coordinate.
- `customer_segment` (CharField(50), Choices: `STANDARD`, `VIP`, `ENTERPRISE`, Default=`STANDARD`).
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Order`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `order_number` (CharField(50), Not Null): Canonical unique invoice/order code.
- `customer_id` (FK $\to$ `Customer`, OnDelete=RESTRICT)
- `branch_id` (FK $\to$ `Branch`, Nullable, OnDelete=SET_NULL)
- `order_date` (DateField, Not Null)
- `order_timestamp` (DateTimeField, Not Null)
- `status` (CharField(30), Choices: `PENDING`, `COMPLETED`, `CANCELLED`, `REFUNDED`, Default=`COMPLETED`)
- `total_amount` (DecimalField(14, 2), Not Null): Canonical `revenue`.
- `tax_amount` (DecimalField(12, 2), Default=0.00)
- `discount_amount` (DecimalField(12, 2), Default=0.00)
- `payment_method` (CharField(50), Choices: `CASH`, `BANK_TRANSFER`, `CREDIT_CARD`, `E_WALLET`)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Constraint*: `Unique(workspace_id, order_number)`

#### `OrderItem`
- `id` (BigInt, PK)
- `order_id` (FK $\to$ `Order`, OnDelete=CASCADE, RelatedName=`items`)
- `product_id` (FK $\to$ `Product`, OnDelete=RESTRICT)
- `quantity` (IntegerField, Not Null)
- `unit_price` (DecimalField(12, 2), Not Null)
- `subtotal` (DecimalField(14, 2), Not Null): Calculated `quantity * unit_price`.
- `discount` (DecimalField(12, 2), Default=0.00)

---

### 2.4 Service Operations Domain

#### `Service` (Catalog of Offered Services)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `code` (CharField(50), Not Null): E.g., `MAINT_ELEVATOR_01`.
- `name` (CharField(200), Not Null)
- `description` (TextField, Blank)
- `standard_duration_minutes` (IntegerField, Default=60)
- `base_fee` (DecimalField(12, 2), Default=0.00)
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `Employee` (Field Technician / Service Staff)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `user_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `code` (CharField(50), Not Null): Employee ID.
- `full_name` (CharField(200), Not Null)
- `phone` (CharField(20), Not Null)
- `skills` (JSONField, Default=list): E.g., `["HVAC", "Plumbing", "Electrical"]`.
- `current_location` (PointField(srid=4326, spatial_index=True), Nullable): Last known location.
- `location_updated_at` (DateTimeField, Nullable)
- `is_available` (BooleanField, Default True)
- `current_workload_score` (FloatField, Default=0.0): Dynamic score calculated from active tasks.
- `created_at` (DateTimeField, auto_now_add=True)
- *Constraint*: `Unique(workspace_id, code)`

#### `SLA` (Service Level Agreement Definition)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null): E.g., `Standard 24h`, `Critical 2h`.
- `priority` (CharField(20), Choices: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, Unique per workspace)
- `response_time_hours` (IntegerField, Not Null): Time to acknowledge.
- `resolution_time_hours` (IntegerField, Not Null): Time to complete.
- `created_at` (DateTimeField, auto_now_add=True)

#### `ServiceRequest`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `request_number` (CharField(50), Not Null): Unique ticket number.
- `customer_id` (FK $\to$ `Customer`, OnDelete=RESTRICT)
- `service_id` (FK $\to$ `Service`, OnDelete=RESTRICT)
- `sla_id` (FK $\to$ `SLA`, OnDelete=RESTRICT)
- `title` (CharField(255), Not Null)
- `description` (TextField, Not Null)
- `location` (PointField(srid=4326, spatial_index=True), Not Null): Incident/service coordinate.
- `priority` (CharField(20), Choices: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, Default=`MEDIUM`)
- `status` (CharField(30), Choices: `NEW`, `SCHEDULED`, `IN_PROGRESS`, `RESOLVED`, `CANCELLED`, Default=`NEW`)
- `deadline_at` (DateTimeField, Not Null): SLA breach threshold.
- `resolved_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)
- `updated_at` (DateTimeField, auto_now=True)
- *Constraint*: `Unique(workspace_id, request_number)`

#### `Task` (Actionable Work Item Assigned to Employee)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `service_request_id` (FK $\to$ `ServiceRequest`, OnDelete=CASCADE, RelatedName=`tasks`)
- `assigned_to_id` (FK $\to$ `Employee`, Nullable, OnDelete=SET_NULL)
- `title` (CharField(255), Not Null)
- `status` (CharField(30), Choices: `PENDING`, `ASSIGNED`, `STARTED`, `COMPLETED`, `FAILED`, Default=`PENDING`)
- `estimated_duration_minutes` (IntegerField, Default=60)
- `actual_duration_minutes` (IntegerField, Nullable)
- `started_at` (DateTimeField, Nullable)
- `completed_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)

#### `Schedule`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `task_id` (FK $\to$ `Task`, OnDelete=CASCADE)
- `employee_id` (FK $\to$ `Employee`, OnDelete=CASCADE)
- `start_time` (DateTimeField, Not Null)
- `end_time` (DateTimeField, Not Null)
- `status` (CharField(20), Choices: `SCHEDULED`, `IN_PROGRESS`, `DONE`, `CANCELLED`, Default=`SCHEDULED`)
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.5 Data Ingestion & Mapping Domain

#### `DataSource`
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null): E.g., `POS Export CSV`, `CRM Mock API`.
- `source_type` (CharField(20), Choices: `CSV`, `EXCEL`, `MOCK_API`, Not Null)
- `connection_config` (JSONField, Default=dict): Connection metadata or API URL.
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
- `created_by_id` (FK $\to` `User`, Nullable, OnDelete=SET_NULL)

#### `MappingRule`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `data_source_id` (FK $\to$ `DataSource`, OnDelete=CASCADE)
- `target_model` (CharField(50), Choices: `Order`, `Product`, `Customer`, `ServiceRequest`, Not Null)
- `mapping_definitions` (JSONField, Not Null): Field mappings, type casts, value lookups.
- `is_active` (BooleanField, Default True)
- `confidence_score` (FloatField, Default=1.0): Confidence when generated by AI assistant.
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.6 Knowledge Base & RAG Domain

#### `KnowledgeBase`
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `name` (CharField(100), Not Null): E.g., `Retail Operations Manual`, `Service SOPs`.
- `description` (TextField, Blank)
- `created_at` (DateTimeField, auto_now_add=True)

#### `Document`
- `id` (UUID, PK, Default=uuid4)
- `knowledge_base_id` (FK $\to$ `KnowledgeBase`, OnDelete=CASCADE, RelatedName=`documents`)
- `title` (CharField(255), Not Null)
- `file_path` (FileField, Not Null)
- `file_type` (CharField(20), Choices: `PDF`, `DOCX`, `TXT`, `MARKDOWN`)
- `file_size_bytes` (BigIntegerField, Default=0)
- `total_chunks` (IntegerField, Default=0)
- `status` (CharField(20), Choices: `PENDING`, `INDEXED`, `FAILED`, Default=`PENDING`)
- `created_at` (DateTimeField, auto_now_add=True)

#### `DocumentChunk`
- `id` (BigInt, PK)
- `document_id` (FK $\to$ `Document`, OnDelete=CASCADE, RelatedName=`chunks`)
- `chunk_index` (IntegerField, Not Null)
- `content` (TextField, Not Null): Text segment content.
- `token_count` (IntegerField, Default=0)
- `embedding` (VectorField(dim=768 / 1536), Nullable): pgvector representation.
- `metadata` (JSONField, Default=dict): Page number, section header, keywords.
- *Index*: `HNSW/IVFFlat` index on `embedding` with cosine distance.

---

### 2.7 AI, Forecasting, Recommendation & Approvals

#### `ForecastModelConfig`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `target_domain` (CharField(30), Choices: `RETAIL_REVENUE`, `RETAIL_ORDERS`, `SERVICE_REQUESTS`)
- `algorithm` (CharField(50), Default=`XGBoostRegressor`)
- `hyperparameters` (JSONField, Default=dict): `{"max_depth": 6, "n_estimators": 100, "learning_rate": 0.05}`.
- `feature_set` (JSONField, Default=list): `["lag_1", "lag_7", "rolling_mean_7", "day_of_week"]`.
- `is_active` (BooleanField, Default True)
- `created_at` (DateTimeField, auto_now_add=True)

#### `ForecastRun`
- `id` (UUID, PK, Default=uuid4)
- `model_config_id` (FK $\to$ `ForecastModelConfig`, OnDelete=CASCADE)
- `trained_at` (DateTimeField, auto_now_add=True)
- `train_start_date` (DateField, Not Null)
- `train_end_date` (DateField, Not Null)
- `mae` (FloatField, Not Null): Mean Absolute Error.
- `rmse` (FloatField, Not Null): Root Mean Squared Error.
- `baseline_mae` (FloatField, Not Null): Naive baseline MAE comparison.
- `artifact_path` (CharField(255), Not Null): Path to serialized `.pkl` in `ml_models/`.

#### `ForecastResult`
- `id` (BigInt, PK)
- `forecast_run_id` (FK $\to$ `ForecastRun`, OnDelete=CASCADE, RelatedName=`predictions`)
- `prediction_date` (DateField, Not Null)
- `predicted_value` (DecimalField(14, 2), Not Null)
- `lower_bound` (DecimalField(14, 2), Nullable)
- `upper_bound` (DecimalField(14, 2), Nullable)
- `actual_value` (DecimalField(14, 2), Nullable): Populated retrospectively for accuracy tracking.

#### `BusinessRule` (Deterministic Policy Engine)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `rule_name` (CharField(100), Not Null)
- `domain` (CharField(30), Choices: `RETAIL`, `SERVICE`, `DISPATCH`, `PRICING`)
- `conditions` (JSONField, Not Null): Evaluated conditions (e.g. `{"workload_score_max": 80, "distance_km_max": 15}`).
- `action_template` (JSONField, Not Null): Template recommendation payload.
- `is_active` (BooleanField, Default True)

#### `Recommendation`
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `title` (CharField(255), Not Null)
- `domain` (CharField(30), Choices: `RETAIL`, `SERVICE`)
- `rationale` (TextField, Not Null): Explainable justification citing source metrics and rules.
- `action_type` (CharField(50), Not Null): E.g., `DISPATCH_ENGINEER`, `STOCK_TRANSFER`, `APPLY_PROMOTION`.
- `action_payload` (JSONField, Not Null): Concrete parameters for tool execution.
- `confidence_score` (FloatField, Default=1.0)
- `status` (CharField(30), Choices: `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `EXECUTED`, Default=`PENDING_REVIEW`)
- `created_at` (DateTimeField, auto_now_add=True)

#### `ApprovalRequest` (Human-in-the-Loop Barrier)
- `id` (UUID, PK, Default=uuid4)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `recommendation_id` (FK $\to$ `Recommendation`, Nullable, OnDelete=SET_NULL)
- `requested_by_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL): User or AI Assistant.
- `action_type` (CharField(50), Not Null)
- `payload` (JSONField, Not Null)
- `status` (CharField(20), Choices: `PENDING`, `APPROVED`, `REJECTED`, Default=`PENDING`)
- `reviewed_by_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `review_comment` (TextField, Blank)
- `reviewed_at` (DateTimeField, Nullable)
- `created_at` (DateTimeField, auto_now_add=True)

---

### 2.8 System & Audit Domain

#### `Notification`
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, OnDelete=CASCADE)
- `recipient_id` (FK $\to$ `User`, OnDelete=CASCADE, RelatedName=`notifications`)
- `title` (CharField(200), Not Null)
- `message` (TextField, Not Null)
- `level` (CharField(20), Choices: `INFO`, `WARNING`, `CRITICAL`, `SUCCESS`, Default=`INFO`)
- `is_read` (BooleanField, Default False)
- `target_link` (CharField(255), Blank)
- `created_at` (DateTimeField, auto_now_add=True)

#### `AuditLog` (Append-Only Immutable Event Trail)
- `id` (BigInt, PK)
- `workspace_id` (FK $\to$ `Workspace`, Nullable, OnDelete=SET_NULL)
- `actor_user_id` (FK $\to$ `User`, Nullable, OnDelete=SET_NULL)
- `actor_type` (CharField(20), Choices: `USER`, `AI_ASSISTANT`, `SYSTEM_JOB`, Not Null)
- `action` (CharField(100), Not Null): E.g., `ORDER_CREATED`, `TASK_ASSIGNED`, `TOOL_EXECUTED`.
- `entity_type` (CharField(50), Not Null): E.g., `Order`, `Task`, `ApprovalRequest`.
- `entity_id` (CharField(50), Not Null): String representation of the entity PK.
- `changes` (JSONField, Default=dict): Before/after delta payload.
- `ip_address` (GenericIPAddressField, Nullable)
- `timestamp` (DateTimeField, auto_now_add=True)
- *Constraint*: No update or delete operations permitted on `AuditLog`.
