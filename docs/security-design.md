# Security, Authentication & Role-Based Access Control (RBAC) Design

## 1. Authentication Strategy

To balance developer velocity, simplicity, and rock-solid security for a V1 modular monolith, authentication is organized into two well-defined channels:

```text
+-----------------------------------------------------------------------------------+
|                            AUTHENTICATION CHANNELS                                |
+-----------------------------------------------------------------------------------+
|  1. Django Web UI Channel (Primary):                                              |
|     - Django Session Authentication (Cookies, HttpOnly, SameSite=Lax, CSRF Guard) |
|     - Simple, proven, eliminates client-side token storage vulnerabilities.        |
|                                                                                   |
|  2. Django REST Framework (DRF) API Channel:                                     |
|     - Session Authentication for browser-based interactive UI & AJAX requests.    |
|     - DRF Token Authentication (rest_framework.authtoken) for external/scripted   |
|       programmatic API clients via header: Authorization: Token <key>.            |
|     - JWT is evaluated as an optional enterprise extension; avoided in V1 to      |
|       eliminate token refresh/revocation state complexity.                        |
+-----------------------------------------------------------------------------------+
```

---

## 2. Global Identity vs Workspace-Scoped Access (RBAC)

The security model separates global platform accounts from tenant-specific permissions:

### 2.1 Three-Tier Entity Security Model
1. **Global Entities (System Scope)**:
   - `User`, `Role`, `Permission`: These exist globally across the platform. A `Role` defines a bundle of permissions; a `User` holds credentials.
2. **Scoping Bridge (Tenancy Scope)**:
   - `WorkspaceMembership`: Binds a `User` to a specific `Workspace` with an assigned `Role`. A user may be a `Manager` in *ABC Tech Store* but only an `Employee` in *XYZ IT Technical Services*.
3. **Domain Entities (Workspace Scoped)**:
   - All business entities (`Order`, `ServiceRequest`, `Document`, `ForecastModelConfig`) belong directly or hierarchically to a `Workspace`.

### 2.2 Role Hierarchy & Default Privileges
| Role | Retail Workspace Scope | Service Workspace Scope | GIS & Spatial Scope | AI & Governance Scope |
|---|---|---|---|---|
| **Admin** | Full management of products, orders, customers, mapping rules, data sources. | Full management of services, tickets, tasks, employees, SLAs. | Full GIS map access + Unmasked customer locations & contact details (`gis.view_customer_locations`). | Full AI chat access, prompt management, user management, full audit inspection. |
| **Manager** | View sales analytics/forecasts, approve promotions/transfers, create orders. | View workload, approve technician dispatches, modify SLAs. | Full GIS map access + Unmasked customer locations (`gis.view_customer_locations`). | Review & Approve/Reject AI recommendations (`ApprovalRequest`). |
| **Employee** | Create orders, view catalog, view assigned store branch. | View assigned tasks, update ticket status, report task completion. | View spatial map layers (`gis.view_spatial_layers`); masked customer PII. | Use AI chat with read-only view on own tasks/orders. |
| **Viewer** | Read-only access to sales reports & dashboards. | Read-only access to service reports & dashboards. | Read-only spatial analytics; masked customer PII. | Read-only analytics viewing; no AI tool execution. |

---

## 3. Workspace Tenancy & Data Isolation Rules

### Invariant: Strict Logical Tenancy
Business queries are strictly filtered by the active `workspace_id`. Cross-workspace data leakage is prevented at both the ORM and View layer.

```python
# Custom QuerySet / Manager for Workspace Isolation
class WorkspaceScopedManager(models.Manager):
    def for_workspace(self, workspace):
        return self.get_queryset().filter(workspace=workspace)
```

### Security Enforcement in DRF
```python
class WorkspacePermission(permissions.BasePermission):
    """Ensures request user has active membership in the target workspace."""
    def has_permission(self, request, view):
        workspace_id = request.headers.get("X-Workspace-ID") or request.session.get("active_workspace_id")
        if not workspace_id:
            return False
        return WorkspaceMembership.objects.filter(
            workspace_id=workspace_id,
            user=request.user
        ).exists()
```

