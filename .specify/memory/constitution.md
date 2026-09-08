<!--
SYNC IMPACT REPORT
Version change: 0.0.0 → 1.0.0 (MAJOR — initial ratification)
Added sections:
  - Core Principles (9 principles: Phase-Gated Development, Modular Monolith
    Architecture, Human-in-the-Loop AI, Scope Lock, Test-First Quality,
    Explainability & Auditability, Security & Data Governance, Simplicity &
    YAGNI, Documentation-Driven)
  - Technology & Architecture Constraints
  - Development Workflow & Quality Gates
  - Governance
Removed sections: (none — initial creation)
Modified principles: (none — initial creation)
Follow-up TODOs: none
-->

# AI Business Platform Constitution

## Core Principles

### I. Phase-Gated Development (NON-NEGOTIABLE)

Development MUST follow the Phase 0–12 sequence defined in the
AGENT_MASTER_SPEC. No phase may begin until the prior phase passes its
Definition of Done gate.

- Each phase has an explicit scope and deliverables; agents MUST NOT
  skip ahead or pull work forward from later phases.
- If a gate's exit criteria are not met, work MUST remain in the
  current phase until resolved.
- Cross-phase dependencies MUST be documented and approved before
  implementation begins.

**Rationale**: Phase isolation prevents scope creep, ensures incremental
verification, and allows focused testing at each stage of the platform's
evolution from infrastructure through AI-powered decision support.

### II. Modular Monolith Architecture

All features MUST be implemented as self-contained Django apps within a
single monolithic codebase. No microservices, no separate backend
services, no additional frameworks.

- Each Django app MUST have clear boundaries: its own models, views,
  serializers, URLs, and tests.
- Inter-app communication MUST use Django's standard import mechanism
  or well-defined service interfaces — never raw SQL across apps or
  shared mutable state.
- New apps MUST follow the established directory structure under
  `apps/`.

**Rationale**: A modular monolith delivers the organizational benefits
of microservices (clear boundaries, independent testability) without the
operational complexity that is inappropriate for a semester-scoped
academic project.

### III. Human-in-the-Loop AI

All AI-generated recommendations, tool actions, and data mutations MUST
require explicit human approval before execution. No autonomous data
modification is permitted.

- AI tool calls MUST pass through a permission → validation → approval
  → audit pipeline.
- The approval workflow MUST present the proposed action, its rationale,
  and expected impact to a human manager.
- Emergency or batch operations MUST still log each action for
  post-hoc audit even if pre-approved by policy.

**Rationale**: The platform handles real business data (orders, SLAs,
dispatching). Autonomous AI action without human oversight poses
unacceptable risk to data integrity and business operations.

### IV. Scope Lock — V1 Boundaries (NON-NEGOTIABLE)

V1 scope is fixed and MUST NOT be expanded without explicit documented
approval:

- **AI**: RAG + LLM, XGBoost tabular forecasting, Business Rules
  engine, Controlled Tool Calling.
- **GIS**: GeoDjango + PostGIS + Leaflet.js spatial queries and
  analytics.
- **Integration**: CSV/Excel import + simulated API + Data Mapping.
- **Architecture**: Django modular monolith, local/Docker deployment.

The following are explicitly out of scope for V1:

- Isolation Forest, Hungarian algorithm, multi-agent systems.
- SAP/Salesforce/commercial ERP integrations.
- Microservices, multi-region deployment, production cloud
  infrastructure.
- Raster/remote-sensing/complex routing engines.

**Rationale**: Scope lock prevents the project from becoming
undeliverable within the academic semester. Every addition increases
testing, documentation, and defense burden.

### V. Test-First Quality

Every feature MUST have automated tests before or alongside
implementation. Tests MUST pass before code is merged.

- Unit tests MUST cover business logic, model validations, and
  serializer contracts.
- Integration tests MUST cover API endpoints, cross-app workflows,
  and database interactions including spatial queries.
- Tests MUST NOT be weakened, skipped, or made trivially passing to
  unblock merges.
- If a test fails, the root cause MUST be fixed — not the test.

**Rationale**: Automated tests are the primary safety net for a complex
platform with AI, GIS, and data integration layers. Test-first
discipline catches regressions early and provides confidence during
phased development.

### VI. Explainability & Auditability

All AI outputs MUST be explainable and grounded in source data. All
impactful actions MUST be recorded in an immutable audit trail.

- RAG answers MUST cite source document chunks with relevance scores.
- XGBoost predictions MUST include feature importance and confidence
  intervals where applicable.
- Recommendations MUST state the business rule or data pattern that
  triggered them.
- The audit app MUST record: actor, action, target, timestamp,
  approval status, and outcome for every side-effecting operation.

**Rationale**: Explainability is a core differentiator of this platform
(not a black-box AI). Auditability is required for regulatory
compliance patterns and academic demonstration of responsible AI.

### VII. Security & Data Governance

No secrets in code. No raw SQL in production paths. RBAC enforced on
all endpoints. AI tool calls go through permission and validation
layers.

