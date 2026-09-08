# Architectural & Technical Decisions Log (ADR)

## ADR-001: Architecture Pattern Selection
- **Status**: Accepted (Phase 0)
- **Decision**: Adopt a **Django Modular Monolith** architecture for V1.
- **Rationale**: Keeps database transactions, shared models, authentication, and testability cohesive while avoiding the complexity and overhead of distributed microservices.

## ADR-002: Dual Workspace Design (Retail & Service)
- **Status**: Accepted (Phase 0)
- **Decision**: Build two distinct operational workspaces (Retail and Service) on top of a unified platform and database.
- **Rationale**:
  - *Retail* demonstrates sales analytics, customer distribution, branch GIS, and revenue forecasting.
  - *Service* demonstrates operational workflows, SLA management, task dispatching, and employee/customer proximity GIS.

## ADR-003: Database & Spatial Stack
- **Status**: Accepted (Phase 0)
- **Decision**: PostgreSQL 18 with PostGIS 3.6 for spatial geometry and pgvector for semantic search.
- **Rationale**: Industrial standard for unified relational, GIS, and vector storage without needing multiple disparate database engines.

## ADR-004: ML & Forecasting Scope Lock
- **Status**: Accepted (Phase 0)
- **Decision**: Restrict forecasting in V1 to XGBoost time-series forecasting with explicit time-based cross-validation and baseline comparison (MAE, RMSE).
- **Rationale**: High interpretability, strong tabular performance, easily explainable during academic defense.

## ADR-005: AI Action Control & Human-in-the-loop
- **Status**: Accepted (Phase 0)
- **Decision**: LLMs interact solely through structured, permitted tool schemas. Actions causing database mutations require deterministic business rule validation and human manager approval.
- **Rationale**: Prevents prompt injection risks, arbitrary SQL execution, and unauthorized modifications.

---

## ADR-006: Selection of PostgreSQL 18 as Primary Datastore
- **Status**: Accepted (Phase 1)
- **Context**: The platform requires strong ACID transaction guarantees, robust JSONB support, spatial indexing, vector extensions, and proven stability.
- **Decision**: Use PostgreSQL 18.x as the single primary relational database.
- **Reason**: Eliminates the operational complexity of maintaining separate relational, GIS, and vector databases; provides native support for GiST spatial indexes and pgvector extensions.
- **Consequences**: Local development requires PostgreSQL 18 with PostGIS extension installed or Docker container deployment.

---

## ADR-007: GeoDjango + PostGIS for Spatial Domain Calculations
- **Status**: Accepted (Phase 1)
- **Context**: The platform needs spatial calculations (distances, radius queries, regional bounding boxes) tightly integrated with business ORM queries.
- **Decision**: Standardize on GeoDjango ORM with PostGIS 3.6 backend.
- **Reason**: Enables spatial lookups directly within Django QuerySets (e.g. `location__dwithin=(pt, D(km=10))`) with native GiST index acceleration, avoiding external routing or GIS servers.
- **Consequences**: Production and Docker builds require `gdal-bin`, `libgeos-dev`, and `libproj-dev`.

---

