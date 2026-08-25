# Security & Role-Based Access Control (RBAC) Design

## 1. Authentication Strategy

The platform employs a dual-channel authentication strategy:
1. **Web UI Channel**: Standard secure Django Session Authentication with CSRF protection (`SameSite=Lax`, `HttpOnly`, `Secure` in production).
2. **API Client Channel**: Standard Token / JWT Authentication with Bearer header verification (`Authorization: Bearer <token>`).

---

## 2. Granular Role-Based Access Control (RBAC)

User privileges are determined by an explicit matrix of **Roles** and **Permissions** scoped per **Workspace**.

### 2.1 Role Hierarchy & Default Privileges
| Role | Retail Workspace Scope | Service Workspace Scope | AI & System Scope |
|---|---|---|---|
| **Admin** | Full read/write on products, orders, customers, mapping rules, data sources. | Full read/write on services, tickets, tasks, employees, SLAs. | Full access to AI chat, prompt configs, user management, audit logs. |
| **Manager** | View sales KPI/forecasts, approve stock transfers, create orders. | View workload, approve technician dispatches, modify SLAs. | Review & Approve/Reject AI recommendations (`ApprovalRequest`). |
| **Employee** | Create orders, view catalog, view assigned store branch. | View assigned tasks, update ticket status, report completion. | Use AI chat with read-only view on own tasks/orders. |
| **Viewer** | Read-only access to sales reports. | Read-only access to service dashboards. | Read-only analytics viewing; no AI tool execution. |

---

## 3. Workspace Tenancy & Data Isolation Rules

### Invariant: Strict Logical Tenancy
Every business entity is tied to a specific `Workspace`. Users can belong to multiple workspaces with different roles (e.g. `Manager` in Retail, `Employee` in Service).

```python
# Standard Model QuerySet Filter Pattern
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
- If an `Employee` asks: *"Hiển thị toàn bộ lương của nhân viên khác"*, the tool executor rejects the request at the service layer because the caller lacks the required permission.

### 4.2 Zero Arbitrary SQL Execution
- LLMs are **strictly prohibited** from generating, interpolating, or executing raw SQL strings.
- All data retrieval happens via strongly typed Python service tools with parameterized ORM filters.

### 4.3 Human-in-the-Loop Mutation Barrier
- Any tool invocation with side-effects (e.g., assigning a technician, cancelling an order, creating a promotion) automatically generates an `ApprovalRequest` record with `status=PENDING`.
- High-risk changes cannot be committed to the database until a user with the `Manager` or `Admin` role explicitly approves the request via the approval interface.

### 4.4 Immutable Audit Logging
- Every tool execution, approval decision, login event, and data import is logged to `AuditLog` with actor ID, timestamp, IP address, and JSON before/after state diffs.
- `AuditLog` rows cannot be updated or deleted via the application layer.
