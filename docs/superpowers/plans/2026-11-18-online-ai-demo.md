# Online AI Demonstration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax. Owner already requested execution and delegated choices; no additional design interview.

**Goal:** ship a truthful, isolated algorithm lab on the existing Render Free site.

**Architecture:** committed synthetic evaluation fixtures/pretrained pre-holdout
model; pure in-memory algorithm runners; selected-workspace-protected Django UI.
No business seed, provider calls, model training in web requests or new tables.

**Tech Stack:** existing Python/Django/XGBoost/NumPy/Pandas and native HTML/JS.

**Spec:** docs/superpowers/specs/2026-11-18-online-ai-demo-design.md.

## Global Constraints

- Existing Render Free service/main only; no new paid resources or production env changes.
- No business-data writes, migrations, new models, provider calls or arbitrary artifacts/inputs.
- Current selected workspace and internal role/permission enforced before algorithm work; customers/Google/employee denied.
- Offline training, online inference/scoring;584-row pre-holdout artifact only, never730-row serving refit for evaluation.
- All inputs/results labeled synthetic and known-scenario, not blinded/commercial or live LLM.
- Keep original local demo, teacher Word and97 ledger untouched; preserve dirty primary.
- No skipped/weakened existing tests; all new test modules in academic inventory.

## Review Focus

- Artifact cutoff/model-schema/SHA corruption must fail before inference, never expose booster.
- Actor permitted elsewhere but not in active workspace denied; no superuser bypass of bad selector.
- Large/duplicate/extra body fields and missing CSRF must not execute algorithms.
- Source snippets/default model params must never call configured live providers or ORM mutation.
- Previous result after failed/repeated click must retain truthful timestamp/state, not appear newly executed.

### Task 1: pure algorithm lab and reproducible forecast assets

**Files:** create apps/forecasting/demo_lab.py, apps/forecasting/demo_assets/{history.csv,evaluation_model.json,manifest.json}, scripts/build_online_ai_demo_assets.py, tests/test_online_ai_demo_algorithms.py; register module in docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md.

**Interfaces:** `run_demo_case(case: str) -> dict` accepts only forecast/retrieval/mapping_pending/mapping_confirmed/recommendation. Returns scope=SYNTHETIC_DEMO, case, execution_mode, warnings, and case-specific display data. View adds executed_at/elapsed_seconds. No workspace or request objects accepted. Constants `DEMO_CASES` supply Vietnamese labels.

- [ ] Write failing tests for known numeric parity, real components, pending-vs-accepted transform, unavailable candidate, schema-only preview, invalid cases, corrupt/cutoff-invalid assets and no business/provider side effects.
- [ ] Observe RED against missing module using isolated evidence settings/test DB.
- [ ] Build fixed584-row evaluation artifact offline using unchanged canonical helpers; audit against archived rows/coverage, write nativeJSON/CSV/manifest with actual source/runtime/cutoff/SHA evidence. Fail on mismatch, no adjustment to seed/data/selection.
- [ ] Implement bounded pure runners with canonical functions; genuine online-equivalent inference and metrics recomputation, no fit/ORM/provider in runtime.
- [ ] Focused GREEN, self-review and commit Task1. Root later runs integrated full suite.

### Task 2: scoped web/UI and navigation

**Files:** create apps/forecasting/demo_views.py, templates/forecasting/demo_lab.html, static/js/ai_demo_lab.js, tests/test_online_ai_demo_access.py, tests/online_ai_demo_ui.test.cjs; modify config/urls.py, apps/workspaces/context_processors.py, templates/base.html, .github/workflows/quality.yml and academic test inventory. Update docs/CURRENT_STATUS.md, CHANGELOG_AI.md, PROJECT_CONTEXT.md.

**Interfaces:** import Task1 `DEMO_CASES/run_demo_case`; `can_use_ai_demo(request)->bool` shared by nav/GET/POST. GET /noibo/mo-phong-ai/ renders template; POST /noibo/mo-phong-ai/run/ returns case data + executed_at/elapsed_seconds. UI uses these real endpoints only.

- [ ] Write failing access/CSRF/current-workspace/input/method/no-store/no-write and UI loading/failure/result tests; observe RED before wiring routes.
- [ ] Implement current role+permission policy, strict512-byte allowlisted form parsing, one execution lock, sanitized503 and no GET compute; preserve canonical internal/Google boundary.
- [ ] Add existing-shell Vietnamese selector/button/tables/explanations; include schema-only approval preview label and retrieval-only/noLLM labels; conditional menu. Use nativeJS, textContent, retained previous result timestamp and no auto retry.
- [ ] Focused GREEN including all scenario POSTs with real components, JS; add both new Python tests and JS to CI, test inventory. Document boundary without changing97progress.
- [ ] Self-review and commit Task2.

### Task 3: root verification and controlled release

**Files:** task receipts output/online_ai_demo_20261118 outside tracked source; update deployment evidence only after observing actual states.

- [ ] Independent scoped task reviews then whole-branch security/correctness review and fixes.
- [ ] Fresh full Django suite on randomized loopback TEST DB, migration drift/check, existing/new JS, Bandit/secret scan, portable asset parity and browser keyboard/375/812/1440px real UI.
- [ ] Verify no migration/build/provider changes and Word/ledger hashes; preserve pinned local demo source155ee33.
- [ ] Push exact tested SHA to feature branch; wait same-SHA CI green; fast-forward main non-force. Use existing pinned Free release helper; avoid duplicate deploy if auto-deploy active.
- [ ] Verify exact SHA LIVE and anonymous deny/health; authenticated production actual scenario POSTs, truthful modes/scores, no business objects created. Provide final URL and updated demo-use notes.
