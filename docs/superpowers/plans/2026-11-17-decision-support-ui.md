# Decision-support UI clarity implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for this small, owner-approved UI change. Preserve existing data, permissions and algorithms.

**Goal:** Keep all five Word-scoped functions, make advanced import/mapping navigation distinct, and explain evidence limits at the point of use.

**Architecture:** Reuse the current base dropdown transport and the five existing page routes. Add one shared, parameterized explanatory include; keep existing model labels, warnings, counts, actions and security checks. Correct the two child CSS blocks that currently do not render into the parent head.

**Tech Stack:** Django templates, existing CSS/JavaScript, Python rendered-template tests and existing JS tests.

**Spec:** Owner-approved description in chat: retain all five pages; group integration/mapping under advanced data management; prioritize honest forecasting/recommendations/approval presentation. This is not a new model-quality experiment or a production-data cleanup.

## Global constraints

- No database writes/migrations, algorithm changes, role grants, public-site changes or paid provider calls.
- Do not change Word or the progress/structure of the 97-item ledger.
- Preserve existing URLs, JS element IDs, CSRF and workspace/RBAC guards.
- Explain that staging validity is not AI accuracy, mapping suggestions are heuristics, MA7 is not XGBoost, MAPE is error, and approving a real pending request may immediately execute it.
- Never classify a record TEST/live based on its name or imply a sandbox exists.

## Task 1: Navigation and honest page guidance

**Files:** `templates/base.html`, `templates/dashboard/main.html`, shared `templates/includes/decision_support_guide.html`; the five dashboard templates; mapping studio/profile and integration job-detail copy; `tests/test_decision_support_ui.py`, existing mapping JS regression tests; `docs/CURRENT_STATUS.md`.

**Interfaces:** Existing routes/context remain unchanged; the shared include consumes only a literal `guide_page`. Existing dropdown JS discovers the new sibling dropdown without a new handler.

- [x] Add rendered DOM tests for group membership/active state, evidence guidance, actual-model/error preservation and CSS in the final head; run RED before editing templates.
- [x] Group import/mapping as a separate advanced menu, neutralize forecast navigation naming, and add short visible explanations with existing next-step links.
- [x] Correct recommendation/approval CSS head blocks; retain existing controls and data.
- [x] Qualify mapping scores as rule-match scores and import success as parser/staging checks; retain all suggestion IDs/API payloads and human confirmation.
- [x] Run new tests, relevant RBAC/business regressions, all Python tests on randomized loopback-only disposable TEST DB, and JS regressions. No business database is reset.
- [x] Review desktop/mobile/keyboard behavior using rendered local fixtures and independent review; record exact results/limits in CURRENT_STATUS.

## Review focus

- Import subpages should highlight the advanced group, not the AI group.
- Missing/empty forecast data must still render without fabricated metrics.
- Large MAPE and MA7 labels must remain visible.
- Guidance must not imply every recommendation is executable or that approval is simulation.
- The two previously missing page styles must render in the head; links and dropdowns remain usable at narrow widths.

## Execution record

User approved this small change in chat. Reuse clean linked worktree at `codex/defense-readiness-20261102`; do not overwrite primary's unrelated dirty changes. One implementation task, followed by fresh independent review. Subsequent explicit owner confirmation authorizes push/deploy once verification passes, on the existing Free service only.

- RED: six rendered tests /13 subcase failures before implementation; GREEN6/6.
- Added real-path navigation case; focused80/80, JS61/61; mapping score RED→GREEN11/11.
- Fresh reviewer found approval CSS leaking to outer shell, source-label inference and compressed phone header. Browser reproduced padding24px/12px8px and non-stacked controls; fixed all in one pass. Chrome15 page/viewport cases now pass, no page errors, no horizontal document overflow; no database or production calls.
- First full run1691/337.383s: one manifest-inventory failure for new test file. Added inventory only, without changing97progress or weakening guard. Final full1691/1691 passed359.948s,0failure/error/skip; disposable TEST DB destroyed and source/protected hashes unchanged. UI+manifest13/13 passed2.039s, JS76/76 passed3.116s and5transportgroups passed.
- Ruling: source-only task; no attempt to improve historical forecast results by altering model/data. Primary differs from release in mapping and recommendations; bulk patch failed atomically. Preserve those differences rather than overwrite released prerequisites or user work.