---

## 4. AI Security Guardrails & Agent Safety Invariants

### 4.1 Strict RBAC Inheritance
- When a user interacts with the AI Assistant, **the AI operates strictly within the authenticated user's permission boundary**.
- The AI cannot see data or trigger tools that the authenticated caller cannot access directly.

### 4.2 Zero Raw SQL Execution
- LLMs are **strictly prohibited** from generating, interpolating, or executing raw SQL strings.
- All database interactions are mediated by strongly typed Python service functions using parameterized Django ORM queries.

### 4.3 Multi-Stage Tool Calling & Approval Pipeline
Every AI tool invocation adheres to a strict multi-tier verification process:

$$\text{LLM Intent} \longrightarrow \text{Tool Selection} \longrightarrow \text{RBAC Check} \longrightarrow \text{Business Rule Check} \longrightarrow \text{Approval Barrier} \longrightarrow \text{Execution} \longrightarrow \text{Audit Log}$$

1. **Read-Only Tools** (`read_sales_summary`, `query_nearby_technicians`): Execute immediately if caller has read permission.
2. **Mutating Tools** (`dispatch_technician`, `update_order_status`, `apply_promotional_rule`):
   - Immediately create an `ApprovalRequest` record with `status=PENDING`.
   - The AI Assistant informs the user: *"Yêu cầu đã được tạo và đang chờ Quản lý phê duyệt."*
   - Only a user with `Manager` or `Admin` role can transition the `ApprovalRequest` to `APPROVED`, which then triggers the underlying execution service.

### 4.4 Immutable Audit Logging
- Every tool execution, approval decision, login event, and data import produces an append-only entry in `AuditLog`.
- `AuditLog` rows cannot be updated or deleted via the application layer.

---

## 5. Spatial Data Privacy & Location Governance (Phase 5)

Customer geographic coordinates and physical addresses represent sensitive personal and commercial data. The platform enforces strict spatial access boundaries:

1. **Customer Location Masking**:
   - Callers with read-only/operational viewer roles (`gis.view_spatial_layers`) receive masked customer names (`Customer <CODE>`) and generic address indicators (`Restricted (Address Protected)`).
   - Sensitive contact details (phone, email) are omitted entirely from GeoJSON properties.
2. **Elevated Location Access**:
   - Access to unmasked customer spatial coordinates and full PII requires explicit possession of `gis.view_customer_locations` or `retail.manage_customer` permission, restricted to `Admin` and `Manager` roles.
3. **Workspace Boundary on Spatial Queries**:
   - PostGIS spatial radius and bounding box searches automatically inject workspace tenant boundaries (`WHERE workspace_id = ...`). Cross-workspace entity matching is physically prevented at the database query level.

---

## 6. Data Integration & Ingestion Security Guardrails (Phase 6)

External file imports and mock API integrations introduce untrusted payloads into the system. The platform enforces strict ingestion boundaries:

1. **Strict Logical Tenancy on Ingestion Models**:
   - `DataSource`, `ImportJob`, and `RawImportRecord` are strictly workspace-scoped with foreign keys to `Workspace` and `WorkspaceScopedManager`.
   - Cross-workspace file access or querying is blocked at the manager and DRF view layer.
2. **Dedicated RBAC Permissions**:
   - `integration.view_datasource`: Read-only access to data source configurations and historical import job telemetry.
   - `integration.manage_datasource`: Ability to register, edit, or delete data sources (restricted to `Admin` and `Manager` roles).
   - `integration.execute_import`: Ability to upload files and trigger batch ingestion jobs (granted to `Admin`, `Manager`, and `Employee`).
3. **Upload Safety & Resource Caps**:
   - Maximum upload file size capped at 10 MB.
   - File extensions validated against `.csv`, `.xlsx`, `.xls`.
   - Multi-encoding fallback with encoding sanitization (`utf-8-sig`, `utf-8`, `latin-1`).
