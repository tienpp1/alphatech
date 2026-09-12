# AI Business Platform — canonical project context

Last verified against source: 2026-09-06  
Authority: current source code and migrations. Historical phase documents are secondary and may be stale.

Public branch directory update (2026-09-11): `/chi-nhanh/` retains its active RETAIL branch visibility contract and sends only public directory fields to browser JSON. Leaflet/OSM renders the map; browser-only opt-in location/manual origin is not persisted. Explicit public-place address queries POST to a CSRF-protected Django endpoint backed by switchable, HTTPS-only Nominatim with shared PostgreSQL rate gate and cache; road-distance/routing requests go to OSRM, and navigation may be handed off to Google Maps. Radius is Haversine distance, distinct from road distance. Device GPS is supplied by browser Geolocation, not OSM. These public providers are best-effort, not a production SLA; address-search live verification is currently blocked by external timeout. No membership or internal GIS permissions are granted by these tools.

Customer approval celebration (2026-09-12): notification signals create a deduplicated public customer event on `Order PENDING→CONFIRMED` and `ServiceRequest OPEN→ASSIGNED/IN_PROGRESS`. The public shell fetches only the authenticated user's unread, currently owned events; acknowledgement is CSRF-protected. Animation runs only in the browser and respects `prefers-reduced-motion`.

## 1. Project purpose and stack

This Django modular monolith serves two domains: **ABC Tech Store** (retail catalog, customers, branches, sales, suppliers, receiving, stock and analytics) and **XYZ IT Technical Services** (service catalog, technicians, tickets, assignments, schedules, SLA and labor cost). Shared capabilities include PostGIS, ingestion/mapping, RAG/assistant, XGBoost forecasts, recommendations, controlled approvals, notifications and audit.

Stack: Python; Django with a custom User; Django REST Framework session/token authentication; PostgreSQL/PostGIS; pgvector-compatible dynamic embeddings; pandas/NumPy/scikit-learn/XGBoost; pypdf/python-docx; Django templates with vanilla JS/CSS, Leaflet-oriented GeoJSON and Chart.js payloads. Dependency ranges are broad (`Django>=5.2,<7.0`), so check runtime versions when relevant.

## 2. Architecture and directories

The request path is generally view → service/selector → ORM model. `config/` owns settings/root routing/health/unified dashboard. `apps.accounts` and `apps.workspaces` own identity, custom RBAC and tenancy. `apps.retail` and `apps.service_ops` own canonical business state. `apps.gis`, `apps.forecasting` and `apps.recommendations` derive analysis. `apps.integration` stages input and `apps.mapping` creates canonical records. `apps.knowledge` owns documents, RAG, conversations, intent routing, business tools and the assistant—there is no live `apps.ai` or `apps.ai_assistant`. `apps.approvals` and `apps.audit` govern mutation/audit. `apps.public_web` and `apps.notifications` own the customer site and internal events.

Other key directories: `templates/public/` is customer-facing; other template folders are internal/legacy UI. `data/synthetic_external/` contains sample feeds. `ml_models/forecasting/` contains trusted XGBoost JSON artifacts. `tests/` has 607 discovered test methods. `.specify/` contains workflow artifacts, not runtime code.

## 3. Capability status

| Capability | Actual state |
|---|---|
| Retail and service operations | Implemented; Service server-rendered reads and mutations now enforce workspace RBAC. |
| Public website/e-commerce | Implemented, with limitations documented below. |
| Unified internal management | Canonical `/noibo/` routes exist for all reviewed surfaces; legacy aliases remain for compatibility and still require cleanup. |
| Workspace isolation/RBAC | Hardened on reviewed UI/API/tool surfaces; remaining gaps are tracked by focused tests and release checklist. |
| Notifications | Four public events; unified authorized-workspace reads. |
| AI/RAG | Implemented in `apps.knowledge`; optional Gemini plus deterministic fallbacks; some tools contain demo output or permission drift. |
| Forecasting | Real XGBoost pipeline with durable DB lifecycle, product/category/branch dimensions and monitoring; deployment worker evidence remains external. |
| Recommendations | Deterministic advisory records; validated mutation recommendations create controlled approvals, while unsupported actions remain unmapped. |
| GIS | Real PostGIS operations; selected assistant cluster/root-cause output is demo logic. |
| Integration/mapping | Staging, preview, SSRF/upload defenses, safe transforms and canonical persistence implemented. |
| Approval/audit | Controlled mutation approval, idempotency and PostgreSQL append-only audit trigger migration implemented; production deployment review remains. |

