# Project Status & Execution Roadmap

**Project**: Intelligent Business Operations Platform with AI-Powered Analytics, Forecasting and Decision Support  
**Framework**: Django + Django REST Framework + PostgreSQL / PostGIS / pgvector  
**Current Phase**: **PRODUCTION READINESS BASELINE — local implementation verified**  
**Next Phase**: **Staging release, credential rotation, HTTPS OAuth/email acceptance, observability and restore evidence**  
**Last Updated**: 2026-09-06  

---

## 1. Phase Progression Matrix

| Phase | Description | Status | DoD Gate Passed |
|:---:|---|:---:|:---:|
| **0** | **Bootstrap & Environment Inspection** | **COMPLETED** | **YES** |
| **1** | **Architecture, ERD & API Conventions** | **COMPLETED (Corrected)** | **YES** |
| **2** | **Django Core, Accounts, RBAC & Workspaces** | **COMPLETED** | **YES** |
| **3** | **Retail Business Modules (Products, Orders, Customers, Branches)** | **COMPLETED** | **YES** |
| **4** | **Service Operations Modules (Requests, Tasks, Schedules, SLA, Labor)** | **COMPLETED** | **YES** |
| **5** | **GIS Analytics & Spatial Queries (GeoDjango + Leaflet)** | **COMPLETED** | **YES** |
| **6** | **Data Integration Engine (CSV, Excel, Mock API Ingestion)** | **COMPLETED** | **YES** |
| **7** | **Data Mapping Engine & Standard Data Model** | **COMPLETED** | **YES** |
| **8** | **Grounded RAG + LLM Knowledge Assistant** | **COMPLETED** | **YES** |
| **9** | **Predictive Analytics & XGBoost Forecasting** | **COMPLETED** | **YES** |
| **10**| **Recommendation Engine, Safe Tool Calling & Approval Flow** | **COMPLETED** | **YES** |
| **11**| **Testing, Security Auditing & System Hardening** | **COMPLETED** | **YES** |
| **12**| **Final Delivery, Demonstration, Documentation & Packaging** | **COMPLETED** | **YES** |

---

## 2. Phase Summary History

### Phase 2: Django Core, Accounts, RBAC & Workspaces
- `apps/accounts`: User, Role, Permission, Session + Token auth.
- `apps/workspaces`: Workspace, WorkspaceMembership, WorkspaceMiddleware tenancy scoping.
- 30 automated tests passing.

### Phase 3: Retail Commercial Modules
- `apps/audit`: Immutable AuditLog.
- `apps/retail`: Category, Product, Branch, Customer, Order, OrderItem.
- Order lifecycle, server-side pricing, revenue analytics selectors, Chart.js dashboard.
- 61 automated tests passing.

### Phase 4 & Domain Correction: IT / Technical Service Operations
- `apps/service_ops`: Service (4 IT categories), Employee (hourly rates), SLA policies, ServiceRequest, Task, Schedule, LaborEntry.
- Server-side labor cost engine, workload scoring, ticket lifecycle management.
- 93 automated tests passing.

### Phase 5: GIS Analytics & Spatial Queries
- `apps/gis`: PostGIS spatial services, Retail branch GeoJSON, Service technician proximity ranking, Leaflet maps.
- 111 automated tests passing.

---

## 3. Phase 6 Implementation & Verification Summary

### Deliverables Completed:
1. **Core Integration Module (`apps/integration`)**:
   - `models.py`: `DataSource`, `ImportJob`, `RawImportRecord`, `SourceType`, `EntityType`, `ImportStatus`.
   - `parsers/`: `csv_parser.py` (multi-encoding fallback, header cleaning, malformed row isolation), `excel_parser.py` (`openpyxl` multi-sheet reader), `api_parser.py` (REST endpoint client with standard library `urllib`), `preview_engine.py` (type inference & warning detection).
   - `services.py`: `create_data_source`, `update_data_source`, `generate_import_preview`, `execute_import_job` (batch raw staging into `RawImportRecord` with `AuditLog` integration), `get_import_job_errors`.
2. **Mock External REST APIs (`apps/integration/mock_api_views.py`)**:
   - `GET /api/v1/mock-external/retail/orders/`
   - `GET /api/v1/mock-external/retail/customers/`
   - `GET /api/v1/mock-external/retail/products/`
   - `GET /api/v1/mock-external/service/tickets/`
   - `GET /api/v1/mock-external/service/technicians/`
