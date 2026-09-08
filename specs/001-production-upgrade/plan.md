# Implementation Plan: Production Upgrade Baseline

**Branch**: `001-production-upgrade` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary

Complete the remaining production-baseline work in the existing Django modular monolith. Reuse PostgreSQL/PostGIS, custom workspace RBAC, the public email outbox, XGBoost, recommendation registry, approval executor, and existing CI conventions. Keep external production acceptance separate from local implementation proof.

## Technical Context

**Language/Version**: Python 3.14 runtime, Django 6.0.2, compatible Django 5.2–6.x range
**Primary Dependencies**: Django ORM, Django REST Framework, PostgreSQL/PostGIS, pandas, NumPy, XGBoost, GitHub Actions
**Storage**: PostgreSQL/PostGIS; trusted JSON forecast artifacts; database-backed forecast queue
**Testing**: Django TestCase/APIClient, focused tests with `--keepdb`, `manage.py check`, migration drift check
**Target Platform**: Linux or Windows Django deployment with a separately supervised forecast worker
**Project Type**: Django modular monolith with public customer website and internal `/noibo/` portal
**Performance Goals**: Queue claims serialized by row locks; bounded worker execution; no unbounded retries; forecast dimensions remain workspace-scoped
**Constraints**: Preserve public routes/schema, Vietnamese UI, seeded RBAC, dirty worktree, no reset/rewrite of existing migrations, no fabricated external evidence
**Scale/Scope**: Existing two-workspace demo and production baseline; eight approved upgrade areas

## Constitution Check

Pass with conditions: workspace isolation, RBAC, public/internal separation, business-layer mutations, migrations, focused tests, and AI human approval are preserved. External production gates are explicitly blocked until evidence is available. Database audit triggers and full staging observability remain follow-up tasks because they require deployment-specific review.

## Architecture and Data Flow

1. Public checkout/contact resolves ownership from authenticated identity, never submitted contact fields.
2. Forecast API creates a committed `PENDING` `ForecastRun`; `forecast_worker` claims it with a lease token, child-process timeout, heartbeat, bounded retry and fenced completion.
3. Dataset selectors validate dimension IDs in the requested workspace before aggregating canonical OrderItem data.
4. Recommendations call registered read/mutation handlers; mutations create one ApprovalRequest per workspace/idempotency key and require a different authorized reviewer.
5. CI runs PostgreSQL/PostGIS migrations and focused tests. Production checklist records external evidence independently.

## Project Structure

```text
apps/retail/models.py                         # Customer user relation
apps/public_web/models.py                     # Contact and delivery entities
apps/public_web/customer_identity.py          # ownership service
apps/public_web/views.py                      # public integration and IDOR boundaries
apps/forecasting/models.py                    # durable run lifecycle
apps/forecasting/queue.py                     # lease/heartbeat/retry/cancel
apps/forecasting/management/commands/forecast_worker.py
apps/forecasting/management/commands/forecast_monitor.py
apps/forecasting/selectors.py                 # dimensional datasets
apps/forecasting/training.py                  # backtest and fenced publication
apps/approvals/models.py                       # database idempotency
apps/approvals/executor.py                     # state and permission fencing
apps/knowledge/services.py                     # grounded answers
.github/workflows/quality.yml                  # CI PostgreSQL/PostGIS gates
tests/                                         # focused regressions
docs/                                          # status, changelog, acceptance contract
specs/001-production-upgrade/                  # this feature artifacts
```

## Implementation Phases

### Phase 0: Research

- Confirm existing migrations, test database, worker command conventions, and production-only gates.
- Choose database-backed worker over Celery/RQ because no broker is present and the existing monolith already uses PostgreSQL.

### Phase 1: Design

- Define identity, contact, delivery, forecast-run, approval, and external-evidence contracts in `data-model.md` and `contracts/`.
- Write `quickstart.md` with local and blocked-production validation paths.

### Phase 2: Implementation

- Implement P1 identity, forecasting, approval, and grounded AI changes with additive migrations and tests.
- Implement CI gates and documentation.

### Phase 3: Convergence

- Compare code, tests, docs, and all eight success criteria. Append unmet work to tasks instead of claiming completion.

## Validation Gates

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- Focused identity, approval, forecasting, public, and AI demonstration tests
- CI workflow syntax and migration execution on PostgreSQL/PostGIS
- Production gates marked VERIFIED only with operator evidence
