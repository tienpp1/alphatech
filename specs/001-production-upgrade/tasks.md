---
description: "Production Upgrade Baseline task list"
---

# Tasks: Production Upgrade Baseline

**Input**: Design documents from `/specs/001-production-upgrade/`
**Status convention**: `[X]` is implemented and validated locally; `[ ]` is remaining or externally blocked.

## Phase 1: Setup and foundation

- [X] T001 Read AGENTS.md, project context, current status, constitution, and dirty worktree before changes.
- [X] T002 Create specification, plan, research, data-model, contracts, and quickstart artifacts under `specs/001-production-upgrade/`.
- [X] T003 [P] Add additive migrations only; run `python manage.py check` and migration drift checks.
- [X] T004 [P] Preserve public routes, seeded RBAC, workspace isolation, Vietnamese UI, and evidence-backed AI failure transparency.

## Phase 2: User Story 1 — Customer identity and transaction ownership (P1)

- [X] T005 [US1] Add nullable workspace-local User FK and unique `(workspace,user)` constraint to `apps/retail/models.py`.
- [X] T006 [P] [US1] Add `ContactSubmission` and immutable `OrderDeliveryAddress` entities in `apps/public_web/models.py` with migrations.
- [X] T007 [US1] Centralize account-vs-guest ownership in `apps/public_web/customer_identity.py` and integrate public checkout/contact/account views.
- [X] T008 [US1] Enforce creator ownership in public order success/history/detail views and add IDOR regressions in `tests/test_customer_account_identity.py`.
- [X] T009 [US1] Run customer identity, public checkout, auth, portal, and contact deduplication tests.

## Phase 3: User Story 2 — Durable forecasting (P1)

- [X] T010 [US2] Add ForecastRun durable lifecycle fields and CANCELLED status in `apps/forecasting/models.py` with migration.
- [X] T011 [US2] Implement DB queue claim, lease, heartbeat, bounded retry, cancellation, recovery, and fencing in `apps/forecasting/queue.py`.
- [X] T012 [US2] Implement supervised `forecast_worker` timeout/restart execution and `forecast_monitor` drift command.
- [X] T013 [US2] Fence training/prediction publication by lease token in `apps/forecasting/training.py` and `prediction.py`.
- [X] T014 [US2] Add product/category/branch dimension validation and filtering in selectors, training, API and prediction.
- [X] T015 [US2] Add queue, recovery, cancellation, dimensional dataset, backtest and drift tests.

## Phase 4: User Story 3 — Recommendation and approval safety (P1)

- [X] T016 [US3] Add database unique workspace/idempotency constraint to `apps/approvals/models.py`.
- [X] T017 [US3] Add transaction locks, payload matching, terminal-state fencing and permission-before-replay checks in `apps/approvals/executor.py`.
- [X] T018 [US3] Add approval replay, changed-payload, rejection, separation-of-duties and unauthorized-cache tests.
- [ ] T019 [US3] Define and implement rollback-capable action contracts for stock reorder, price change and workload balancing in `apps/approvals/registry.py`; stock-transfer is now transactional with compensation, while reorder/workload execution remains unmapped until domain transactions exist.
- [X] T020 [US3] Add a PostgreSQL-only database-level append-only AuditLog trigger migration; deployment review remains required before production rollout.

## Phase 5: User Story 4 — Grounded AI and canonical tests (P2)

- [X] T021 [US4] Repair the two Phase-10 demonstration failures using canonical recommendation and GIS outputs.
- [X] T022 [X] [US4] Run `tests/test_phase10_demonstration_scenarios.py` and preserve exact failure reporting semantics.
- [X] T023 [US4] Rewrite `tests/test_enterprise_qna.py` fixtures and expectations against current Product, StockBalance, Customer, OrderItem and ServiceRequest models without weakening assertions.

## Phase 6: User Story 5 — CI and production readiness (P2)

- [X] T024 [US5] Add PostgreSQL/PostGIS GitHub Actions workflow with Django check, migration gate and focused test commands.
- [ ] T025 [US5] Add dependency/security scan, coverage threshold, staging deployment, Sentry/OpenTelemetry configuration and release health checks. (workflow scans/readiness checks added; staging/observability remain external)
- [ ] T026 [US5] Add staging backup/restore drill automation and evidence recording.
- [ ] T027 [US5] Rotate all credentials exposed in chat, configure HTTPS OAuth callback, validate CSP/secure cookies and record actual email Inbox/Spam delivery evidence.

## Phase 7: Polish and verification

- [X] T028 [P] Update `docs/CURRENT_STATUS.md`, `docs/CHANGELOG_AI.md`, and production acceptance contract with exact evidence and blockers.
- [X] T029 Run full focused regression groups, `manage.py check`, migration drift and Python compile checks.
- [ ] T030 Execute a full staging release review and mark every external production gate VERIFIED or BLOCKED with operator evidence.

## Dependencies

T001–T004 → T005–T009 → T010–T015 → T016–T020 → T021–T023 → T024–T027 → T028–T030.

## Parallel opportunities

After foundation, identity tests (T006–T009), forecasting tests (T010–T015), and approval tests (T016–T018) can be developed independently, but migrations touching shared database state must be applied sequentially.

## MVP

The local MVP is T001–T018, T021–T022, T024, and T028–T029. T019–T020 and T023–T027 require additional implementation or external deployment authority.

## Phase 8: Convergence

- [X] T031 [US4] Reconcile remaining `tests/test_enterprise_qna.py` expectations with canonical tool response keys and current intent routing; do not weaken assertions.
- [X] T032 [US4] Repair the canonical service compliance selector that references removed `is_sla_breached` data and replace it with the current deadline/status calculation.
- [ ] T033 [US3] Complete formally documented rollback-capable stock reorder, price change, and workload-balancing action contracts; stock-transfer is complete with idempotent execution/compensation, while reorder/workload remain unmapped until domain handlers and rollback semantics exist. (partial)
- [X] T034 [US5] Add a PostgreSQL-only append-only trigger migration that leaves SQLite test cleanup supported; production deployment review is still required.
- [ ] T035 [US5] Run the CI workflow on a real PostgreSQL/PostGIS runner and add coverage/security/staging/observability gates. (missing)
- [ ] T036 [US5] Obtain and record credential rotation, HTTPS OAuth, inbox delivery, secure-header, and restore-drill evidence. (blocked-external)

## Phase 9: Production-readiness convergence (2026-09-06)

- [X] T037 [US5] Add request correlation IDs, redacted `platform_readiness` diagnostics, local security settings and production runbook.
- [X] T038 [US3] Add transactional `StockTransfer` execution with workspace/idempotency constraints, row locks, audit events and compensating rollback; execute approved proposals through the real handler.
- [X] T039 [US4] Re-run canonical Phase-10 demonstration, approval/tool and public identity regression groups without weakening assertions.
- [X] T040 [P] Reconcile project context, current status, changelog, contracts and task ledger with implemented behavior and explicit external blockers.
- [ ] T041 [US5] Execute the GitHub PostgreSQL/PostGIS workflow and collect pip-audit, Bandit and coverage artifacts on a real runner.
- [ ] T042 [US5] Complete credential rotation, HTTPS OAuth/inbox acceptance, staging observability and backup/restore evidence.
