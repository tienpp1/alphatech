# AI Business Platform — canonical project context

Last verified against source: 2026-09-15
Command Center update (2026-09-30): /noibo/ai-command-center/ and the
/ws/telemetry/ illustrative stream use existing telemetry permissions. ASGI
validates Origin; the stream rechecks current active identity/membership on each
send. DEMO data is explicitly labeled and never represents measured AI accuracy.
Authority: current source code and migrations. Historical phase documents are secondary and may be stale.

Provider transport update (2026-09-25): OAuth token/UserInfo and AI generation/
embedding HTTP clients use config.provider_http with explicit HTTPS host allowlists
and reject redirects before forwarding credential-bearing requests. Google proxy
opt-in remains unchanged. This is a local security change, not evidence of live
OAuth/LLM success; configured-provider errors retain existing safe fallbacks.

Legacy seed_student_admin is disabled (2026-09-25): it cannot reset passwords
or grant global/workspace administrator privileges to preselected identities.
No existing account was changed. WSGI/public health continue to avoid seeding.

Collaboration selection update (2026-09-25): bulletin/chat UI and API use
`notifications.services.resolve_collaboration_workspace` on active authorized
memberships. Explicit invalid/blank/foreign selectors and header/query conflicts
are denied; only absence permits the existing authorized default/session behavior.
Malformed canonical header UUIDs are caught by workspace validation. This does
not add roles or change public-customer access. See focused tests and the separate
pre-patch full-run fingerprint in ACCEPTANCE_BATCH_2026_09_25.md.

Continuation workflow: follow docs/CONTINUATION_WORKING_AGREEMENT.md when the
user requests the next batch. Group implementation, verification and evidence;
preserve other agents' changes and never inflate the 97-item completion count.
Academic working scope: ACADEMIC_ACCEPTANCE_SCOPE.md; requirement evidence:
ACADEMIC_REQUIREMENTS_MATRIX.md; remaining gates: NEXT_CLOSURE_GATES.md.
Employee realtime chat and internal bulletin are teacher-requested requirements,
not replaced by AI ConversationSession/ChatMessage or per-user Notification.
Both now have source implementations (2026-09-23 review): InternalBulletin and
TeamChatMessage, migration notifications/0003, workspace-scoped APIs/UI. Chat
uses 3-second polling, not WebSockets. Bulletin publishing permits active
workspace ADMIN/MANAGER or the explicit superuser bypass; Django is_staff alone
does not grant publishing rights (11 focused tests passed after correction).
The 97/97 claim in Batch 50 is withdrawn: see CHECKLIST_97_PROGRESS.md.
Branch root-cause queries (2026-09-24): an unspecified branch alert may retrieve
recorded workspace recommendations through existing tool RBAC. A named branch
must not inherit workspace-wide evidence as its cause; missing matched evidence
is stated explicitly. Stock root-cause reads now require retail.view_product,
an unambiguous workspace product, and actual balance data (missing is not zero).
SLA/technician explanation branches request case evidence instead of inventing
hours or weights; these clarification responses are not completed causal analysis.
Bulletins support editorial updates at /noibo/bang-tin/<id>/sua/ and the scoped
notifications API. Only title/content/priority change; author/workspace/publication
are preserved. Existing ADMIN/MANAGER or superuser policy applies server-side.

Customer email publication boundary (2026-09-18): order/service emails must not
retrieve internal Knowledge SOPs. Matching a workspace is not public publication
approval; previous first-workspace retrieval has been removed. Preserve transaction
facts and outbox snapshots; no retroactive email rewrite. Approved commercial
policy documents are awaiting user upload (POLICY_PUBLICATION_REVIEW.md).

RAG evidence (2026-09-18): newly ingested chunks store actual embedding mode,
provider/model, returned dimension and sanitized fallback reason in existing
metadata. Query retrieval records its actual embedding and effective threshold;
legacy chunks remain UNKNOWN, not inferred from current configuration. These
observations do not prove semantic correctness or a live provider evaluation.

Embedding compatibility (2026-09-18): retrieval excludes known differences in
mode/provider/model/dimension, including same-length hash fallback versus API
vectors. Legacy unknown provenance remains searchable with an explicit count;
no automatic re-index or assumption about its original model is made.
Checkout concurrency evidence covers strict delivery/pickup and cancellation on
local PostgreSQL. Product locks use PK order. Legacy delivery policy is unchanged.

