# Operational data and AI repair implementation plan

> **For agentic workers:** Use subagent-driven-development and TDD; independent module tasks have disjoint file ownership. Root handles shared files and final verification. Owner explicitly delegated decisions and opted out of questions.

**Goal:** Repair actual ingestion, safe AI-assisted mapping, trustworthy forecasts and controlled real domain execution.

**Architecture:** Extend current modules, existing JSON receipts and canonical services. No new tables or synthetic production events. Preserve all existing contracts unless they are the reproduced unsafe behavior; document each intentional tightening.

**Tech Stack:** Django/PostGIS, urllib provider boundary, Groq JSON-schema output, current XGBoost/MA7 engine, existing frontend JS.

**Spec:** `docs/superpowers/specs/2026-11-17-operational-ai-design.md`.

## Global constraints

- No business-database writes, schema migration, reset, fake trade/partner evidence or automatic human approval. Isolated TEST records are clearly synthetic.
- Preserve Word and 97-item ledger, RBAC/workspace/public isolation, existing canonical models and saved historical results.
- No test weakening/skipping; add focused RED→GREEN tests. Workers never stage/commit shared index concurrently.
- No provider calls in regression tests, no samples/PII/credentials sent to Groq; schema-only smoke is root-controlled and bounded.
- Existing source-type enum remains backward compatible. Source observations do not establish commercial truth.

## Task 1: Integration and mapping operational repairs

**Own:** `apps/integration/**`, `apps/mapping/**`, their templates and narrowly named regression tests. No root settings/docs/CI edits.
**Interfaces:** Preserve existing URLs; add optional suggestion mode and signed confirmation to existing mapping API. Version1 `ingestion_provenance` in existing source_metadata. Groq uses `config.provider_http` fixed-host request; defaults off/heuristic until explicit schema-export request.

- [ ] Reproduce/fix empty envelopes, remote params, ignored CSV delimiter, relative-route/redirect boundaries, invalid request/config shapes and recursive secret disclosure.
- [ ] Record the payload actually consumed, not a separately fetched preview; preserve legacy receipts UNKNOWN. Reject cross-datasource profile/job application; keep staging distinct from canonical writes.
- [ ] Reproduce/fix winning candidate config drift, duplicate target suggestions, unsafe enum defaults and pending/rejected gating across rule types. Reuse confirmation/audit services.
- [ ] Add bounded optional Groq schema mapper with strict validated indexes/targets, no provider-controlled formulas/defaults, truthful provenance/fallback and signed expiring user/workspace/profile/schema binding.
- [ ] Run real file-byte and controlled HTTP/LLM transport tests, import→staging→confirmation→canonical apply sandbox E2E, existing security/mapping tests and shipped JS tests. Report RED/GREEN commands, actual counts and external limits.

## Task 2: Forecast source, readiness and evaluation correctness

**Own:** `apps/forecasting/**`, forecast template/JS tests, narrowly scoped retail creation default and public checkout business-date fix if needed. Do not touch service_ops/approval/recommendation or shared settings/docs/CI.
**Interfaces:** Preserve current target definitions and guarded selection/holdout. Add read-only readiness under existing view permission; optional `data_mode=historical|operational` training parameter, compatible historical default for API and explicit operational choice in UI. Save readiness and actual evaluation horizons in existing run JSON.

- [ ] Add closed-day/closed-week as-of bounds, actual source bounds and observed/imputed coverage; never pad unknown trailing days or infer TEST/real from names.
- [ ] Operational preflight rejects stale/inadequate data before misleading completion; historical mode remains explicit. Correct mixed elapsed/future-horizon freshness and API/chart parity.
- [ ] Report actual selection/evaluation horizons separately from requested serving horizon; preserve frozen scores. Add WAPE/nonzero-MAPE denominator/coverage diagnostics without disguising MA7 selection as XGBoost superiority.
- [ ] Correct retail default business date to configured timezone, retaining explicit imported dates. Join chart series onto sorted unique dates, without connecting late actuals to a stale forecast origin.
- [ ] Check current/saved data compatibility and active configuration provenance without deleting historical runs; retain artifact/fingerprint protection.
- [ ] Run boundary/date/sparse/horizon/chart tests and existing forecast/business regression suites; report concrete accuracy/data limitations separately from software correctness.

## Task 3: Action freshness, canonical execution and replay

**Own:** `apps/approvals/**`, `apps/recommendations/**`, `apps/service_ops/services.py`, approval/recommendation templates and narrowly named tests. No new tables/shared root settings/docs/CI edits.
**Interfaces:** Existing recommendation→ApprovalRequest relation and canonical tool handlers remain authoritative. Add derived review state and current/history queues without GET writes. Keep exact actor/payload/workspace idempotency binding and human decision.

- [ ] Revalidate tool mutation contract, current permissions, linked recommendation freshness and parameter/workspace consistency under approval lock before execution; no stale/terminal work resurrection.
- [ ] Recognize authorized identical executed replay before current mutable-domain validation, returning original cached result; changed actor/payload remains denied.
- [ ] Harden canonical technician assignment/transition and reuse from dispatch handler, preserving terminal tasks, availability, responded_at, workload and audit.
- [ ] Serialize generation and deduplicate across pending plus accepted-but-open approvals; independent requests for the same live dispatch must not multiply.
- [ ] Derive actionable queue vs history, keep old rows, expose stale reasons and bind POST to displayed workspace.
- [ ] Extend genuine PostGIS generated-rule→accept→independent human approval→canonical mutation→audit/replay E2E in isolated TEST DB, including stale evidence, role/workspace denials, concurrent review and rollback.

## Task 4: Integration verification and handoff

**Own:** Root only — shared settings if justified, docs CURRENT_STATUS/CHANGELOG/PROJECT_CONTEXT, test inventory, CI, common guide and output evidence.

- [ ] Read-only aggregate census of Neon, no PII export; evaluate actual historical series offline if feasible, never create replacement production trades.
- [ ] Review each task (spec and quality) and cross-module interfaces; register new test inventory/CI without changing97progress.
- [ ] Full Python suite on randomized disposable TEST DB, full JS, security/secret checks, browser and bounded schema-only Groq smoke when available.
- [ ] Commit verified code; existing owner-authorized Free release only if source/CI safe. No production import/apply/train/approve business action as autonomous UAT.
- [ ] Report completed engineering work, actual live/sandbox evidence and exact remaining outside-data requirements. Do not label missing real partner/current-data proof complete.

## Review focus

- Secrets in nested config, exceptions/audit, redirect credentials and source receipts.
- LLM suggestion tampering, cross-profile/job binding, delayed acceptance, invalid enum lifecycle conversion and unconfirmed-rule execution.
- Daily/weekly time boundaries, sparse unknown gaps, revised canonical history, reported-vs-scored horizon and model identity.
- Stale approval, actor revocation, duplicate pending actions, replay after stock depletion and terminal task resurrection.
- Cross-task API/frontend compatibility, passive GETs and invariants preserved under concurrency/failure.

## Execution record

Base ab007d5 has fresh full1691/1691, JS76/76 and live seven-case browser evidence from the immediately preceding release. New task implementation still requires fresh verification. Parallelism is limited to disjoint module ownership; shared git index and docs stay root-only. External partner access, verified real legacy provenance and fresh sales are unknown until measured, not fabricated.