3. **REST API Endpoints**:
   - `GET, POST /api/v1/integration/data-sources/`
   - `GET, PATCH, DELETE /api/v1/integration/data-sources/{id}/`
   - `POST /api/v1/integration/imports/preview/`
   - `GET, POST /api/v1/integration/import-jobs/`
   - `GET /api/v1/integration/import-jobs/{id}/`
   - `GET /api/v1/integration/import-jobs/{id}/raw-records/`
   - `GET /api/v1/integration/import-jobs/{id}/errors/`
4. **Web UI Dashboards & Ingestion Wizard**:
   - `/integration/`: Ingestion dashboard with KPI metric cards and quick action tiles.
   - `/integration/sources/`: Data source registry with active status toggles.
   - `/integration/import/`: Multi-format import wizard with live AJAX preview.
   - `/integration/jobs/`: Import job audit log with filter tabs.
   - `/integration/jobs/{id}/`: Job inspector with staged raw records and error log tabs.
5. **Quality Assurance & Verification**:
   - **144 automated tests** passing across platform (33 new Phase 6 tests, 100% pass rate).
   - Zero schema drift (`makemigrations --check` clean).
   - `seed_demo` updated with 6 default data sources and initial staged records.

---

## 4. Phase 7 Implementation & Verification Summary

### Deliverables Completed:
1. **Core Data Mapping Module (`apps/mapping`)**:
   - `canonical.py`: Canonical ontology contracts for 10 entities (`Customer`, `Product`, `Order`, `OrderItem`, `Branch`, `Service`, `Employee`, `ServiceRequest`, `Task`, `LaborEntry`) with types, constraints, and Vietnamese/English aliases.
   - `models.py`: `MappingProfile` & `MappingRule` supporting 5 rule types (`FIELD_MAPPING`, `TYPE_CONVERSION`, `VALUE_MAPPING`, `BUSINESS_FORMULA`, `AI_ASSISTED_MAPPING`), workspace tenancy, and human review statuses (`PENDING`, `ACCEPTED`, `REJECTED`).
   - `engine/safe_evaluator.py`: Abstract Syntax Tree (AST) safe formula evaluator strictly whitelisting arithmetic and string operations, with zero `eval()` / `exec()` and complete injection rejection.
   - `engine/converters.py` & `value_mappers.py`: Sanitization and type conversion primitives for Decimal (currency parsing), Date, DateTime, Boolean, Integer, Float, List, and categorical dictionary lookup.
   - `engine/transformer.py`: Row transformation pipeline applying active, accepted rules sequentially.
   - `validators.py`: Canonical record validator checking required fields, choices, coordinate ranges, and active workspace foreign key resolution.
   - `ai_suggester.py`: Recommendation engine proposing schema mappings with confidence scores and reasoning, strictly defaulting to `PENDING_CONFIRMATION` for human-in-the-loop review.
   - `services.py`: `discover_source_fields`, profile/rule CRUD, `generate_mapping_preview` (read-only simulation), and `apply_mapping_to_domain` (transactional atomic persistence into `apps.retail` and `apps.service_ops` with `AuditLog` logging).
2. **REST API & Web UI Mapping Studio**:
   - 12 REST API endpoints under `/api/v1/mapping/`.
   - Web UI routes under `/mapping/`: Dashboard (`/mapping/`), Profile Wizard (`/mapping/profiles/new/`), and interactive Mapping Studio (`/mapping/profiles/{id}/studio/`) with live preview modal and AI suggestion panel.
3. **Quality Assurance & Verification**:
   - **170 automated tests** passing across platform (26 new Phase 7 tests, 100% pass rate).
   - Zero schema drift (`makemigrations --check` clean, `migrate --plan` clean).
   - `seed_demo` updated with default mapping profiles for Retail Orders and Service Tickets.

---

## 5. Phase 8 Implementation & Verification Summary