Forecast evidence (2026-09-17): new training provenance includes source SHA-256
for training/selectors/features/evaluation alongside effective configs, runtime,
dataset fingerprint, chronological split and artifact hash. Academic report
exports these explicitly; old metadata is not reconstructed. Daily RETAIL_REVENUE
is the primary academic target per FORECAST_EXPERIMENT_PROTOCOL.md. Hashes are
identifiers, not source-data backups or proof of production deployment.

Service API read contract (2026-09-17): GET/HEAD of catalog, employee, SLA,
request, task and schedule endpoints require their existing view permission.
Ticket-cost/global labor reads require view_analytics; task-labor reads require
view_task. Mutation checks remain independent. Existing nested ticket/task data
(including costs/employee fields) is unchanged: this is not field-level redaction.

Service analytics (2026-09-17): overview/workload/SLA API reads require active
workspace membership plus service.view_analytics, like the internal dashboard.
Ticket aggregates cover all scoped rows (no first-200 cap). SLA missing deadlines
now produce UNKNOWN and null remaining minutes. A known breach takes precedence
over missing data; otherwise UNKNOWN takes precedence over risk/on-time. Summary
excludes UNKNOWN from its denominator, returns null rate for no evaluable tickets,
and exposes unknown/evaluated counts (also in SLA analytics API). This is current
health, not final contractual compliance; cancellation/closure semantics unchanged.

Service UI (2026-09-16): request detail mutation lookups propagate scoped 404;
labor form uses separate labor_technicians choices (self-only unless existing
manage_task/manage_employee permission). Assignment choices remain independent.
This does not grant service employees permission to change task/request status.

Demo provisioning contract (2026-09-16): seed_demo now requires DEBUG=True,
local database host, --confirm-empty-demo and no existing User/Workspace/Role.
It refuses reseeding instead of resetting existing credentials/data. Optional
--identity-only stops after actual role/user/membership provisioning. No credentials
or tokens are printed. Use only disposable local databases, one seed process at
a time; local host does not detect remote tunneling. Full domain seed was not
revalidated in checkpoint 28. See DEMO_IDENTITY_RUNBOOK.md.

Update 2026-09-17: checkpoint 30 validates the full synthetic seed including three
completed forecast runs. Seed reports DEMO PARTIAL for caught failures in knowledge,
forecast or recommendation stages; completion is not production/model-quality proof.
Routine evidence test runs omit --keepdb, cleaning only their own new test database.

Generation evidence (2026-09-16): normal synthesis returns generation_metadata
and records it in AI_CHAT_QUERY audit. LLM_RESPONSE means a nonempty provider
response was used; model is the requested model identifier, not an independently
verified provider version. DETERMINISTIC records no-key/provider-unavailable/
simulation reasons; NO_CONTEXT makes no provider call. Legacy/early router paths
without metadata stay UNKNOWN. Benchmarks preserve this distinction; tests with
simulated providers do not establish live LLM quality. Assistant status labels
apply to newly returned messages; historical ChatMessage schema is unchanged.

GIS distance contract (2026-09-16): shared calculate_distances and radius filters
explicitly use spheroid=True on WGS84 geometry. Both share the same distance
model. Published/analytic reference checks are documented in GIS_REFERENCE_EVIDENCE.md;
they do not certify all PostGIS operations or road distances.

RAG evaluation scoring (2026-09-15): offline cases may declare forbidden phrase
groups; matching one causes `contradiction_detected` and fails the lexical proxy.
This catches only known, declared contradictions. Semantic entailment, numeric
fact validation and live provider provenance remain unmeasured by design.

What-if evidence (2026-09-15): answers containing simulate_what_if_scenario use
deterministic synthesis, including mixed-tool answers, instead of LLM rewriting.
Labels distinguish assumptions from observed events and validated forecasts.
Stock depletion uses explicitly assumed demand, not a learned forecast. Zero
active technicians yields null per-person workload rather than an invented person.

Import/mapping boundary (2026-09-15): import execution rejects a datasource from
another workspace. Canonical apply validates the profile, job, their datasources
and staged row workspace before processing. Rows marked invalid by ingestion are
rejected, not remapped into valid canonical records: strict mode performs no
writes and partial mode skips invalid rows. These service checks supplement,
not replace, existing API/UI RBAC. Customer duplicate business keys remain scoped
upserts; this does not establish replay idempotency for append-only child entities.