## 4. Public website

`apps.public_web.urls` is mounted at `/`: homepage, `/san-pham/` and detail, `/dich-vu/` and detail, `/yeu-cau-dich-vu/`, `/chi-nhanh/`, `/gioi-thieu/`, `/lien-he/`, Vietnamese auth/reset routes, `/tai-khoan/`, cart, `/gio-hang/api/`, checkout, order history/success, and public AI copilot at `/api/v1/public/copilot/`. Public catalog queries span workspaces of the relevant type. Intended templates and public assistant strictly exclude cost, supplier and internal metrics. Service inquiries persist `ServiceRequest`; contacts create notifications but there is no Contact model.

## 5. Internal management and routes

September 8 review: executive report/export/telemetry now filter workspaces by
the existing capabilities used by each surface. Public Copilot order tracking
requires the authenticated creator or owning guest session and an exact code.
Telemetry query timings are not inference or vector-search benchmarks.

The aggregate dashboard applies capability scopes before business queries;
contact activity is restricted to the logged-in notification recipient.
Report resolution ratio is not SLA compliance; its display hash is a reference,
not a digital signature. Report drafts are plain text in session storage scoped
to user/workspaces, never authoritative server records. CSV text is protected
against spreadsheet formula interpretation. Public health retains field names
but redacts database connection identifiers and raw connection failures.

`/noibo/` is membership-protected and aggregates all workspaces authorized to the user. Every internal UI surface now has a canonical route below `/noibo/`: notifications, retail, services, GIS, integration, mapping, knowledge, assistant, forecasting, recommendations, approvals and status. Primary navigation, dashboard cards and notification targets use these routes. Legacy top-level UI routes remain resolvable for backwards compatibility.

APIs: `/api/v1/auth/*`, `/workspaces/*`, `/retail/*`, `/service-ops/*`, `/gis/*`, `/integration/*`, `/mapping/*`, `/knowledge/*`, `/ai/*`, `/forecasting/*`, `/recommendations/*`, `/approvals/*`, `/tools/*` and `/notifications/*` (all under `/api/v1/`). `apps.retail.urls` also contains duplicate UI patterns that root config does not mount; `ui_urls` is mounted separately.

## 6. Authentication and customer identity

- `accounts.User` extends `AbstractUser`; email is unique.
- `/accounts/login/` is internal browser login, creates a DRF token and stores the default workspace. `/dang-nhap/` routes members/superusers to `/noibo/`, customers to `/tai-khoan/`.
- Public password registration creates one inactive User and a customer profile, sends a six-digit mailbox code valid for 10 minutes plus a single-use signed confirmation link. Code activation is a session-bound CSRF-protected POST; link activation may occur on another device, after which the original browser polls a session-bound CSRF-protected status endpoint and logs the same User in. RegistrationCode serializes issuance/consumption under the User lock, stores a password hash, limits resends to 60 seconds/5 per hour and failed attempts to 5 per hourly window (resend does not reset failures). Existing signed-link registrations without RegistrationCode remain compatible. It never creates membership/role; welcome and internal new-customer notifications wait for activation.
- `Customer.user` is an optional workspace-local FK with a unique `(workspace,user)` constraint. Legacy guest identity is handled explicitly by the public identity service.
- Password reset uses Django tokens and an enumeration-safe response; development email defaults to console.
- Google OAuth uses authorization-code exchange plus UserInfo, requires a verified normalized email and stable `sub`, and persists the provider link in `public_web.SocialIdentity`. A verified Google email activates/links the same pending password-registration User instead of creating a duplicate, invalidating its unverified password; an existing account/provider email cannot be registered again (case insensitive). State is single-use and expires after ten minutes. Production callbacks must be an environment-configured HTTPS URI; public OAuth never grants workspace membership/staff privileges.
- Customer email delivery is persisted per recipient in `public_web.CustomerEmailDelivery` with immutable rendered content, deduplication, status/attempt metadata, bounded retry and customer-owned CSRF-protected resend. Authenticated checkout/service/contact sends separate messages to the account and distinct form address; guests use only a valid form address. SMTP failure never rolls back the business event and is shown as a warning.
- Checkout stores an immutable `OrderDeliveryAddress` snapshot and contacts persist as `ContactSubmission`; the legacy Customer address remains a denormalized profile field pending a future address-book migration.

