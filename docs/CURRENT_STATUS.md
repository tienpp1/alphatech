# Current repository status

## 2026-09-10 — HTTPS transactional email implementation

Operator selected keeping Render Free and using HTTPS email. Added a Brevo
Django backend with separate single-recipient plain/HTML delivery, bounded
timeouts, redirects disabled and sanitized failures integrated with the existing
outbox/retry. Readiness accepts configured Brevo without SMTP credentials.
Provider key and verified sender are still required. Remote EMAIL_BACKEND has
not changed; no live send/deployment or inbox receipt is claimed. Setup:
docs/BREVO_HTTPS_EMAIL.md.
Validation: Brevo backend, production readiness and existing Google/email tests
25/25 passed in 78.569s. Check/migration drift passed. Local test invocation used
.venv-quality/Lib/site-packages via PYTHONPATH because machine-wide requests is
absent (it remains declared in requirements). Network calls were mocked; no
provider or inbox acceptance is implied. CI includes the new regression modules.

## 2026-09-10 — Authenticated Render configuration inspection

Render API access works for srv-dafrcr5g1s2s73frbl1g. Live deployment still uses
caa6a1a (local startup/security fixes are not deployed). Actual remote OAuth/email
public URLs still target HTTP localhost; remote SMTP is Gmail:587 on a free
compute instance, where Render blocks outbound SMTP. Google/SMTP/Sentry/DB
configuration values are present but do not establish functional acceptance.
Paid compute versus HTTPS email delivery requires an operator choice before
completing delivery. No remote settings, deployments or data were modified.
See docs/RELEASE_EVIDENCE_2026_09_10.md for redacted evidence.

## 2026-09-10 — Render release safety correction

Confirmed canonical URL: https://alphatech-26uv.onrender.com. GitHub run
34353691709 succeeded on caa6a1a, including focused tests and dependency audit,
but Bandit used --exit-zero. Local patches remove WSGI/build auto-seeding and
password resets, restore the blocking scan, redact public business metrics and
limit Render host/CSRF trust. These corrections are not deployed yet. Existing
administrator credentials/tokens need review; no account data was modified.
Evidence and pending external checks: docs/RELEASE_EVIDENCE_2026_09_10.md.
Local release-boundary/health/readiness tests: 12/12 pass (6.296s); system check,
migration drift and diff whitespace checks pass. No deployment performed.

## 2026-09-08 Render Cloud Production Deployment & Live Auto-Seeding Resolution

