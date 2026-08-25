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