## 7. Workspace architecture

`Workspace` (UUID, RETAIL/SERVICE) is the data/security boundary. `WorkspaceMembership` maps global User ↔ Workspace ↔ optional Role, unique per user/workspace. Middleware resolves `request.active_workspace` from verified `X-Workspace-ID`, session, default membership, first membership, or first active workspace for a superuser. A forged explicit header resolves to none/access denied.

`WorkspaceScopedModel` adds a required FK and `.objects.for_workspace()`. Children such as OrderItem, Task, Schedule and LaborEntry inherit scope through parents. UI aggregation may query an authorized workspace set, but mutation/detail access must remain constrained to one authorized workspace.

Service/GIS UI resolution uses the active authorized workspace or a workspace of the required domain drawn only from the user's active memberships. Explicit workspace requests are never silently replaced, and global first-workspace fallbacks are forbidden.

## 8. RBAC matrix

Custom Permission rows are bundled into global Roles, then scoped via membership. Superusers bypass custom checks. This is distinct from Django model permissions.

| Area | Admin | Manager | Employee | Viewer | Public customer |
|---|---|---|---|---|---|
| All seeded permissions | All | All except account/workspace management | Limited | Read-oriented | None internal |
| Retail product/order/customer/branch view | Yes | Yes | Yes | Yes | Public subset only |
| Retail create order/manage customer | Yes | Yes | Yes | No | Public checkout only |
| Retail product/order/branch management | Yes | Yes | No | No | No |
| Retail analytics | Yes | Yes | Not seeded | Yes | No |
| Service catalog/request view/create | Yes | Yes | Yes | View only | Public inquiry only |
| Service employee/task/schedule/SLA/analytics | Yes | Yes | Mostly no | Mostly no | No |
| GIS layers / unmasked customer GIS | Yes/Yes | Yes/Yes | Yes/No | Yes/No | No |
| Integration | All | All | View/execute | View | No |
| Mapping | All | All | View/apply | View | No |
| Knowledge/assistant | All | All | View/chat | View only | No |
| Forecast view/manage | Both | Both | View | View | No |
| Recommendation/approval management | Yes | Yes | No | No | No |

Actual enforcement remains inconsistent outside the hardened Service/GIS paths: several list/detail APIs check membership only; knowledge UI calls built-in `user.has_perm()` instead of custom workspace RBAC; assistant tools contain stale permission names.

## 9. Retail architecture

- Category: workspace hierarchy, unique code.
- Product: category/SKU/prices/active and soft-delete metadata. Active SKU uniqueness is conditional on nondeleted state.
- ProductImage: validated 5 MB JPG/PNG/WebP gallery with UUID filenames and primary selection.
- Branch and Customer: contact/location data; Customer has a nullable User FK and workspace-local uniqueness.
- Order/OrderItem: PENDING, CONFIRMED, COMPLETED, CANCELLED; server-calculated totals and historical unit-price snapshots.
- Supplier, GoodsReceipt/Item and StockBalance: atomic, locked receiving increments branch-product stock once.
- Product UI/API implements create/edit/media/trash/restore/permanent delete; purge command defaults to dry-run semantics and protects references.
- Stockout risk is a deterministic lag/rolling-demand heuristic over completed quantities, separate from XGBoost.

Related-model same-workspace consistency is mostly service-layer validation, not a cross-table database constraint.

## 10. Service architecture

Service has four categories, duration, fee and active state. Employee has optional User, skills, availability/workload, hourly rate and GIS point. SLA is unique per priority/workspace. ServiceRequest links Customer, Service, SLA and Employee and stores deadlines/location/lifecycle. Task, Schedule and LaborEntry inherit ticket workspace.