- API keys, database credentials, and LLM tokens MUST be loaded from
  environment variables or `.env` files that are gitignored.
- All database access MUST use Django ORM or GeoDjango spatial
  lookups — never raw SQL strings in business logic.
- Every API endpoint MUST enforce role-based access control via
  Django's permission framework or DRF permission classes.
- AI-initiated actions MUST be validated against the user's role and
  the tool's permission requirements before execution.

**Rationale**: Security by design prevents credential leaks, SQL
injection, and unauthorized access — critical for a platform that
combines business data, AI capabilities, and tool execution.

### VIII. Simplicity & YAGNI

Start with the simplest solution that works. Do not add complexity,
abstractions, or features until there is a concrete, justified need.

- Prefer Django's built-in capabilities over third-party packages
  unless the built-in solution is demonstrably insufficient.
- Do not add abstraction layers, caching, or optimization until
  profiling demonstrates a measurable problem.
- New dependencies MUST be justified in terms of the specific problem
  they solve and their maintenance cost.
- Demo/seed data MUST NOT be embedded in business logic.

**Rationale**: Over-engineering is the primary risk in an ambitious
multi-module project. YAGNI discipline keeps the codebase
maintainable, debuggable, and defensible within the semester timeline.

### IX. Documentation-Driven

Every phase, module, and API MUST have up-to-date documentation.
Architecture decisions MUST be recorded as ADRs.

- Each Django app MUST include a module-level docstring or README
  explaining its purpose, models, and API surface.
- Significant architecture choices (e.g., why XGBoost over other
  models, why monolith over microservices) MUST be recorded as
  Architecture Decision Records (ADRs) in `docs/`.
- The PROJECT_STATUS.md MUST be updated at each phase gate with
  current status, completed deliverables, and known issues.
- API endpoints MUST have docstrings that serve as inline
  documentation for DRF's browsable API.

**Rationale**: Documentation is the bridge between implementation and
academic defense. Without it, sophisticated technical work cannot be
effectively communicated or evaluated.

## Technology & Architecture Constraints

The following technology decisions are locked for V1 and MUST NOT be
changed without a constitution amendment:

| Layer | Locked Technology | Constraint |
|---|---|---|
| **Backend** | Python 3.12+, Django 6.0, DRF | No alternative web frameworks |
| **Database** | PostgreSQL 18, PostGIS 3.6, pgvector | No alternative databases |
| **GIS** | GeoDjango, PostGIS, Leaflet.js | No alternative GIS stacks |
| **ML** | XGBoost, pandas, NumPy, scikit-learn | No deep learning frameworks in V1 |
| **AI/Retrieval** | RAG pattern, LLM API, embeddings | No multi-agent or autonomous systems |
| **Frontend** | Django Templates, Vanilla HTML/CSS/JS, Chart.js | No SPA frameworks (React/Vue/Angular) |
| **Deployment** | Docker, Docker Compose | Local/demo only; no cloud orchestration |

Adding a new major dependency requires:
1. Written justification tied to a specific business requirement.
2. Assessment of maintenance and testing burden.
3. Approval and constitution amendment (version bump).

## Development Workflow & Quality Gates

### Workflow Rules

1. Read existing documentation (this constitution, AGENT_MASTER_SPEC,
   PROJECT_STATUS) before modifying code.
2. Identify the current phase and verify it has not been superseded.
3. Run formatter, linter, and tests after every change.
4. Check and generate Django migrations when models change.
5. Prioritize fixing root causes of test failures over bypassing them.
6. Do not hard-code demo data into business logic.

### Quality Gate Checklist (per Phase)

- [ ] All new code has corresponding unit tests.
- [ ] All tests pass (`python manage.py test`).
- [ ] Migrations are generated and applied cleanly.
- [ ] No secrets or credentials in committed code.
- [ ] PROJECT_STATUS.md updated with phase deliverables.
- [ ] Module documentation updated or created.
- [ ] No unresolved TODO items blocking the gate.

## Governance

This constitution is the supreme governance document for the AI Business
Platform project. It supersedes all other practices, conventions, or
ad-hoc decisions.

### Amendment Procedure

1. Propose the change with written justification.
2. Classify the change as MAJOR, MINOR, or PATCH per semantic
   versioning:
   - **MAJOR**: Removal or redefinition of a core principle, breaking
     change to governance structure.
   - **MINOR**: New principle added, existing principle materially
     expanded, new section added.
   - **PATCH**: Clarifications, wording improvements, typo fixes,
     non-semantic refinements.
3. Document the change in the Sync Impact Report (HTML comment at top
   of this file).
4. Update the version number and Last Amended date.

### Compliance

- All code changes, AI agent actions, and development decisions MUST
  be verifiable against this constitution.
- Agents MUST read this constitution before executing any spec-kit
  command that modifies project artifacts.
- Complexity MUST be justified against specific business requirements
  — never added speculatively.

**Version**: 1.0.0 | **Ratified**: 2026-08-25 | **Last Amended**: 2026-08-25