Public branch directory update (2026-09-11): `/chi-nhanh/` retains its active RETAIL branch visibility contract and sends only public directory fields to browser JSON. Leaflet/OSM renders the map; browser-only opt-in location/manual origin is not persisted. Explicit public-place address queries POST to a CSRF-protected Django endpoint backed by switchable, HTTPS-only Nominatim with shared PostgreSQL rate gate and cache; road-distance/routing requests go to OSRM, and navigation may be handed off to Google Maps. Radius is Haversine distance, distinct from road distance. Device GPS is supplied by browser Geolocation, not OSM. These public providers are best-effort, not a production SLA; address-search live verification is currently blocked by external timeout. No membership or internal GIS permissions are granted by these tools.

Customer approval celebration (2026-09-12): notification signals create a deduplicated public customer event on `Order PENDING→CONFIRMED` and `ServiceRequest OPEN→ASSIGNED/IN_PROGRESS`. The public shell fetches only the authenticated user's unread, currently owned events; acknowledgement is CSRF-protected. Animation runs only in the browser and respects `prefers-reduced-motion`.

## 1. Project purpose and stack

Registration link safety (2026-09-15): signed registration tokens are checked again inside the locked consume transaction, using the same User row lock as resend. A link superseded between initial lookup and consumption cannot consume the newer challenge. Existing route/expiry/customer privilege contracts are unchanged.

This Django modular monolith serves two domains: **ABC Tech Store** (retail catalog, customers, branches, sales, suppliers, receiving, stock and analytics) and **XYZ IT Technical Services** (service catalog, technicians, tickets, assignments, schedules, SLA and labor cost). Shared capabilities include PostGIS, ingestion/mapping, RAG/assistant, XGBoost forecasts, recommendations, controlled approvals, notifications and audit.

Stack: Python; Django with a custom User; Django REST Framework session/token authentication; PostgreSQL/PostGIS; pgvector-compatible dynamic embeddings; pandas/NumPy/scikit-learn/XGBoost; pypdf/python-docx; Django templates with vanilla JS/CSS, Leaflet-oriented GeoJSON and Chart.js payloads. Dependency ranges are broad (`Django>=5.2,<7.0`), so check runtime versions when relevant.

## 2. Architecture and directories

The request path is generally view → service/selector → ORM model. `config/` owns settings/root routing/health/unified dashboard. `apps.accounts` and `apps.workspaces` own identity, custom RBAC and tenancy. `apps.retail` and `apps.service_ops` own canonical business state. `apps.gis`, `apps.forecasting` and `apps.recommendations` derive analysis. `apps.integration` stages input and `apps.mapping` creates canonical records. `apps.knowledge` owns documents, RAG, conversations, intent routing, business tools and the assistant—there is no live `apps.ai` or `apps.ai_assistant`. `apps.approvals` and `apps.audit` govern mutation/audit. `apps.public_web` and `apps.notifications` own the customer site and internal events.

Other key directories: `templates/public/` is customer-facing; other template folders are internal/legacy UI. `data/synthetic_external/` contains sample feeds. `ml_models/forecasting/` contains trusted XGBoost JSON artifacts. Test inventory changes with source; use the dated discovery/run manifests, not the historical 607-test count. `.specify/` contains workflow artifacts, not runtime code.

## 3. Capability status

| Capability | Actual state |
|---|---|
| Retail and service operations | Implemented; Service server-rendered reads and mutations now enforce workspace RBAC. |
| Public website/e-commerce | Implemented, with limitations documented below. |
| Unified internal management | Canonical `/noibo/` routes exist for all reviewed surfaces; legacy aliases remain for compatibility and still require cleanup. |
| Workspace isolation/RBAC | Hardened on reviewed UI/API/tool surfaces; remaining gaps are tracked by focused tests and release checklist. |
| Notifications | Four public events; unified authorized-workspace reads. |
| AI/RAG | Implemented in `apps.knowledge`; optional Gemini plus deterministic fallbacks; some tools contain demo output or permission drift. |
| Forecasting | Real XGBoost pipeline with durable DB lifecycle, product/category/branch dimensions, explicit missing-period policy and per-run provenance; deployment worker evidence remains external. |
| Recommendations | Deterministic advisory records; validated mutation recommendations create controlled approvals, while unsupported actions remain unmapped. |
| GIS | Real PostGIS operations; selected assistant cluster/root-cause output is demo logic. |
| Integration/mapping | Staging, preview, SSRF/upload defenses, safe transforms and canonical persistence implemented. |
| Approval/audit | Controlled mutation approval, idempotency and PostgreSQL append-only audit trigger migration implemented; production deployment review remains. |