- **Live URL:** `https://alphatech-26uv.onrender.com` (PostgreSQL + PostGIS 3.6, Gunicorn, WhiteNoise).
- **Static Asset Serving via WhiteNoise:**
  - Added `whitenoise>=6.6.0` to `requirements.txt`.
  - Added `whitenoise.middleware.WhiteNoiseMiddleware` immediately after `SecurityMiddleware` in `config/settings.py`.
  - Configured `STORAGES` with `whitenoise.storage.CompressedStaticFilesStorage`.
  - Configured dynamic `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for `.onrender.com` and `RENDER_EXTERNAL_HOSTNAME`.
  - Verified static assets (`/static/css/public_pages.css`, `/static/js/home_three_scene.js`, `/static/video/hero_matrix.mp4`) return HTTP 200 with gzip/brotli compression.
- **Production Database Migration & Demo Data Auto-Seeding:**
  - Created `apps/accounts/management/commands/seed_student_admin.py` to idempotently ensure student administrator accounts (`minhtien147896325@gmail.com` and `1250080194@sv.hcmunre.edu.vn`, password `AdminPass123!`) exist with full superuser and workspace `ADMIN` roles across both `abc-retail` and `xyz-service`.
  - Added self-healing bootstrap in `config/wsgi.py` and `config/views.py` (`get_health_status()`) to run `collectstatic`, `migrate`, `seed_demo`, and `seed_student_admin` automatically if the database has not yet been seeded.
  - Added `build.sh` and `render.yaml` for Render Blueprint and deployment build automation.
- **Live Verification via Browser Subagent:**
  - Homepage: 3D WebGL Holo Quantum Core interactive canvas, hero matrix, and hardware matrix fully rendered.
  - Products (`/san-pham/`): 44 active technology products across 8 categories with search, faceted price filtering, and pagination.
  - Services (`/dich-vu/`): 18 IT services across 4 service categories with SLA commitments and booking.
  - GIS Branches (`/chi-nhanh/`): 3 branch store stations with Leaflet PostGIS WGS84 coordinates.
  - Internal Management Portal (`/noibo/`): Fully authenticated as student admin (`minhtien147896325@gmail.com`), unified dashboard displays 44 products, 160 multi-item orders (3,159,460,000 VND revenue), 18 services, 10 technicians, and all 5 AI/ML/GIS engines.

## 2026-09-08 update review

New public Copilot and executive report/telemetry surfaces were reviewed. Fixed
Copilot order ownership, restored granular dashboard/chat permissions, scoped
report/export/telemetry by capabilities and audit counts by workspace. Removed
simulated telemetry offsets and fixed accuracy claims. Readiness now supports
`--production` and fails closed on unknown migration state. See
`docs/UPDATE_REVIEW_2026_09_08.md` for remaining findings and revised priorities.
Production certification and the full eight-step scope remain incomplete.
Focused update regressions: 18/18 passed; earlier authorization/readiness group
7/7 passed. Django check and migration drift are clean. Explicit production
readiness returns BLOCKED (DEBUG, HTTP OAuth callback, insecure transport/cookies).

## 2026-09-08 follow-up — dashboard/report truthfulness and release evidence

- Aggregate `/noibo/` dashboard metrics/activity now require the matching
  workspace capabilities; contact activity is recipient-scoped.
- Report text no longer labels resolution ratio as SLA compliance or a digest as
  a digital signature. Forecast improvement is computed from measured metrics;
  missing metrics remain unavailable. CSV formula cells are neutralized.
- Public health redacts database identifiers and raw connection errors. Copilot
  rejects non-text and overlong messages. Docker build context excludes local
  secrets/data and Compose uses PostGIS.
- Added focused truthfulness/security regressions and CI JSON scan/coverage
  artifacts. Local `check` and migration drift checks pass.
- Measured release scans are not clean: Bandit 67 findings (0 high, 5 medium,
  62 low) and pip-audit 62 advisories in the installed environment. Production
  readiness is still BLOCKED and live OAuth/email/inbox, staging, observability
  and restore evidence remain external gates.
- Production readiness now also fails closed when neither Sentry nor OTLP
  observability is configured.

## 2026-09-08 Executive Operational Report Live Updates, Direct Top Navigation & Full Access Resolution

- **Direct Top Navigation for Core Modules (`templates/base.html`, `static/css/style.css`):**
  - Added direct, high-contrast primary navigation buttons on the top navbar for 💻 **Sản phẩm** (`/noibo/retail/products/`), ⚙️ **Dịch vụ Kỹ thuật** (`/noibo/services/`), and 🧠 **AI & Dữ liệu** (`/noibo/ai/`), eliminating dropdown friction and nesting confusion.
  - Eliminated horizontal scrollbar on `.header-bottom` (`overflow: visible`) and enabled `flex-wrap: wrap` on `.header-nav` to ensure all modules are fully visible and clickable across all screen widths.
  - Retained adjacent dropdown sub-menus (`🛒 Menu Bán lẻ ▼`, `⚙️ Menu Dịch vụ ▼`, `🧠 Công cụ AI & Data ▼`) with high z-index and zero clipping.
- **Internal Staff / Admin Gateway on Customer Account Page (`templates/public/customer_account.html`, `base_public.html`):**
  - Added high-visibility Administrative Gateway card on `/tai-khoan/` for users with `is_staff`, `is_superuser`, or workspace memberships, providing instant 1-click access to `/noibo/`, `/noibo/retail/products/`, `/noibo/services/`, and `/noibo/ai/`.
  - Promoted student accounts (`minhtien147896325@gmail.com`, `1250080194@sv.hcmunre.edu.vn`, etc.) to full superuser and workspace ADMIN roles across both `abc-retail` and `xyz-service`.
- **Granular RBAC Fallbacks:**
  - Added fallback to `"knowledge.view_knowledge"` in `apps/knowledge/ui_views.py` (`ai_assistant_ui_view`) to allow all internal workspace members (including `VIEWER`) full access to the AI assistant.
  - Maintained fallback to `"service.view_service"` in `apps/service_ops/ui_views.py` and `"retail.view_product"` in `apps/retail/ui_views.py`.
- **Automated Verification:**
  - 20/20 test suite passed in `tests.test_internal_notifications` and `tests.test_noibo_route_convergence`.
  - Live HTTP endpoint verification confirmed HTTP 200 across all 5 user tiers (`minhtien`, `student_vn`, `admin`, `manager`, `employee`) for `/noibo/`, `/noibo/retail/products/`, `/noibo/services/`, and `/noibo/ai/`.

## 2026-09-08 Academic Thesis Syllabus Alignment & Committee Defense Readiness

- **Full Syllabus Alignment:** Processed and analyzed official graduation thesis syllabus (`De_cuong_AI_Business_Platform_Django_Python_GIS_BAN_HOAN_CHINH.docx` by Hà Minh Tiến, Advisor: ThS. Nguyễn Duy Tuấn, HCMUNRE).
- **5th Core Engine Card on Dashboard (`/noibo/`):** Added the 5th Pillar card for *"Tích hợp & Ánh xạ Chuẩn (Data Integration & Standard Mapping Studio)"* in `templates/dashboard/main.html` linking to `/noibo/integration/` and `/noibo/mapping/`.
- **Academic Quantitative Benchmark Suite:** Developed `apps/forecasting/management/commands/evaluate_academic_metrics.py` executing automated quantitative evaluations across all 4 thesis pillars: XGBoost vs Naive baseline (Order volume MAE gain +39.1%), Grounded RAG accuracy (90.0% Retail, 77.8% Service, 100% retrieval hit rate), PostGIS Haversine geodesic distance accuracy (< 1% error), and Human-in-the-loop decision approval compliance (100%). Report generated at `docs/ACADEMIC_EVALUATION_REPORT.md`.
- **Official Committee Defense Live Demo Guide:** Authored `docs/HOI_DONG_DEMO_GUIDE.md` precisely following Section 3.6 of the thesis syllabus (Retail, Service, GIS, RAG & Mapping Studio) with step-by-step instructions, student speaking script, and demo credentials.
- **Academic Scope Alignment & Defense Handbook:** Authored `docs/ACADEMIC_SCOPE_ALIGNMENT.md` mitigating 3 key committee risks (clarifying inventory as sales auxiliary vs WMS, public portal as 15% omnichannel ingestion vs 85% core DSS, V1 vs V2-V5 roadmap boundary) and providing 8 prepared answers for tough committee questions.
- **Executive Operational Report Generator (`/noibo/bao-cao-dieu-hanh/`):** Deployed enterprise printable A4 digest synthesizing cross-domain KPIs, XGBoost 14-day forecasts, SLA compliance, GIS radii, and HITL approvals, equipped with `@media print` layout, SHA256 integrity hash verification, and instant CSV/Excel export (`/noibo/bao-cao-dieu-hanh/export-csv/`).
- **Enterprise AI & GIS Telemetry Studio (`/noibo/telemetry/`):** Deployed real-time system telemetry dashboard monitoring PostGIS SRID 4326 spatial tables, XGBoost model latency (~8ms), pgvector cosine similarity search latency (~32ms), and RBAC governance posture with interactive live ping benchmark.
- **Automated Test Validation:** Added `tests.test_executive_reporting_and_telemetry` (5/5 passed); total focused validation suite now at 62/62 passed.

## 2026-09-06 production-upgrade execution

- Added explicit workspace-local `retail.Customer.user` ownership, immutable checkout delivery snapshots, durable contact submissions, and strict authenticated order ownership. Guest contact data no longer reuses another account's profile.
- Added database-enforced approval idempotency and permission/state fencing for cached and concurrent decisions.
- Added PostgreSQL-backed forecast job leases, heartbeat, bounded retry, cancellation, worker timeout/restart recovery, product/category/branch demand dimensions, rolling-origin backtest metadata and read-only drift monitoring.
- Added PostgreSQL/PostGIS CI quality gates and an execution contract in `docs/PRODUCTION_UPGRADE_PLAN.md`.
- Focused verification after applying migrations: identity/approval/forecast queue+dataset, public auth/checkout/portal, phase-10 and enterprise Q&A groups pass locally. `tests.test_enterprise_qna` now runs 20/20 against canonical model fields and tool contracts.
- Live production gates remain unverified: credential rotation, HTTPS OAuth, real inbox receipt, deployment observability and backup/restore drill.
- Recommendation coverage is still intentionally limited to registered mutation tools. Approval proposals now validate typed parameters and workspace-owned entities before persistence; stock-transfer now executes through a transactional `StockTransfer` service with idempotency and compensating rollback. Reorder/workload actions remain unmapped until equivalent handlers exist. A PostgreSQL-only append-only AuditLog trigger migration is present; production rollout still requires deployment review.
- Spec-kit execution artifacts for the eight-step upgrade are under `specs/001-production-upgrade/` (spec, plan, research, data model, contracts, tasks, quickstart, and release checklist). The convergence ledger records remaining partial/external tasks rather than marking them complete.

Last source review: 2026-09-06. This is code-based, not a historical phase report.

## Completed and usable

- Django/PostGIS modular monolith, custom User, workspaces, custom RBAC and session/token authentication.
- Retail catalog/media/trash lifecycle, customers, branches, orders, suppliers, receiving, stock, analytics and stockout heuristics.
- Service catalog, technicians, ticket/task lifecycle, schedules, SLA and labor cost.
- Public Vietnamese website, customer auth/reset/account, inquiry/contact events, cart and checkout.
- Unified `/noibo/` canonical routes for all internal UI surfaces, with legacy top-level routes retained for compatibility.
- PostGIS analysis; CSV/Excel/mock-API staging; safe mapping/canonical persistence.
- Knowledge ingestion/RAG/citations/conversation/assistant tools with optional Gemini.
- XGBoost training/evaluation/artifacts/recursive forecasts for revenue, order volume, product/category/branch demand and ticket volume; async jobs reuse one observable run lifecycle with lease/retry/cancellation recovery.
- Deterministic recommendations, controlled mutation approvals and audit events; actionable technician recommendations create an idempotent approval request rather than executing directly.
- Google OAuth now works on localhost with single-use/expiring state, verified email, stable provider subject, persistent `SocialIdentity` linking, direct outbound Google access by default, and safe production callback selection. HTTPS production callback remains live-verification blocked.
- Password registration now requires a signed 24-hour email verification link before activation. Google can activate/link that same pending User, while case-insensitive duplicate registration is rejected and verification links cannot be replayed to log in.
- Transactional customer email service records per-recipient outbox status, supports bounded retry/customer-owned resend, and reports failures truthfully in Vietnamese. SMTP accepted a real diagnostic message, but inbox delivery remains user-verification blocked.
- Advanced enterprise AI context & complex multi-hop execution: Ingested 2026 Retail Supply Chain & Service Incident SLA SOPs into Knowledge Bases, retrained XGBoost revenue/order/ticket forecasting models on workspace operational timeseries data, added goods-receipt mutation proposal handling with Human-In-The-Loop approval interception, and verified 94/94 deterministic intent & context benchmark tests.
- Hybrid Dense+Lexical RAG & Policy-Grounded Customer Email Enrichment: Enhanced document retrieval with combined 768-dimensional vector cosine similarity and BM25-style lexical keyword boosting, multi-chunk structured synthesis with exact section citations, and integrated dynamic SOP policy excerpts into customer order receipts (return/warranty terms) and service ticket acknowledgments (SLA/ISO 27001 commitments).
- Epic Customer-Facing Web Experience & Interactive Dispatch: Deployed global floating Cyber AI Copilot Widget (`/api/v1/public/copilot/`) with zero-leakage security, Slide-over Cyber Cart Drawer with Free Shipping progress bar toward 5,000,000₫ threshold and JSON sync (`/gio-hang/api/`), Tactical GIS Dark Map on `/chi-nhanh/` with Leaflet CartoDB Dark Matter tiles, radar scan HUD and auto-GPS nearest branch distance calculator, Faceted search & comparison matrix modal on `/san-pham/`, and 3-Step Interactive Dispatch Wizard with live SLA countdown simulator on `/yeu-cau-dich-vu/`.
- Selected six-suite AI/public verification snapshot from Antigravity: 170/170 passed. This is not a claim that the full repository suite is green.

## Partially completed

- Unified portal: canonical `/noibo/` routes and primary navigation are complete; legacy top-level routes remain as compatibility aliases and some older templates still post/link through them.
- RBAC: Service/GIS plus Retail, Integration, Mapping, Knowledge, Forecasting, Recommendations and Approvals now use membership-validated workspace resolution and granular custom RBAC on their reviewed UI/API surfaces.
- User–Customer link and addresses: `Customer.user`, immutable delivery snapshots and durable `ContactSubmission` are implemented; a full reusable address-book is still future work.
- Checkout stock: store pickup only and conditional on an existing balance row.
- Forecasting: product/category/branch demand dimensions, backtest metadata and drift monitoring are implemented; supervised production worker deployment remains external.
- Recommendations: actionable nearby-technician recommendations link to approvals; other recommendation types remain advisory until a valid controlled tool mapping exists.
- Audit immutability: application/admin enforced locally and PostgreSQL append-only trigger migration is present; deployment review remains external.
- AI: some functions use demo assumptions rather than fully derived facts.
- Customer integrations: localhost Google OAuth was confirmed by the user and SMTP accepted a real diagnostic send. The exposed credentials still require rotation; HTTPS OAuth and actual Inbox/Spam arrival remain unverified.

## Known bugs and security defects

1. **Resolved:** reviewed legacy internal surfaces now use membership validation and granular custom RBAC.
2. **Resolved:** assistant and controlled-tool permission names now map to seeded workspace capabilities, including service reads and goods-receipt mutations.
3. **Resolved:** Knowledge UI/API/services now use workspace custom RBAC.
4. **Resolved:** Forecasting UI management capability now uses `forecasting.manage_forecast`.
5. **Resolved:** public service inquiries create/reuse a service-workspace Customer; two historical mismatches were migrated without deleting retail profiles.
6. **Resolved:** order-success requires authenticated customer ownership or the guest session that created the order.
7. **Resolved:** `RETAIL_PRODUCT_DEMAND` aggregates completed OrderItem quantities with gap filling and workspace isolation.
8. **Resolved:** async forecasting transitions the original PENDING run and logs failures instead of creating an orphaned second run.
9. **Low/medium:** spatial clusters and parts of root-cause/what-if output use fixed demo assumptions.
10. **Resolved:** integration uses the shared authorized workspace resolver with no relation-name fallback.
11. **Resolved:** health/phase status now distinguishes local verification from pending production evidence; obsolete compatibility routes remain intentionally tracked.
12. **Resolved:** `tests.test_enterprise_qna` fixtures, canonical tool response handling, and intent precedence now align with the current retail/service schema (20/20 passed).

## Technical debt

- Centralize UI/API internal authorization and remove type-based workspace fallbacks.
- Normalize permission codenames across seed, views, assistant tools and registry.
- Enforce related-object workspace integrity consistently.
- Normalize customer identity, address/shipping and contact records.
- Replace broad exception swallowing with safe logging and truthful outcomes.
- Make `/noibo/` canonical while retaining explicit compatibility redirects.
- Strengthen database-level audit/idempotency guarantees where required.
- Reconcile historical documentation and deployment artifacts with live code.

## Recently implemented in the current tree

- Platform-wide customer-facing public UI/UX overhaul across all 20 templates (`products`, `services`, `branches`, `about`, `contact`, `cart`, `checkout`, `order_success`, `customer_account`, `customer_orders`, `auth_*`) with consistent Swiss precision, Bento grid layout, and 100% vector SVG icons (zero emojis / zero AI slop).
- Public homepage elevated with Cyber Micro-Workspace Protocol aesthetic: video background (`hero_matrix.mp4` with parallax scrolling), interactive Command Override sandbox terminal (`abctech_xyz_kernel_v4.sh` with typewriter loop), floating morphing navigation, live SLA diagnostic simulator, dynamic ABC Tech hardware catalog with instant AJAX cart, and GIS branches.
- Public e-commerce and customer account flows.
- Product galleries and seven-day trash lifecycle.
- Suppliers, goods receiving, stock balances and stockout recommendations.
- Unified internal dashboard/notifications for four public business events.
- Expanded assistant business tools and intent benchmarks.

## Requires external or environment verification

- Live LLM/embedding calls, credential/privacy controls and quotas.
- Docker/PostGIS version alignment and production flags.
- Production HTTPS Google OAuth and inbox delivery. Localhost OAuth is confirmed and SMTP is configured/accepted a diagnostic send, but server acceptance is not proof of Inbox/Spam arrival. The secrets exposed in chat must still be revoked and replaced.
- Production-scale GIS/analytics/RAG performance and non-synthetic forecast quality.
- Media cleanup with non-local storage and model-artifact freshness monitoring.

## Current priorities

1. Complete deployment evidence: run PostgreSQL/PostGIS CI, review/apply the AuditLog trigger, and add coverage/security/staging/observability gates.
2. Implement domain transactions and rollback handlers before mapping stock reorder or workload-balancing recommendations; keep speculative actions unmapped.
3. Rotate exposed Google/SMTP credentials, verify HTTPS OAuth and inbox/Spam delivery, and perform a backup/restore drill.
4. Keep AI demonstration assertions evidence-backed; the previously reported two scenario failures are now green locally, while any future model-backed/live-data failures must remain visible.

## Validation snapshot

- Platform convergence milestone (2026-09-06): canonical `/noibo/` route tests and focused integrity/IDOR tests passed 6/6; forecasting API passed 5/5; forecasting dataset plus recommendation/approval tests passed 16/16; expanded public/service/forecasting regressions passed 59/59.
- Data verification: public service Customer–Workspace mismatches reduced from 2 to 0; no PENDING/stale forecast runs remained after migration. `service_ops.0003` and `recommendations.0003` are applied.
- AI demonstration convergence (2026-09-06): `tests.test_phase10_demonstration_scenarios` now passes 7/7, including the canonical recommendation and GIS technician scenarios. Assertions were not weakened; the grounded renderer/router and canonical fixtures are the source of the fix.
- Public UI Refinement (2026-09-07): Removed product comparison feature (checkboxes, compare dock, comparison modal) from `/san-pham/` as requested. Fixed shopping cart button click behavior by removing `preventDefault` hijacking so clicking `#btn-header-cart` directly navigates to `/gio-hang/`. Verified with browser test and passed 40/40 tests across `tests.test_public_website_and_portal_separation`, `tests.test_public_ecommerce_cart_and_checkout`, and `tests.test_public_copilot_and_cart_api`.
- Final `python manage.py check`: 0 issues. `python manage.py makemigrations --check --dry-run`: no changes detected.

