# Intelligent Business Operations Platform with AI-Powered Analytics, Forecasting and Decision Support

> **A Unified Django-based Platform with Dual Operational Workspaces (Retail & Service), Spatial GIS Analytics, RAG Knowledge Retrieval, XGBoost Forecasting, and Human-in-the-Loop AI Decision Support.**

---

## 📌 1. Project Overview & Mission

Modern businesses operate with disparate data silos across sales, customer management, field service operations, and static documentation. This platform bridges operational silos into an intelligent, explainable decision support system.

### Core Value Pipeline
$$\text{Data Ingestion} \longrightarrow \text{Data Mapping} \longrightarrow \text{Standard Model} \longrightarrow \text{GIS / Spatial Analytics} \longrightarrow \text{AI / Forecasting} \longrightarrow \text{Recommendation} \longrightarrow \text{Human Approval} \longrightarrow \text{Tool Action} \longrightarrow \text{Audit Log}$$

### Dual Workspaces
1. **Retail Operations**:
   - Products, Categories, Orders, Customers, Branches, Revenue & KPIs.
   - Spatial GIS business analytics (branch catchment areas, regional revenue, customer density).
   - XGBoost daily/weekly revenue & order volume forecasting.
2. **Service Operations**:
   - Customers, Services, Service Requests, Tasks, Schedules, SLA Tracking.
   - Spatial GIS operational analytics (customer/engineer locations, radius dispatching, proximity queries).
   - Workload analysis and intelligent dispatch recommendations.

---

## 🛠️ 2. Technology Stack

| Layer | Technologies | Role & Purpose |
|---|---|---|
| **Backend** | Python 3.12+, Django 6.0, Django REST Framework | Web platform, ORM, REST API, RBAC, Services |
| **Database** | PostgreSQL 18, PostGIS 3.6, pgvector | Core relational store, spatial geometries, vector embeddings |
| **Spatial / GIS** | GeoDjango, PostGIS, Leaflet.js | Location-aware queries, distance/radius search, map overlays |
| **Machine Learning** | XGBoost, pandas, NumPy, scikit-learn | Time-series tabular forecasting, feature engineering |
| **AI & Retrieval** | RAG, LLM API, Embeddings | Grounded Q&A on SOPs/documents, controlled tool routing |
| **Frontend** | Django Templates, Vanilla HTML/CSS/JS, Chart.js | Responsive dark-mode dashboard, analytics visualization |
| **Containerization** | Docker, Docker Compose | Consistent reproducible environment |

---

## 📁 3. Source Code Structure

```text
ai_business_platform/
├── manage.py                # Django CLI management script
├── config/                  # Core settings, URL routing, WSGI/ASGI, health views
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                    # Modular Django applications
│   ├── accounts/            # Users, roles, RBAC permissions (Phase 2)
│   ├── workspaces/          # Dual workspace switcher (Retail & Service) (Phase 2)
│   ├── retail/              # Retail sales, products, orders (Phase 3)
│   ├── service_ops/         # Service requests, tasks, SLA (Phase 4)
│   ├── gis/                 # Spatial models, GeoDjango queries, Leaflet views (Phase 5)
│   ├── integration/         # Ingestion engine for CSV/Excel/Mock API (Phase 6)
│   ├── knowledge/           # Document ingestion, chunks, embeddings, pgvector (Phase 8)
│   ├── ai_assistant/        # AI chat, prompt templates, tool definitions (Phase 8/10)
│   ├── forecasting/         # XGBoost pipeline, features, training, evaluation (Phase 9)
│   ├── recommendations/     # Business rules engine, action recommendations (Phase 10)
│   ├── approvals/           # Human-in-the-loop review & approval flows (Phase 10)
│   └── audit/               # Immutable audit trail for user & AI actions (Phase 10)
├── templates/               # Django HTML templates
├── static/                  # Vanilla CSS design system, JavaScript & icons
├── ml_models/               # Serialized model artifacts (.pkl/.json)
├── tests/                   # Automated unit, integration, and smoke test suites
├── docs/                    # Architectural specs, ERD diagrams, ADR logs
├── requirements.txt         # Pinned Python package dependencies
├── Dockerfile               # Production & local Docker image definition
├── docker-compose.yml       # Multi-container orchestration (Web + PostGIS DB)
├── PROJECT_STATUS.md        # Real-time phase tracking & Definition of Done gates
├── AGENT_MASTER_SPEC.md     # Single Source of Truth specification
└── .env.example             # Environment configuration template
```

---

## 🚀 4. Quickstart Guide

### Prerequisites
- Python 3.12+ (Tested on Python 3.14)
- PostgreSQL 18 with PostGIS extension installed
- Git

### Local Setup
1. **Clone & Navigate**:
   ```bash
   cd ai_business_platform
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Update database credentials in .env if needed
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Run Automated Tests**:
   ```bash
   python manage.py test
   ```

6. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```
   Open your browser at `http://127.0.0.1:8000` to view the health status dashboard or `http://127.0.0.1:8000/api/health/` for JSON.

### Docker Setup
```bash
docker-compose up --build
```

---

## 🧪 5. Testing & Verification
Execute the test suite at any time:
```bash
python manage.py test tests/
```

---

## 📜 6. Development Rules & Governance
- **Strict Scope Control**: V1 limits algorithms to RAG + XGBoost + Business Rules + Controlled Tools. No uncontrolled multi-agent systems or autonomous SQL execution.
- **Human-in-the-Loop**: All impactful business actions require explicit permission validation, deterministic rule checks, and human manager approval.
- **Phase Isolation**: Phases 0 through 12 must be completed strictly in sequence.