## 4. Public website

Public assistant evidence contract (2026-09-14): static consultation replies must not invent commercial terms, certifications, SLA timings, licensing, refunds, discounts or partner arrangements. Unknown policies are explicitly unverified and directed to existing contact/service forms. Branch results have no invented address/phone fallback. Catalog listing does not imply stock availability. Service descriptions are not repeated as validated certification evidence. These changes do not certify existing catalog/seed content; that content still needs owner review.

`apps.public_web.urls` is mounted at `/`: homepage, `/san-pham/` and detail, `/dich-vu/` and detail, `/yeu-cau-dich-vu/`, `/chi-nhanh/`, `/gioi-thieu/`, `/lien-he/`, Vietnamese auth/reset routes, `/tai-khoan/`, cart, `/gio-hang/api/`, checkout, order history/success, and public AI copilot at `/api/v1/public/copilot/`. Public catalog queries span workspaces of the relevant type. Intended templates and public assistant strictly exclude cost, supplier and internal metrics. Service inquiries persist `ServiceRequest`; contacts persist ContactSubmission and create notifications.

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

- Internal demo credentials are not part of the normal login response. The `/accounts/login/` helper panel requires both `DEBUG=True` and explicit `SHOW_DEMO_CREDENTIALS=True`; production readiness treats any visible panel and an insecure default `SECRET_KEY` as blockers. Seeded demo accounts are still disposable-local fixtures and are not certified or altered by this UI guard.
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

The reviewed internal modules use custom workspace RBAC. This does not certify every future endpoint; explicit exceptions and gaps belong in the current checklist rather than stale pre-convergence descriptions.

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

Strict allocation boundary (2026-09-15): only the configured central/satellite
branches are eligible. Duplicate product lines are aggregated; inactive/deleted
or foreign-workspace products and fractional quantities are rejected. Allocation
still requires one branch for the entire cart; distributed stock has a separate
safe denial, not a false network-shortage claim. `check_fulfillment_stock` is a
read-only workspace-explicit data preflight, not production certification.

The cart is session-backed as `{product_id_string: quantity}`. It resolves live active/nondeleted products, cleans stale items, clamps quantity to at least one and recalculates prices server-side. Shipping is 30,000 VND, free for pickup or subtotal ≥ 5,000,000 VND.

Place-order is atomic: lock/revalidate products; store pickup locks/deducts selected-branch stock and records a reservation; optional strict home-delivery policy (`HOME_DELIVERY_FULFILLMENT_POLICY=strict`) locks all candidate branch balances, prefers configured `BR-D1`, reroutes to configured satellites with valid browser coordinates and hard-stops on network stockout; find/create Customer; generate `ORD-YYYYMMDD-<6 hex>`; create PENDING/CASH Order and price snapshots; mark the stock reservation explicitly; audit; notify on commit; clear cart. Cancelling a stock-backed order locks its balances and releases the reservation exactly once. The default remains `legacy` until production balances are verified.

The order-success page requires either authenticated ownership (creator or normalized customer email) or the guest browser session that created the order. Strict home-delivery allocation is opt-in and has local regression evidence; production activation and branch-balance verification remain external. Without strict policy, legacy home delivery keeps no branch allocation; store pickup rejects missing StockBalance rows; no max quantity; only COD/cash is integrated; shipping is in notes.

## 12. Notifications

Events: `NEW_CUSTOMER`, `NEW_ORDER`, `NEW_SERVICE_REQUEST`, `NEW_CONTACT`. Dispatchers select workspace/roles, include active superusers for ADMIN events, deduplicate by event/entity/recipient/workspace and create unread rows. Bell/latest/unread/read-all/center/click-through are implemented.

Reads aggregate across **all authorized workspaces by default**, correctly avoiding selected-workspace restriction. Ownership and authorized-workspace checks protect reads. Notification targets use canonical `/noibo/...` routes. ContactSubmission is the persistent public contact event.

## 13. Assistant and RAG

