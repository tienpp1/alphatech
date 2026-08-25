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
   - `WorkspaceMembership`: Binds a `User` to a specific `Workspace` with an assigned `Role`. A user may be a `Manager` in *ABC Retail* but only an `Employee` in *XYZ Service*.
3. **Domain Entities (Workspace Scoped)**:
   - All business entities (`Order`, `ServiceRequest`, `Document`, `ForecastModelConfig`) belong directly or hierarchically to a `Workspace`.

### 2.2 Role Hierarchy & Default Privileges
| Role | Retail Workspace Scope | Service Workspace Scope | AI & Governance Scope |
|---|---|---|---|
| **Admin** | Full management of products, orders, customers, mapping rules, data sources. | Full management of services, tickets, tasks, employees, SLAs. | Full AI chat access, prompt management, user management, full audit inspection. |
| **Manager** | View sales analytics/forecasts, approve promotions/transfers, create orders. | View workload, approve technician dispatches, modify SLAs. | Review & Approve/Reject AI recommendations (`ApprovalRequest`). |
| **Employee** | Create orders, view catalog, view assigned store branch. | View assigned tasks, update ticket status, report task completion. | Use AI chat with read-only view on own tasks/orders. |
| **Viewer** | Read-only access to sales reports & dashboards. | Read-only access to service reports & dashboards. | Read-only analytics viewing; no AI tool execution. |

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