Lifecycle: Customer → ServiceRequest → optional assignment/Task → Schedule and labor → RESOLVED → CLOSED. Assignment records response and creates/updates a task. Internal service creation computes SLA deadlines. Labor cost is minutes/60 × rate snapshot; ticket cost adds service base fee. There is no service-branch model; GIS uses tickets and technicians.

Public inquiries stop at an OPEN ticket. They create or reuse a Customer profile in the selected service workspace, and model validation rejects related Customer, Service, SLA or Employee objects from another workspace. Migration `service_ops.0003` safely cloned/relinked historical mismatches while retaining retail profiles.

## 11. E-commerce architecture

The cart is session-backed as `{product_id_string: quantity}`. It resolves live active/nondeleted products, cleans stale items, clamps quantity to at least one and recalculates prices server-side. Shipping is 30,000 VND, free for pickup or subtotal ≥ 5,000,000 VND.

Place-order is atomic: lock/revalidate products; optionally lock/deduct selected-branch stock; find/create Customer; generate `ORD-YYYYMMDD-<6 hex>`; create PENDING/CASH Order and price snapshots; audit; notify on commit; clear cart.

The order-success page requires either authenticated ownership (creator or normalized customer email) or the guest browser session that created the order. Limitations: home delivery allocates no branch stock; store pickup allows purchase when no StockBalance row exists; no max quantity; only COD/cash is integrated; shipping is in notes.

## 12. Notifications

Events: `NEW_CUSTOMER`, `NEW_ORDER`, `NEW_SERVICE_REQUEST`, `NEW_CONTACT`. Dispatchers select workspace/roles, include active superusers for ADMIN events, deduplicate by event/entity/recipient/workspace and create unread rows. Bell/latest/unread/read-all/center/click-through are implemented.

Reads aggregate across **all authorized workspaces by default**, correctly avoiding selected-workspace restriction. Ownership and authorized-workspace checks protect reads. Notification targets use canonical `/noibo/...` routes. Contact has no persistent entity.

## 13. Assistant and RAG

`apps.knowledge` handles AIChatAPIView, per-user/workspace sessions/messages, intent classification, retrieval, permission-checked tools, optional Gemini synthesis, citations and audit. Tools cover retail sales/catalog/rankings/customers/branches/stock; service tickets/technicians/labor/catalog/schedules; GIS; forecasts; recommendations; comparisons; simulations; root cause. Mutation phrases create ApprovalRequests for dispatch, order status, price or task scheduling.

Reliable answers require permitted canonical tool data or relevant document chunks above threshold; otherwise the strict fallback is returned. Some root-cause, stock simulation and spatial-cluster functions use hard-coded rates/regions/assumptions and are demo/simulation, not observed facts.

RAG pipeline: KnowledgeBase → Document (PDF/DOCX/TXT/MD) → parse → recursive chunks → embeddings → DocumentChunk vectors/metadata → workspace retrieval → citations → synthesis. Ingestion is synchronous. Chunk/overlap/top-k/threshold/model/dimension/provider are settings-driven. Gemini/OpenAI embedding helpers are available; deterministic normalized embeddings are fallback. Conversation messages persist sources/tools.

## 14. Forecasting

The main engine is real `XGBRegressor`. It builds gapless daily/weekly targets; lags 1/7/14; shifted rolling mean 7/14 and std 7; calendar features; chronological 80/20 split; seasonal-naive baseline; MAE/RMSE/MAPE/R² and importances; trusted JSON artifacts. Recursive inference defaults to 14 days with growing ±1.96×RMSE visualization bands (not calibrated intervals).

Working targets: completed retail revenue, noncancelled order count, completed OrderItem quantity as product/category/branch-filterable retail demand, and service-ticket count. Async mode creates one PENDING run and a durable DB worker transitions that same record through RUNNING to COMPLETED/FAILED with lease, heartbeat, retry and cancellation. A supervised worker deployment is still required in production.

## 15. Recommendations

Deterministic workspace-scoped rules produce explainable PENDING records. Retail covers revenue/order thresholds, high performance and stockout/reorder. Service covers SLA risk, overload and nearby candidates. Technician score is 40% distance, 40% workload, 20% skill with availability gating.