### Deliverables Completed:
1. **Knowledge & RAG Core Module (`apps/knowledge`)**:
   - `fields.py`: `DynamicVectorField` supporting dynamic dimensions, transparently mapping to native PostgreSQL `vector` when extension exists, falling back to indexed `jsonb` array for Windows/dev environments without pgvector binaries.
   - `models.py`: `KnowledgeBase`, `Document`, `DocumentChunk`, `ConversationSession`, `ChatMessage` (all inheriting `WorkspaceScopedModel` with tenancy isolation).
   - `parsers.py`: Pure Python parsers for PDF (`pypdf`), DOCX (`python-docx`), TXT, and Markdown (`NFC` normalization, page number & heading extraction).
   - `chunking.py`: `RecursiveTextChunker` respecting `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, sentence/paragraph boundary hierarchy, and retaining page/heading metadata.
   - `embedding.py`: Dynamic dimension vector embedding service supporting Gemini, OpenAI, and deterministic offline hash-projection fallback with stop-word suppression using standard library `urllib.request`.
   - `retrieval.py`: Vector search engine with cosine similarity ranking, threshold filtering (`RAG_SIMILARITY_THRESHOLD`), and strict active-workspace isolation.
   - `tools.py`: Predefined read-only business telemetry tools (`get_sales_summary`, `get_product_catalog_summary`, `get_customer_summary`, `get_service_ticket_summary`, `get_technician_workload_summary`) enforcing RBAC, PII masking, and audit logging.
   - `services.py`: Document ingestion pipeline (`ingest_document`), hybrid query router (`detect_query_intent`), grounded answer synthesis with citations, and unified entrypoint (`answer_grounded_query`).
2. **REST API & Web UI AI Assistant**:
   - REST API endpoints under `/api/v1/ai/` and `/api/v1/knowledge/`:
     - `POST /api/v1/ai/chat/`
     - `GET, POST /api/v1/ai/sessions/`
     - `GET /api/v1/ai/sessions/{id}/`
     - `GET, POST /api/v1/knowledge/bases/`
     - `GET, DELETE /api/v1/knowledge/bases/{id}/`
     - `GET, POST /api/v1/knowledge/documents/`
     - `GET, DELETE /api/v1/knowledge/documents/{id}/`
     - `POST /api/v1/knowledge/documents/{id}/reindex/`
     - `GET /api/v1/knowledge/documents/{id}/chunks/`
   - Web UI routes:
     - `/ai/`: Full-featured AI Knowledge Assistant with session management, suggestion chips, grounded citation cards, tools-used badges, and copy-to-clipboard.
     - `/knowledge/`: Knowledge Base management studio with upload modal, ingestion status indicators, document deletion, and interactive Chunk Inspector modal.
3. **Quality Assurance & Benchmark Evaluation**:
   - **211 automated tests** passing across platform (28 new Phase 8 tests, 100% pass rate).
   - Test suites: `test_rag_documents.py`, `test_rag_chunking_embedding.py`, `test_rag_retrieval.py`, `test_rag_grounding_assistant.py`, `test_rag_security_rbac.py`, `test_rag_evaluation.py`.
   - Benchmark evaluation across 16 test cases:
     - **Retrieval Relevance Rate**: 85.7% (target >= 80%)
     - **Grounded Correctness Rate**: 100.0% (target >= 80%)
     - **Fallback Precision**: 100.0% (target = 100%)
   - Zero schema drift (`makemigrations --check` clean, `check` clean).
   - Seed script updated: Ingests 4 synthetic Retail policies and 5 Service SOP documents into default workspaces.

---

## 6. Phase 9 Implementation & Verification Summary

### Deliverables Completed:
1. **Core Forecasting Engine (`apps/forecasting`)**:
   - `models.py`: `ForecastModelConfig`, `ForecastRun`, `ForecastResult` inheriting `WorkspaceScopedModel`.
   - `selectors.py`: `get_historical_timeseries` for `RETAIL_REVENUE`, `RETAIL_ORDER_VOLUME`, and `SERVICE_TICKET_VOLUME` with gapless continuous date reindexing and zero-filling.
   - `features.py`: Autoregressive lags (`lag_1`, `lag_7`, `lag_14`), shifted rolling stats (`rolling_mean_7`, `rolling_std_7`, `rolling_mean_14` on `shift(1)` for zero leakage), and calendar features.
   - `evaluation.py`: MAE, RMSE, non-zero masked MAPE, $R^2$, and Naive Persistence Baseline benchmarking with relative percentage improvements.
   - `training.py`: Chronological train/test split (80/20, non-shuffled), XGBoost Regressor training, and native JSON artifact serialization in `ml_models/forecasting/`.
   - `prediction.py`: Recursive multi-step forward forecasting across 14-day horizons, non-negative clamping ($\ge 0$), and approximate 95% prediction bands based on test residual standard deviation.
   - `services.py`: Background thread execution, default config provisioning, and unified Chart.js payload builder (`get_forecast_chart_data`).
   - `serializers.py` & `views.py`: REST API endpoints under `/api/v1/forecasting/` enforcing tenant isolation and RBAC.
   - `ui_views.py` & `templates/forecasting/index.html`: Forecasting dashboard with KPI summary cards, interactive Chart.js multi-line charts with shaded approximate 95% prediction bands, feature importance bar charts, and training history.
   - `management/commands/train_forecast.py`: CLI training command with configurable horizons and hyperparameters.
2. **Quality Assurance & Verification**:
   - **234 automated tests** passing across platform (23 new Phase 9 tests, 100% pass rate).
   - Test suites: `test_forecasting_dataset.py`, `test_forecasting_features.py`, `test_forecasting_training.py`, `test_forecasting_prediction.py`, `test_forecasting_security_rbac.py`, `test_forecasting_api.py`.
   - Zero schema drift (`makemigrations --check` clean, `check` clean).
   - Model verified against naive persistence baseline (results dataset-dependent):
     - Retail Revenue: **+23.69% MAE improvement**, **+27.14% RMSE improvement** over Naive Baseline (MAPE 31.85%).
     - Retail Order Volume: **MAE 0.65 orders**, **MAPE 34.45%** (+19.75% MAE improvement over baseline).
     - Service Ticket Volume: **MAE 0.94 tickets**, **MAPE 62.58%** (+17.54% MAE improvement over baseline; high MAPE attributable to small integer counts, MAE/RMSE emphasized).
3. **Documentation**:
   - Dedicated `docs/forecasting.md` created.
   - Updated `docs/ai-architecture.md` (Section 3: Predictive Analytics Engine).
   - Updated `walkthrough.md` with complete Phase 9 metrics and verification details.

---

## 7. Phase 10 Implementation & Verification Summary

### Deliverables Completed:
1. **Recommendation Engine (`apps/recommendations`)**:
   - `models.py`: `Recommendation` inheriting `WorkspaceScopedModel` with types (`RETAIL_DECLINING_REVENUE`, `RETAIL_LOW_ORDER_VOLUME`, `RETAIL_HIGH_PERFORMING`, `SERVICE_SLA_AT_RISK`, `SERVICE_TECHNICIAN_OVERLOAD`, `SERVICE_NEARBY_TECHNICIAN`).
   - `scoring.py`: Deterministic, explainable technician candidate scoring formula:
     $$\text{Score} = 0.40 \times S_{\text{dist}} + 0.40 \times S_{\text{workload}} + 0.20 \times S_{\text{skill}}$$
     With hard availability gating (`is_available=False` $\to 0.0$), hourly labor rate normalization, and SLA urgency factor.
   - `rules.py`: `evaluate_retail_recommendations` & `evaluate_service_recommendations` generating structured explainable recommendations with WHAT, WHY, EVIDENCE, and EXPECTED EFFECT.
   - `views.py` & `ui_views.py`: REST APIs under `/api/v1/recommendations/` and Web UI dashboard at `/recommendations/` with accept/reject modals and filter tabs.
2. **Controlled Tool Calling & Approval Workflow (`apps/approvals`)**:
   - `models.py`: `ApprovalRequest` with `PENDING`, `APPROVED`, `REJECTED`, `EXECUTED` statuses, `idempotency_key`, row-locking `select_for_update`, and separation of duties (requester != reviewer).
   - `registry.py`: Centralized `ToolRegistry` with schema-validated `READ` tools (immediate telemetry execution) and `MUTATION` tools (redirect to `PENDING` `ApprovalRequest`).
     - Supported mutation tools: `dispatch_technician`, `update_order_status`, `schedule_task`, `adjust_product_price`.
     - Deprecated unsupported tool: `create_promotion_request` (deprecated, preserved for contract stability).
   - `executor.py`: Idempotent tool execution engine with replay protection, separation of duties, and audit logging.
   - `views.py` & `ui_views.py`: REST APIs under `/api/v1/approvals/` and `/api/v1/tools/` plus Approval Center dashboard at `/approvals/`.
3. **AI Assistant & End-to-End Governance Pipeline (`apps/knowledge`)**:
   - AI assistant `answer_grounded_query` connected to `ToolRegistry` for structured telemetry.
   - Natural language action intent routing: when user commands a mutation (e.g. dispatch technician, update order status), AI assistant creates a `PENDING` `ApprovalRequest` via backend execution engine, returns `#AR-<id>` tracking token, and logs `AI_MUTATION_REQUESTED`.
   - **Zero direct DB mutations by LLM / autonomous agents**.