`apps.knowledge` handles AIChatAPIView, per-user/workspace sessions/messages, intent classification, retrieval, permission-checked tools, optional Gemini synthesis, citations and audit. Tools cover retail sales/catalog/rankings/customers/branches/stock; service tickets/technicians/labor/catalog/schedules; GIS; forecasts; recommendations; comparisons; simulations; root cause. Mutation phrases create ApprovalRequests for dispatch, order status, price or task scheduling.

Reliable answers require permitted canonical tool data or relevant document chunks above threshold; otherwise the strict fallback is returned. Some root-cause, stock simulation and spatial-cluster functions use hard-coded rates/regions/assumptions and are demo/simulation, not observed facts.

RAG pipeline: KnowledgeBase → Document (PDF/DOCX/TXT/MD) → parse → recursive chunks → embeddings → DocumentChunk vectors/metadata → workspace retrieval → citations → synthesis. Ingestion is synchronous. Chunk/overlap/top-k/threshold/model/dimension/provider are settings-driven. Gemini/OpenAI embedding helpers are available; deterministic normalized embeddings are fallback. Conversation messages persist sources/tools.

## 14. Forecasting

Run provenance records resolved features, actual model arguments, split dates,
target units and model-file SHA-256. Completion publishes these with results
after checking the worker lease; intermediate metadata must not bypass fencing.
No independent validation partition exists in the current holdout workflow.

The main engine is real `XGBRegressor`. It builds gapless daily/weekly targets; lags 1/7/14; shifted rolling mean 7/14 and std 7; calendar features; chronological 80/20 split; seasonal-naive baseline; MAE/RMSE/MAPE/R² and importances; trusted JSON artifacts. Training runs now store one-step holdout interval coverage as an explicitly labeled diagnostic. Recursive inference defaults to 14 days with growing ±1.96×RMSE visualization bands; these remain not-calibrated intervals without recursive coverage evidence.

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

Domain snapshots (2026-09-15): dispatch logs `TECHNICIAN_DISPATCHED` with ticket status/employee before and after plus task ID, with ticket reload under row lock. Stock execution/compensation logs source/destination quantities captured under balance locks. `TASK_STATUS_CHANGED` now records Task status, lifecycle timestamps, actual duration and assigned employee before/after. `GOODS_RECEIPT_RECEIVED` records each item stock quantity before/after and whether its balance was created. These records commit/rollback with their domain mutations; other tools/actions remain outside this evidence.

Permission-denial boundary (2026-09-15): authenticated `ToolPermissionDenied` from tool/decision workers is audited after worker rollback and re-raised unchanged. Metadata excludes submitted parameters and exception text. This covers service entry, not requests rejected earlier by API permission middleware; outer caller transactions still control final persistence.

Failure boundary (2026-09-15): `process_approval_decision` calls an atomic worker, then records sanitized `MUTATION_FAILED` only after handler failure rolls back the business transaction. The current API caller is not atomic. Callers adding an outer transaction must account for audit being subject to that outer rollback; this is not an independent audit store. Handler permission exceptions propagate unchanged; other handler failures return a safe Vietnamese validation error. Successful mutation/state/audit remain atomic.

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
| Recommendation, ApprovalRequest | Advice/controlled action | Direct; ApprovalRequest declares unique `(workspace, idempotency_key)` constraint `unique_workspace_approval_key`. Deployment still needs migration verification. |
| Notification | Recipient business event | Direct workspace+recipient; app-level dedupe. |
| AuditLog | Traceability | Optional workspace; model guard plus PostgreSQL append-only UPDATE/DELETE trigger in migration 0002. Not protection against database owners or outer transaction rollback. |

## 20. Testing strategy and gaps

Django tests cover auth, workspace/RBAC/isolation, both domains, GIS/privacy, integration/SSRF, mapping/AST, RAG/grounding, forecasting, recommendations/approvals/tools, public site/cart/checkout/IDOR, notifications and security scenarios. Large assistant benchmarks often test routing/structured behavior, not live LLM quality.

Weak/missing coverage: real Google OAuth/Inbox evidence; production verification of
home-delivery reservation/release and branch balances; full tool permission matrix;
production deployment/restore evidence; complete LLM quality evaluation; and
legacy route removal after compatibility policy is approved. Local strict
reservation/release behavior is covered by focused regressions.

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
Forecast async contract (2026-10-01): `FORECAST_ASYNC_ENABLED` defaults to DEBUG.
Production must explicitly enable it only with an operated worker; disabled
async requests are rejected before creating configs/jobs. Render Free remains
synchronous-only by owner decision; no paid worker provisioned.