## ADR-008: Adoption of pgvector for RAG with Configurable Parameters
- **Status**: Accepted (Phase 1 / Corrected)
- **Context**: RAG requires storing vector embeddings of organizational documents and performing semantic similarity search with fine-tuned hyperparameters.
- **Decision**: Use `pgvector` with **configurable experimental parameters** (`RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_SIMILARITY_THRESHOLD`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`).
- **Reason**: Embedding dimension must be dynamically derived from the selected embedding model (e.g. 768 for `text-embedding-004`, 1536 for OpenAI); similarity thresholds must be tuned empirically against domain test benchmarks rather than hardcoded.
- **Consequences**: Vector field dimensions and similarity thresholds are managed via Django settings and environment variables.

---

## ADR-009: Modular Monolith Boundary Enforcement
- **Status**: Accepted (Phase 1)
- **Context**: Managing multi-domain logic (Retail, Service, GIS, AI) without falling into a tangled "spaghetti monolith".
- **Decision**: Strictly isolate domain responsibilities into modular Django apps (`apps/*`) with explicit service layers and banned cross-imports.
- **Reason**: Delivers the development speed and transactional integrity of a monolith while maintaining clean boundaries that could be extracted into microservices in V2+ if enterprise scale requires.
- **Consequences**: Cross-app data access must go through service functions or workspace-scoped queries, avoiding direct foreign key cross-dependencies where inappropriate.

---

## ADR-010: V1 AI Feature Scope: RAG + XGBoost + Business Rules + Tool Calling
- **Status**: Accepted (Phase 1)
- **Context**: AI scope can easily become over-engineered, unprovable, or ungrounded.
- **Decision**: Restrict V1 AI exclusively to 4 auditable capabilities: (1) RAG grounded Q&A, (2) XGBoost tabular forecasting, (3) Deterministic Business Rules, (4) Safe Tool Calling with Approval.
- **Reason**: Provides a complete, demonstrable end-to-end intelligent platform with mathematically sound evaluation metrics (MAE, RMSE, RAG Groundedness) that is 100% defendable.
- **Consequences**: Multi-agent swarms, black-box autonomous actions, and deep reinforcement learning are strictly deferred to future versions.

---

## ADR-011: Deferral of Isolation Forest, Hungarian Algorithm & Multi-Agent Orchestration
- **Status**: Accepted (Phase 1)
- **Context**: Complex algorithms like Hungarian matching, Isolation Forest anomaly detection, and Multi-Agent meta-orchestrators increase failure surfaces without adding core value to V1 MVP.
- **Decision**: Explicitly defer Hungarian Algorithm, Isolation Forest, and Multi-Agent Orchestrator to Future Roadmap (V2+).
- **Reason**: V1 prioritizes robust business data ingestion, spatial intelligence, reliable forecasting, and human-in-the-loop governance.
- **Consequences**: Workforce dispatching in V1 uses transparent, explainable heuristic scoring combining PostGIS distance and current technician workload.

---

## ADR-012: Data Mapping & Standard Data Model as Core Architecture
- **Status**: Accepted (Phase 1)
- **Context**: Real-world SME data arrives in unpredictable CSV/Excel formats with localized column headers (`tong_tien`, `ma_kh`).
- **Decision**: Establish the Standard Data Model (SDM) and Data Mapping Engine as fundamental architectural components.
- **Reason**: Decouples domain logic, GIS pipelines, and ML models from messy external schemas; ensures the platform can ingest any client dataset via configuration without code modifications.
- **Consequences**: Every ingestion pipeline must produce validated SDM records before database persistence.

---

## ADR-013: Session & DRF Token Authentication Over Complex JWT for V1 Monolith
- **Status**: Accepted (Phase 1 / Corrected)
- **Context**: Need a secure, simple, and maintainable authentication mechanism for Django templates and REST API endpoints.
- **Decision**: Standardize on **Django Session Authentication** for the server-rendered Web UI and **DRF Token Authentication** (`rest_framework.authtoken`) for programmatic API clients. Avoid complex JWT refresh token rotation workflows in V1.
- **Reason**: Session cookies with `HttpOnly`, `SameSite=Lax`, and CSRF protection are natively robust for Django web applications. Simple tokens suffice for external client integrations without adding distributed revocation complexity.
- **Consequences**: JWT is treated as a future optional extension for external mobile/partner APIs.

---

## ADR-014: Three-Tier Entity Ownership & Workspace Scoping Hierarchy
- **Status**: Accepted (Phase 1 / Corrected)
- **Context**: An earlier draft indiscriminately placed `workspace_id` on all tables, incorrectly coupling global identity entities with tenant boundaries.
- **Decision**: Enforce a **Three-Tier Entity Ownership Hierarchy**:
  1. *Global Entities*: `User`, `Role`, `Permission` (No `workspace_id`).
  2. *Scoping Bridge*: `WorkspaceMembership` (Maps `User` $\leftrightarrow$ `Workspace` $\leftrightarrow$ `Role`).
  3. *Workspace-Scoped Entities*: Direct tenant models (`Order`, `ServiceRequest`, `Product`, `DataSource`, `ForecastModelConfig`) and child entities inheriting tenancy via parent FK (`OrderItem`, `Task`, `DocumentChunk`, `ForecastResult`).
- **Reason**: Allows users to belong to multiple workspaces with distinct roles without duplicating credentials, while ensuring absolute logical data segregation for business transactions.
- **Consequences**: Querysets for tenant models must always filter via `workspace_id` or parent relationships.

---

## ADR-015: Docker Compose Environment Alignment & Verification Deferral
- **Status**: Accepted (Phase 1 / Pre-Phase 2 Cleanup)
- **Context**: The primary canonical local development environment uses native PostgreSQL 18 with PostGIS 3.6. The existing `docker-compose.yml` references `postgis/postgis:16-3.4`. Docker is not installed in the current development environment, meaning container image tags cannot be empirically verified locally.
- **Decision**: Keep `docker-compose.yml` with its existing image configuration and explicitly treat Docker Compose as an optional future/CI deployment artifact. Do NOT fabricate an unverified container image tag. Native PostgreSQL 18 + PostGIS 3.6 remains the canonical datastore standard.
- **Reason**: Prevents committing unverified or broken Docker image tags while maintaining architectural transparency.
- **Consequences**: Docker image verification and compose harmonization are formally deferred until a verified Docker runtime environment is provisioned.