4. **Demonstration Scenarios Verified (`tests/test_phase10_demonstration_scenarios.py`)**:
   - **Scenario A**: Retail Flagged Branch — Querying why a branch is flagged returns structured explainability (what, why, evidence, expected effect) $\to$ **PASSED**.
   - **Scenario B**: Service Technician Candidate — Natural language query recommending technician for ticket calculates multi-criteria GIS distance, workload, skill, availability $\to$ **PASSED**.
   - **Scenario C**: AI Mutation Action — Natural language command to dispatch technician generates `PENDING` `ApprovalRequest`, does not directly mutate ticket $\to$ **PASSED**.
   - **Scenario D**: Approval Execution — Authorized Manager B approves request in Approval Center $\to$ atomically updates ticket assignment, updates task, logs `MUTATION_EXECUTED` in `AuditLog`, enforces replay protection $\to$ **PASSED**.
   - **Scenario E**: Rejection Flow — Manager B rejects request with documented reason $\to$ request marked `REJECTED`, ticket remains unchanged $\to$ **PASSED**.
   - **Scenario F**: Unauthorized Approval Denied — Employee role without approval privileges attempts to approve $\to$ HTTP 403 Forbidden $\to$ **PASSED**.
   - **Scenario G**: Cross-Workspace Isolation — User attempting to execute tool or approve request for another workspace resource is rejected $\to$ **PASSED**.
