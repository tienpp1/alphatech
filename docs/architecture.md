# System Architecture Blueprint

## 1. Executive Summary

The **Intelligent Business Operations Platform with AI-Powered Analytics, Forecasting and Decision Support** is designed as an enterprise-grade **Django Modular Monolith**. It unifies relational business management, spatial GIS analytics, machine learning forecasting, and retrieval-augmented generation (RAG) into a single cohesive, auditable platform.

---

## 2. End-to-End Architectural Layers

```text
+-----------------------------------------------------------------------------------+
|                            PRESENTATION & CLIENT LAYER                            |
|  - Web Browser / Desktop UI (Django Templates + Vanilla CSS + JavaScript)         |
|  - Interactive Maps (Leaflet.js + GeoJSON Overlays)                              |
|  - KPI & Analytics Dashboards (Chart.js / ECharts)                                |
+-----------------------------------------------------------------------------------+
                                        | (HTTP / HTTPS / REST / JSON)
                                        v
+-----------------------------------------------------------------------------------+
|                             DJANGO WEB & API GATEWAY                              |
|  - Django URL Dispatcher & Authentication Middleware                              |
|  - Django REST Framework (DRF) ViewSets & Serializers                            |
|  - RBAC & Workspace Isolation Guard (Tenant Context Filter)                       |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                            APPLICATION SERVICE LAYER                              |
|  - retail.services          - service_ops.services       - gis.services           |
|  - integration.services     - mapping.services           - knowledge.services     |
|  - forecasting.services     - recommendations.services   - approvals.services     |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
+-----------------------------------------------------------------------------------+
|                        DOMAIN MODELS & DATA ACCESS (ORM)                          |
|  - Multi-Workspace Scoped Entities (Retail, Service, Integration, Workflow)      |
|  - Django ORM + GeoDjango Spatial Field Mixins                                   |
|  - Atomic Database Transactions (django.db.transaction.atomic)                    |
+-----------------------------------------------------------------------------------+
                                        |
                    +-------------------+-------------------+
                    |                                       |
                    v                                       v
+---------------------------------------+   +---------------------------------------+
|        DATABASE STORAGE LAYER         |   |       AI & ML EXECUTION LAYER         |
|  PostgreSQL 18                        |   |  - XGBoost Regressor (Forecasting)    |
|  ├── PostGIS 3.6 (Spatial Points/GIS) |   |  - pandas & NumPy Feature Engineering |
|  ├── pgvector (Embeddings & RAG)      |   |  - LLM API (Google Gemini / OpenAI)   |
|  └── Immutable Audit Log Tables       |   |  - Controlled Tool Calling Engine     |
+---------------------------------------+   +---------------------------------------+
```

---

## 3. Comprehensive Layer Breakdown

### 3.1 Web Presentation Layer
- **Tech Stack**: Django Templates (`.html`), Modern CSS Design System (`static/css/style.css`), Vanilla JavaScript, Leaflet.js for GIS mapping, Chart.js for time-series and KPI visualizations.
- **Responsibilities**: Fast server-side rendering with progressive enhancement; zero heavy client frameworks required in V1 to minimize runtime complexity and dependency vulnerabilities.

### 3.2 API Layer (Django REST Framework)
- **Tech Stack**: DRF 3.18+, Token/Session Authentication, JSON Serializers.
- **Responsibilities**: Exposing uniform REST endpoints (`/api/v1/...`) for external integrations, mobile-ready clients, and asynchronous frontend components.

### 3.3 Application Service Layer
- **Design Pattern**: Pure Python service modules (`services.py`) encapsulating multi-model orchestrations, validation rules, state machine transitions, and external API calls.
- **Responsibilities**: Ensures views remain ultra-thin while business workflows remain unit-testable without spinning up HTTP clients.

### 3.4 Spatial & GIS Layer
- **Tech Stack**: GeoDjango, PostGIS 3.6, Leaflet.js.
- **Responsibilities**: Manages 2D geometries (SRID 4326), spatial indexing via GiST, proximity searches ($ST\_DWithin$), spatial distance calculations ($ST\_Distance$), and bounding box aggregations ($ST\_Contains$).

### 3.5 Machine Learning & Forecasting Layer
- **Tech Stack**: XGBoost, pandas, NumPy, scikit-learn.
- **Responsibilities**: Tabular feature extraction (lags, rolling averages, seasonality indicators), time-based cross-validation splits, training execution isolated in background management commands, persistence of model metrics (MAE, RMSE, MAPE).

### 3.6 RAG & Knowledge Layer
- **Tech Stack**: pgvector extension, text parsing (PDF/DOCX/TXT), recursive text chunking, vector embedding API, cosine similarity vector search.
- **Responsibilities**: Ingests organizational SOPs, policy guidelines, and business documentation; retrieves top-K grounded contexts for user queries while strictly respecting workspace boundaries.

### 3.7 Data Ingestion & Mapping Layer
- **Tech Stack**: openpyxl, pandas, custom transformation pipelines.
- **Responsibilities**: Ingests raw tabular data from CSV/Excel/APIs, applies declarative mapping rules (field aliases, type casts, value conversions, arithmetic formulas), and creates validated Standard Data Model entities.

### 3.8 Security & Audit Layer
- **Tech Stack**: Django Auth, RBAC permissions, append-only `AuditLog` model.
- **Responsibilities**: Enforces tenant-level data segregation by `workspace_id`, authenticates all mutations, verifies user/role permissions before executing AI tools, logs all critical actions.

---

## 4. Why Modular Monolith Over Microservices in V1

| Evaluation Criteria | Modular Monolith (Chosen) | Microservices (Rejected for V1) |
|---|---|---|
| **Data Integrity & Consistency** | **ACID Transactions**: Atomic database operations across orders, tasks, and audit logs within a single PostgreSQL transaction. | **Eventual Consistency**: Requires 2-Phase Commits or Saga pattern, adding massive operational overhead and risk of inconsistent state. |
| **Operational Simplicity** | **Single Container / Process**: Easy local development, zero service mesh, single database connection pool. | **High Overhead**: Requires Docker swarm/K8s, API gateway, distributed tracing, network latency handling. |
| **Development Velocity** | **Rapid Evolution**: Refactoring module boundaries requires standard Python refactoring without breaking network protocols. | **Slow**: Contract versioning (gRPC/Protobuf) required across 5+ independent services. |
| **Explainability (Thesis Defense)** | **Crystal Clear & Transparent**: The entire data flow from CSV $\to$ DB $\to$ GIS $\to$ AI $\to$ Audit can be demonstrated and traced end-to-end in code. | **Opaque & Complex**: Hard to debug and explain distributed network failures during live academic demonstrations. |
| **Future Extensibility** | **Path to Extraction**: Clean app boundaries allow any single app (e.g. `apps.forecasting`) to be extracted into a standalone service in V2+ if scale demands. | **Premature Optimization**: Adds distributed systems complexity before product-market fit is proven. |

---

## 5. Architectural Quality Attributes

1. **Testability**: Every layer (Serializers, Services, ORM Queries, ML Pipelines) has dedicated automated tests.
2. **Security**: Zero SQL interpolation; all AI actions constrained by strict JSON schema validation and RBAC.
3. **Observability**: Every state-changing action (User or AI Tool) produces an immutable `AuditLog` entry.
4. **Resilience**: Graceful fallbacks when external LLM APIs timeout or return insufficient context.