4. **Isolated Raw Staging (Zero Domain Pollution)**:
   - External records are stored in `RawImportRecord.raw_data` as untrusted JSON objects.
   - External fields are NEVER directly inserted into canonical business tables (`Order`, `Customer`, `Product`, `ServiceRequest`) during Phase 6 ingestion. Domain insertion is strictly gated behind Phase 7 Data Mapping.
5. **Immutable Audit Trail for Ingestion**:
   - Every data source creation/update and every import lifecycle transition (`IMPORT_STARTED`, `IMPORT_COMPLETED`, `IMPORT_PARTIAL`, `IMPORT_FAILED`) creates an immutable `AuditLog` entry detailing row counts, success rates, and user identity.
6. **Remote API & SSRF Defense Architecture**:
   - **Scheme Restriction**: Only `http://` and `https://` are permitted for remote endpoints; local mock endpoints must use `/` relative paths (scheme-relative `//` is blocked).
   - **SSRF Blocklist & DNS Resolution**: Hostnames and IP literals are validated prior to connection. Loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), link-local (`169.254.0.0/16`, `fe80::/10`), cloud metadata (`169.254.169.254`, `metadata.google.internal`, `instance-data`, `metadata.azure.com`), CGNAT (`100.64.0.0/10`), and internal domain suffixes (`.local`, `.internal`, `.corp`, `.lan`, `.home`, `.arpa`) are resolved and rejected.
   - **Safe Redirect Interception**: `SafeRedirectHandler` validates every redirected URL against the SSRF policy and limits max redirects to 3.
   - **Response Size & Timeout Limits**: Maximum response payload is capped at 5 MB read in chunks; timeouts are clamped to a maximum of 15 seconds.
7. **Credential Privacy & Upload Sanitization**:
   - **Credential Masking**: `DataSourceSerializer` automatically masks sensitive connection keys (`password`, `token`, `secret`, `api_key`, `auth`) with asterisks.
   - **Filename Traversal Protection**: Uploaded file names are strictly sanitized using `get_valid_filename(os.path.basename(...))` to prevent path traversal.
   - **Disallowed Executable Formats**: All non-tabular formats (`.exe`, `.py`, `.sh`, `.php`, `.js`) are rejected before execution.

---

## 7. Data Mapping & Transformation Security Guardrails (Phase 7)

Transforming external inputs into canonical domain records introduces formula injection and privilege escalation risks. The platform enforces strict mapping guardrails:

1. **AST-Based Formula Evaluation (Zero `eval()` / `exec()`)**:
   - Business formulas are evaluated exclusively through a dedicated Abstract Syntax Tree (AST) parser (`apps.mapping.engine.safe_evaluator`).
   - Only safe binary operators (`+`, `-`, `*`, `/`) and string concatenation are whitelisted.
   - Any function calls (`Call`), attribute lookups (`Attribute`), subscripts (`Subscript`), lambdas (`Lambda`), or imports (`Import`) immediately trigger `SecurityValidationError`.
2. **Mandatory Human-in-the-Loop Approval for AI Recommendations**:
   - AI-assisted schema suggestions operate strictly in recommendation mode (`ai_status = PENDING_CONFIRMATION`).
   - Recommendations NEVER automatically mutate the database or activate rules. An authorized human manager must explicitly click `Accept` or `Reject`.
3. **Workspace Isolation on Mapping Profiles & Rules**:
   - `MappingProfile` and `MappingRule` extend `WorkspaceScopedModel`.
   - Cross-workspace profile inspection, modification, or rule application is rejected at the manager and DRF permission layer.
4. **Dedicated Mapping RBAC Permissions**:
   - `mapping.view_mapping`: View mapping profiles, rules, field discoveries, and simulation previews.
   - `mapping.manage_mapping`: Create, edit, and configure mapping profiles and rules (Manager & Admin).
   - `mapping.apply_mapping`: Trigger atomic canonical domain ingestion (Manager, Admin, Employee).
5. **Transactional Domain Persistence with Immutable Auditing**:
   - Domain insertion operations (`POST /api/v1/mapping/apply/`) execute inside `transaction.atomic()` blocks.
   - Every profile creation, rule modification, AI approval/rejection, and domain import batch creates an immutable append-only `AuditLog` entry.