5. **Quality Assurance & Verification**:
   - **257 automated tests** passing across platform (23 Phase 10 tests, 100% pass rate).
   - Test suites: `test_recommendations.py`, `test_approvals.py`, `test_tool_registry.py`, `test_phase10_integration.py`, `test_phase10_demonstration_scenarios.py`.
   - Django system check: **0 issues (0 silenced)**.
   - Migration check: `makemigrations --check` clean, `migrate --plan` clean (0 pending migrations).
6. **Documentation**:
   - Updated `docs/recommendations.md`, `docs/tool-calling.md`, and `docs/approval-workflow.md`.
   - Updated `docs/ai-architecture.md` (Section 5: Controlled Tool Calling & Approval Workflow).
   - Updated `walkthrough.md` with complete Phase 10 Final Integration Pass verification details.

---

## 8. Phase 11 Implementation & Verification Summary

### Deliverables Completed:
1. **Cross-Domain End-to-End Pipeline Scenarios (`tests/test_phase11_cross_domain_scenarios.py`)**:
   - **Scenario A (Retail Pipeline)**: External CSV Ingestion $\to$ Raw Staging $\to$ Mapping Engine $\to$ Canonical Orders $\to$ GIS Spatial Analytics $\to$ Revenue Forecasting $\to$ Recommendation Engine $\to$ Grounded AI Querying $\to$ AuditLog Trail.
   - **Scenario B (Service Operations Pipeline)**: External Ticket Ingestion $\to$ Mapping Engine $\to$ Canonical ServiceRequest $\to$ SLA & Priority $\to$ GIS Proximity Ranking $\to$ Candidate Recommendation $\to$ Controlled Dispatch $\to$ Separation of Duties Approval $\to$ Single Atomic Execution $\to$ Replay Protection.
   - **Scenario C (Grounded RAG Pipeline)**: Document Ingestion $\to$ Semantic Chunking $\to$ pgvector Embedding $\to$ Hybrid Retrieval $\to$ Grounded Answer with exact citations $\to$ Out-of-domain query exact Vietnamese fallback invariance.
   - **Scenario D (AI Mutation Governance Pipeline)**: Natural language command $\to$ Intent detection $\to$ Zero direct DB mutation $\to$ `PENDING` `ApprovalRequest` $\to$ Separation of Duties validation $\to$ Manager approval $\to$ Controlled execution $\to$ Audit trail.
2. **Security Auditing & Hardening Suite (`tests/test_phase11_security_hardening.py`)**:
   - **Authentication**: Unauthenticated request rejection (401), session + DRF token auth, inactive user block, token revocation on logout, strict JWT exclusion.
   - **RBAC**: Admin, Manager, Employee, Viewer role bounds; Viewer mutation block; Requester self-approval block (Separation of Duties).
   - **Multi-Tenant Isolation & IDOR**: Cross-workspace queries strictly scoped via `WorkspaceScopedModel`; forged `X-Workspace-ID` rejected; cross-workspace object IDOR requests rejected.
   - **AI Safety**: Strict input schema validation via `ToolRegistry`; unregistered tools rejected; malformed parameters blocked; zero direct DB writes by AI.
   - **Data Integration & SSRF**: Private IP ranges (RFC 1918), localhost/loopback, and cloud metadata endpoints (`169.254.169.254`) blocked by `validate_safe_remote_url`.
   - **File Upload Safety**: File size limits (10MB) and dangerous extension blocks (.py, .sh, .exe) enforced by `validate_uploaded_file`.
   - **AST Evaluator Safety**: Safe mathematical and string concatenation formula evaluator strictly rejecting `eval()`, `exec()`, `__import__`, attributes, and calls.
   - **GIS Privacy**: Customer PII (name, phone, email, address) dynamically masked for non-authorized viewers (`can_view_pii=False`).
