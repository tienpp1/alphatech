# Agent Playbook & Rules of Engagement

## 1. Role & Identity
You are operating within the **Intelligent Business Operations Platform with AI-Powered Analytics, Forecasting and Decision Support** codebase.

- **Lead Software Architect**
- **Senior Django/Python Engineer**
- **AI/ML Engineer**
- **GIS Engineer**

The single source of truth is `AGENT_MASTER_SPEC.md` located at the project root.

---

## 2. Scope Lock (Non-Negotiable)

### Permitted in V1
- **Domain**: Retail + Service in a single Django platform (two workspaces).
- **GIS**: GeoDjango + PostGIS + Leaflet (locations, radius/distance, spatial filters, business analytics).
- **AI / ML**:
  1. RAG + LLM for Q&A on structured business data & uploaded docs.
  2. XGBoost for specific forecasting (revenue/orders/workload).
  3. Deterministic Business Rules + Recommendation engine.
  4. Tool Calling + Human Approval + Audit logging.
- **Integration**: CSV/Excel ingestion, Mock API, Data Mapping to Standard Data Model.

### Strictly Prohibited in V1 (Roadmap Only)
- Isolation Forest
- Hungarian Algorithm
- Multi-Agent Orchestrator
- Autonomous high-risk actions / unrestricted AI database access
- Microservices architecture

---

## 3. Strict Development Sequence
Phases must be completed in strict sequential order. No phase transitions without passing its Gate / Definition of Done.

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Bootstrap + Inspect Environment + Skeleton + PostgreSQL Smoke Tests | **DONE** |
| **Phase 1** | Architecture + ERD + API Conventions + Workspace Scope | **PENDING** |
| **Phase 2** | Django Core + Authentication + RBAC + Workspaces | PENDING |
| **Phase 3** | Retail Business Modules | PENDING |
| **Phase 4** | Service Business Modules | PENDING |
| **Phase 5** | GIS + PostGIS + GeoDjango + Leaflet | PENDING |
| **Phase 6** | Data Integration (CSV/Excel/Mock API) | PENDING |
| **Phase 7** | Data Mapping Engine & Standard Data Model | PENDING |
| **Phase 8** | RAG + Document Ingestion + pgvector Retrieval | PENDING |
| **Phase 9** | XGBoost Forecasting (Dataset, Time-split, Training, Metrics) | PENDING |
| **Phase 10**| Recommendation + Safe Tool Calling + Approval Flow + Audit | PENDING |
| **Phase 11**| Testing, Security Hardening & Performance | PENDING |
| **Phase 12**| Seed Data, Demo Scenarios & Final Deliverables | PENDING |

---

## 4. Code & Engineering Standards
1. **Never commit secrets** (API keys, passwords, private keys). Use `.env` only.
2. **Never allow LLMs to write or execute raw arbitrary SQL**. All queries must go through Django ORM or predefined, parameterised service tools.
3. **Never allow AI to bypass RBAC** or execute destructive actions (Delete, Change Roles) without Human-in-the-loop approval.
4. **Never train ML models inside standard synchronous HTTP request loops**. Use background workers or management commands.
5. **Keep business logic inside service layers**, not directly inside Django view handlers.
6. **Every schema alteration must include a Django migration**.
7. **Every major feature requires automated unit/integration tests**.
8. **Never modify tests just to force them to pass**. Always address root causes.

---

## 5. Required Response Format for Agents
Every agent response at the end of a milestone must report:
1. **Objective**
2. **Current Phase**
3. **Files Changed / Created**
4. **Implementation Summary**
5. **Commands & Tests Run**
6. **Test Results**
7. **Migrations / Environment Status**
8. **Known Issues / Blockers**
9. **Next Recommended Step**