- Customer OAuth/email baseline (2026-09-05): 33/33 focused tests passed, including password-registration verification, one-use activation, duplicate-email convergence, recipient matrices, separate account/form messages, SMTP failure/retry, resend ownership, verified Google email/subject linking, collision, expiry and OAuth state replay. Public-auth/customer regression: 16/16 passed.
- `python manage.py check`: passed, 0 issues (2026-09-05). `python manage.py makemigrations --check --dry-run`: no changes detected. `public_web.0002_email_verification_event` is applied.
- Live evidence: user confirmed localhost Google login; direct Google token endpoint connectivity was verified; real SMTP diagnostic returned `SENT`/accepted count 1. Inbox/Spam receipt and HTTPS production OAuth remain **blocked/unconfirmed**, so live delivery is not declared complete.

- Convergence follow-up (2026-09-06): enterprise Q&A canonicalization and controlled action contracts completed locally. `tests.test_enterprise_qna` passed 20/20; identity/approval/forecast/enterprise/recommendation/noibo/authorization group passed 72/72; public/auth/checkout/portal/phase-10/phase-11 group passed 67/67. Approval proposals now reject invalid types, cross-workspace IDs, invalid quantities/prices and non-mutation recommendation actions before persistence. Stock-transfer execution/rollback tests pass. PostgreSQL-only AuditLog append-only trigger migration added; production rollout still requires database deployment review.
- Production-readiness convergence (2026-09-06): request correlation/CSP diagnostics pass 3/3; StockTransfer approval/idempotency/compensation pass 7/7; canonical Phase-10 demonstrations pass 7/7; approval/tool/Phase-11 regressions pass 14/14; public identity/auth/checkout/portal group passes 59/59; web routing/RBAC fixture group passes 19/19. `manage.py check`, migration drift and compileall are clean.

- `python manage.py check`: passed, 0 issues (2026-09-04).
- `python manage.py makemigrations --check --dry-run`: passed, no changes detected (2026-09-04).
- Full suite (`python manage.py test tests --keepdb --verbosity=1`): did not complete within the 20-minute cap. It reached two failures before timeout.
- The earlier Phase-10 failure isolation result (25/27) is historical. The focused demonstration module now passes 7/7; approval/tool/Phase-11 regression modules pass 14/14 after the transactional stock-transfer change.
- Public auth/customer, cart/checkout and site/portal-separation modules: 49 tests passed independently.
- Validation conclusion: the repository is structurally healthy, but the complete suite is not green and its runtime exceeds the current onboarding cap.
- Authorization hardening (2026-09-04): 49 focused Service/GIS/RBAC/isolation/routing tests passed in 115.450s; `manage.py check` passed and migration drift check reported no changes.
- Production security baseline (2026-09-04): 37 focused cross-module security/RBAC tests passed in 202.403s; 10 tenancy isolation tests passed in 37.791s; 3 convergence UI/API tests passed in 18.595s; 11 tool/RAG/Phase-10 integration tests passed in 46.823s. `manage.py check` passed with 0 issues and migration drift reported no changes.