Accept/reject changes advisory status and audits. Recommendations with a validated `proposed_action` and immutable parameters create one idempotent ApprovalRequest; nearby-technician recommendations map to `dispatch_technician`, and stock transfers use a transactional service with compensation. They still require a different authorized reviewer. Unsupported reorder/workload actions remain advisory. `SERVICE_TICKET_SPIKE` is declared but not clearly generated.

## 16. GIS

Point fields live on Branch, Customer, Employee and ServiceRequest. GeoDjango performs distance/radius, bbox, branch revenue, technician proximity and GeoJSON output. Customer output masks PII without elevated permission. GIS UI and APIs require `gis.view_spatial_layers`; customer details remain masked without the elevated customer-location permission.

## 17. Integration and mapping

Integration: DataSource (CSV/Excel/MOCK_API) → preview/parse → ImportJob → RawImportRecord staging. Uploads are limited to 10 MB and tabular extensions with sanitized names. Remote APIs enforce scheme/DNS/IP/redirect/timeout/size SSRF controls; relative mock endpoints are allowed.

Mapping: discovery → MappingProfile → ordered rules (direct, conversion, value map, restricted-AST transformation, AI-assisted) → preview/validation → atomic persistence. AI suggestions remain pending/inactive until accepted. Supported targets are Customer, Product, Branch, Order/Item, Service, Employee, ServiceRequest, Task and LaborEntry. Raw staging never directly mutates domain tables.

Integration UI/API access is capability-based: `integration.view_datasource` for reads, `integration.manage_datasource` for configuration, and `integration.execute_import` for preview/execution. It uses the shared membership-derived workspace resolver and has no relation-name fallback.

## 18. Approval and audit

Registry READ tools execute after schema/permission checks. MUTATION tools create PENDING ApprovalRequest with risk/parameters/reason/idempotency key. A different authorized reviewer approves; row lock prevents double execution, stores result and marks EXECUTED. Rejection/execution are audited.

AuditLog records workspace/user/actor/action/entity/changes/IP/timestamp. Model save/delete and admin prevent mutation; migration `audit.0002_auditlog_append_only_trigger` adds PostgreSQL database enforcement. Login/logout are not audited despite older claims.

Controlled tools translate legacy Django-style registry names to seeded custom workspace capabilities. Knowledge tools use custom workspace RBAC directly, including the canonical `service.view_request` codename.

## 19. High-level database map

| Models | Purpose/relationships | Workspace/surface/constraints |
|---|---|---|
| User, Role, Permission | Global identity and bundles | Global; User email and names unique; internal auth. |
| Workspace, Membership | Tenant and User↔Workspace↔Role | Boundary; unique user/workspace. |
| Category, Product, ProductImage | Catalog/media/lifecycle | Direct; public read/internal write; category code and active SKU unique. |
| Branch, Customer | Locations/customers | Direct; public subset/internal; code unique. |
| Order, OrderItem | Sales/price snapshots | Header direct/item inherited; order number unique. |
| Supplier, GoodsReceipt/Item, StockBalance | Inbound inventory | Header/balance direct; item inherited; supplier/receipt/balance uniqueness. |
| Service, Employee, SLA, ServiceRequest | Catalog/staff/SLA/ticket | Direct; public subset/internal; code/request/SLA uniqueness. |
| Task, Schedule, LaborEntry | Work/calendar/cost | Inherited; overlaps service-validated, not DB constrained. |
| DataSource, ImportJob, RawRecord | External staging | Direct; source name unique. |
| MappingProfile, MappingRule | Transform configuration | Direct; consistency mostly application validated. |
| KnowledgeBase, Document, Chunk | RAG corpus/vectors | Direct; KB name and document chunk index constraints. |
| ConversationSession, ChatMessage | AI history/citations/tools | Direct; queries also constrain user/session. |
| ForecastConfig, Run, Result | ML lifecycle | Direct; config version and run/date constraints. |
| Recommendation, ApprovalRequest | Advice/controlled action | Direct; idempotency checked but not unique in DB. |
| Notification | Recipient business event | Direct workspace+recipient; app-level dedupe. |
| AuditLog | Traceability | Optional workspace; app-level append-only. |

