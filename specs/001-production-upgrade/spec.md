# Feature Specification: Production Upgrade Baseline

**Feature Branch**: `001-production-upgrade`
**Created**: 2026-09-06
**Status**: In progress
**Input**: Complete the eight approved production-upgrade steps without weakening workspace isolation, RBAC, public/customer separation, or known AI failure transparency.

## User Scenarios & Testing

### User Story 1 - Safe customer identity and transaction ownership (Priority: P1)

An authenticated customer has an explicit workspace-local customer profile and sees only orders, contacts, and delivery data they own. Guests may submit data but may not claim an existing account profile using contact fields.

**Why this priority**: Identity and IDOR errors can expose customer data and undermine every later feature.

**Independent Test**: Create two users and guest records with matching email/name; verify profile creation, checkout, contact submission, and order-success access remain isolated.

**Acceptance Scenarios**:
1. Given an authenticated user, when checkout creates a profile, then the profile has a database user relation unique per workspace.
2. Given a guest submits another user's email, when a contact or order is created, then a new unowned record is created and the existing profile is not reused.
3. Given a user requests another user's order number, then the response is 404 and reveals no object existence.

### User Story 2 - Durable product-demand forecasting (Priority: P1)

An operator can submit a forecast job and a worker can safely recover, retry, cancel, and complete it after web-process or worker restart. Demand can be scoped to SKU/product, category, and branch.

**Why this priority**: Forecasts are operational decisions and must not disappear or publish stale results.

**Independent Test**: Enqueue a job, claim it, expire its lease, recover it with a new token, cancel a running job, and verify bounded retries and dimensional data isolation.

### User Story 3 - Explainable recommendation approvals (Priority: P1)

An operator can accept only a validated recommendation action that creates an idempotent approval request; a separate authorized reviewer can execute it once with audit evidence.

**Why this priority**: AI must not directly mutate business state or create duplicate actions.

**Independent Test**: Replay the same approval concurrently, alter parameters under the same idempotency key, reject then replay, and verify no duplicate or unauthorized mutation occurs.

### User Story 4 - Grounded AI demonstrations and canonical tests (Priority: P2)

AI answers for the flagged branch and technician candidate scenarios are derived from canonical records and retain truthful fallback behavior. Stale enterprise benchmark fixtures are reconciled to current models or explicitly recorded as blocked.

**Independent Test**: Run phase-10 scenarios and the enterprise benchmark separately, recording exact pass/fail causes without weakening assertions.

### User Story 5 - Delivery and production readiness (Priority: P2)

Maintainers can run CI gates against PostgreSQL/PostGIS, migrations, security checks, observability and release checklists. Production acceptance requires external evidence for secret rotation, HTTPS OAuth, inbox delivery, CSP/secure cookies, and restore verification.

**Independent Test**: Run local CI gates and execute a staging checklist; mark external checks blocked when evidence or deployment access is unavailable.

## Edge Cases

- Conflicting or expired worker leases must never publish results.
- A cancelled job must not be retried or completed.
- Duplicate approval keys with different payloads must be rejected.
- Cross-workspace product/category/branch dimensions must return validation failure.
- A contact submitted before a workspace is configured must remain safely unassigned.
- SMTP, OAuth, staging, and inbox failures must be reported as blocked/failed, never as success.

## Requirements

### Functional Requirements

- **FR-001**: System MUST store an explicit nullable User relation on Customer and enforce at most one profile per user/workspace.
- **FR-002**: System MUST persist contact submissions and immutable checkout delivery snapshots without using submitted email as account ownership proof.
- **FR-003**: System MUST authorize order history and success pages by authenticated creator/owner or guest session only.
- **FR-004**: System MUST persist asynchronous forecast jobs and support lease, heartbeat, bounded retry, timeout, cancellation, and restart recovery.
- **FR-005**: System MUST validate product, category, and branch dimensions against the active workspace before dataset aggregation.
- **FR-006**: System MUST record chronological holdout/backtest metrics and expose a read-only drift signal without inventing missing actuals.
- **FR-007**: System MUST enforce database uniqueness for workspace approval idempotency keys and serialize state transitions.
- **FR-008**: System MUST keep mutation actions behind validated contracts, human approval, separation of duties, and audit logging.
- **FR-009**: System MUST produce grounded branch and technician demonstration answers from canonical data and preserve explicit known failures.
- **FR-010**: System MUST provide CI checks for PostgreSQL/PostGIS, Django checks, migration drift, and focused regression suites.
- **FR-011**: System MUST document production acceptance evidence and refuse to claim completion when external gates are unverified.
- **FR-012**: System MUST preserve Vietnamese customer UI, workspace isolation, seeded RBAC, public/internal separation, and existing AI failure transparency.

### Key Entities

- **CustomerAccountProfile**: workspace-local link between a User and Customer.
- **ContactSubmission**: immutable public contact event with optional workspace/user ownership.
- **OrderDeliveryAddress**: immutable order-time delivery snapshot.
- **ForecastRun**: durable forecast job state, parameters, lease, retry and metrics.
- **ApprovalRequest**: idempotent, reviewed mutation intent and execution result.
- **AuditLog**: append-only operational evidence; database-level immutability remains a production task.

## Success Criteria

- **SC-001**: Identity, approval, queue, dimensional dataset and regression tests pass with zero focused failures.
- **SC-002**: A recovered forecast worker cannot publish results using an expired lease token.
- **SC-003**: No authenticated user can retrieve a cross-user order through success, history, or detail URLs.
- **SC-004**: CI runs Django check, migration drift and PostgreSQL/PostGIS focused tests on every pull request.
- **SC-005**: Every production gate is marked VERIFIED with evidence or BLOCKED with the exact missing external action.

## Assumptions and Out of Scope

- Existing Django/PostgreSQL/PostGIS, RBAC, email outbox, approval registry, and XGBoost architecture are reused.
- Celery/Redis is not required if the database-backed worker meets durable lifecycle requirements.
- No database reset, public API schema redesign, OAuth provider change, or new role is introduced.
- Production secret rotation, deployment, inbox access, monitoring account setup, and restore drills require operator access and cannot be fabricated by local code tests.
