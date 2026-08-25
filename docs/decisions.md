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

## ADR-008: Adoption of pgvector for Document RAG Retrieval
- **Status**: Accepted (Phase 1)
- **Context**: RAG requires storing vector embeddings of organizational SOPs and performing semantic cosine similarity search.
- **Decision**: Use the `pgvector` PostgreSQL extension instead of deploying external vector databases like Pinecone, Weaviate, or Milvus.
- **Reason**: Keeps all document chunks, relational metadata, and vector embeddings in the exact same database engine with transactional consistency, zero extra infrastructure costs, and native workspace tenancy joins.
- **Consequences**: Queries use HNSW or IVFFlat indexes directly inside PostgreSQL.

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