## 20. Testing strategy and gaps

Django tests cover auth, workspace/RBAC/isolation, both domains, GIS/privacy, integration/SSRF, mapping/AST, RAG/grounding, forecasting, recommendations/approvals/tools, public site/cart/checkout/IDOR, notifications and security scenarios. Large assistant benchmarks often test routing/structured behavior, not live LLM quality.

Weak/missing coverage: real Google OAuth/Inbox evidence; home-delivery stock reservation; full tool permission matrix; production deployment/restore evidence; complete LLM quality evaluation; and legacy route removal after compatibility policy is approved.

## 21. Security rules and invariants

1. Public website != internal portal; public customers never receive internal access.
2. Unified internal presentation never removes workspace isolation.
3. Scope every business query directly or via a scoped parent; validate related entities share the intended workspace.
4. Enforce custom RBAC on UI and API mutations; login alone is insufficient.
5. Retail and Service remain distinct domains on one platform.
6. Keep server-side totals, lifecycle state machines, snapshots, transactions and row locks.
7. Keep upload/SSRF/redirect/AST/artifact-path protections.
8. Integration stages before mapping; untrusted input never bypasses validation.
9. Actuals, forecasts, recommendations, simulations and LLM prose remain distinguishable.
10. Grounded answers cite evidence or fall back; AI uses structured ORM tools, never arbitrary SQL.
11. AI mutations require deterministic validation, human approval, separation of duties, replay protection and audit.
12. Business events/material mutations remain traceable; PII requires explicit permission.
13. `X-Workspace-ID` is the authoritative explicit selector. Legacy `X-Workspace` code remains compatible only after active-membership validation; an invalid or unauthorized explicit selector never falls back to session/default workspace.

## 22. Known limitations

- Reviewed internal surfaces in Service/GIS, Retail, Integration, Mapping, Knowledge, Forecasting, Recommendations and Approvals use membership-derived resolution and granular custom RBAC; new internal modules must follow the same resolver contract.
- Customer identity, delivery snapshots and ContactSubmission are normalized at the event boundary; a full customer address book is future work.
- Public inquiry tenancy linkage is workspace-validated and historical mismatches were migrated safely.
- Internal routes/navigation are canonical under `/noibo/`; legacy aliases remain during compatibility transition.
- Product-demand dimensions and async lifecycle are implemented; worker deployment and calibrated uncertainty remain future work.
- Recommendation acceptance is controlled by approval; unsupported action types remain advisory.
- Some assistant facts are demo assumptions.
- Health metadata still says “verified & frozen”; settings define LOGIN/LOGOUT constants twice, with later values winning.
- Broad exception handlers sometimes conceal failures.

## 23. Implementation conventions

Email may use the opt-in Brevo HTTPS Django backend on Render Free. Existing
outbox SENT means provider acceptance, not inbox receipt. Timeout outcome is
unknown and must be reconciled against provider logs before retry. See
docs/BREVO_HTTPS_EMAIL.md for supported message formats and activation.

Customer email delivery serializes attempts with a database row lock held across
the bounded provider request and reloads persisted state before checking SENT.
This prevents concurrent or stale callers from duplicating a completed attempt;
it cannot guarantee exactly-once delivery after a provider timeout/process crash.
Pickup checkout validates every available stock row before mutating any balance,
so a rejection redirect cannot commit a partially deducted cart.

Production WSGI imports and health probes must not migrate, seed or reset users.
Build produces artifacts; database migrations run explicitly during release.
Render trust is limited to configured domains. See September 10 release evidence
for deployed-versus-local status and prior administrator seed exposure.

Keep customer UI Vietnamese; identifiers/enums are English/uppercase. Use `.for_workspace()` or an authorized set. Put mutation/calculation in services and reads in selectors. Use atomic transactions/locks for checkout, stock and approvals. Use explicit enums/transitions and historical snapshots. Audit significant mutations. Bound and validate uploads. Add migrations only intentionally, run schema checks, and add focused workspace/RBAC/IDOR tests. Reuse existing abstractions; do not create parallel models/routes/services.