3. **Production Configuration Hardening (`config/settings.py`)**:
   - `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = False` (AJAX friendly).
   - `SESSION_COOKIE_SAMESITE = 'Lax'`, `CSRF_COOKIE_SAMESITE = 'Lax'`.
   - `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `SECURE_BROWSER_XSS_FILTER = True`.
   - Structured logging configuration (`LOGGING`) formatting standard timestamps and levels.
4. **Platform Regression & Quality Verification**:
   - **276 automated tests** passing across the platform with **0 failures and 0 errors** (100% pass rate in 651.146s).
   - Django system check: **0 issues (0 silenced)**.
   - Migration check: `makemigrations --check` clean, `migrate --plan` clean (0 pending migrations).

---

## 9. Phase 12 Final Delivery, Demonstration & Documentation Summary

### Deliverables Completed:
1. **Comprehensive Documentation Package**:
   - `docs/project-summary.md`: End-to-end architectural summary, component breakdown, target users, technology stack, and full pipeline diagram.
   - `docs/academic-defense-notes.md`: Standardized technical rationale (What, Why, Input, Process, Output, Evaluation, Limitations) for all 22 core technologies.
   - `docs/ai-defense-guide.md`: Conceptual boundary distinctions clarifying RAG vs LLM vs XGBoost vs Business Rules vs Tool Calling vs Human Approval, with Q&A defense.
   - `docs/demo-guide.md`: Exact click-by-click manual for 7 live demonstration scenarios (Retail, Service, Mapping, RAG, Forecasting, Recommendations, Approvals).
   - `docs/installation.md`: Step-by-step installation instructions for native development and optional Docker deployments.
   - `docs/troubleshooting.md`: Real-world operational troubleshooting covering PostgreSQL, PostGIS, pgvector, GDAL/GEOS DLLs, and port conflicts.
2. **Production Security & Configuration Verification**:
   - Hardened session cookies (`SESSION_COOKIE_HTTPONLY = True`).
   - Retained `CSRF_COOKIE_HTTPONLY = False` with documented rationale for frontend AJAX token consumption.
   - Documented `SECURE_BROWSER_XSS_FILTER = True` as legacy/deprecated; highlighted Django auto-escaping and CSP as primary defenses.
   - Evaluated Content Security Policy safely in Report-Only mode (`CSP_REPORT_ONLY = True`).
3. **Demo Data & Model Seeding (`python manage.py seed_demo`)**:
   - Verified that seed command populates complete synthetic demo state: 4 roles, 2 dual workspaces, 4 demo accounts, 40 retail products, 160 orders, 16 service catalog items, 10 technicians, 120 service tickets, 109 labor records, 9 grounded RAG documents, and 3 pre-trained XGBoost forecast models.
4. **Full System Verification**:
   - Django system check: `python manage.py check` $\to$ 0 issues (0 silenced).
   - Migrations integrity: `makemigrations --check` clean, `migrate --plan` clean (0 pending migrations).
   - Full automated test suite: 276 tests passing (100% pass rate).

---

## 10. Production-readiness sign-off
- **Local status**: **BASELINE IMPLEMENTED AND FOCUSED-TEST VERIFIED**.
- Identity/ownership, durable forecasting lifecycle, canonical AI grounding, controlled approvals, transactional stock transfer/rollback, correlation IDs, CSP report-only headers and redacted readiness diagnostics are implemented locally.
- **Production status**: **PENDING EXTERNAL EVIDENCE**. PostgreSQL/PostGIS CI, staging deployment, secret rotation, HTTPS OAuth and inbox delivery, observability, secure-header enforcement review, and backup/restore drill require operator/deployment access.
- Do not describe the repository as production-certified until `docs/PRODUCTION_READINESS_RUNBOOK.md` acceptance evidence is recorded.
