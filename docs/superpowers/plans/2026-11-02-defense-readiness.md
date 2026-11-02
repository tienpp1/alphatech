# Academic defense readiness implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkboxes for tracking.

**Goal:** Repair confirmed end-to-end blockers and complete bounded proposal gaps.
**Architecture:** Keep existing Django/DRF models and workspace/RBAC services.
Independent public, mapping/GIS and chat changes have separate file ownership;
forecast advisory integration reads existing saved runs without training or SQL tools.
**Tech Stack:** Django, PostgreSQL/PostGIS, vanilla JS, existing test runner.
**Spec:** docs/superpowers/specs/2026-11-02-defense-readiness-design.md

## Global Constraints

- Preserve the approved Word and the structure/progress of the 97-item ledger.
- No schema migrations, data resets, fabricated production records, grants or paid APIs.
- Preserve workspace/RBAC, Google-public-only identity, CSRF and independent approval.
- Vietnamese user-facing UI; no visual redesign or replacement of existing services.
- New tests reproduce actual defects RED before fixes; retain old tests/assertions.
- One heavy test/ML job at a time; root alone commits/releases and edits shared docs.
- Accepted no-live-LLM, historical data, local storage and Render Free boundaries remain.
- Exception explicitly approved02Nov after live readback: add only existing
  service.view_task/view_schedule to globalEMPLOYEE, with reviewed read-only
  plan, protected-state checks, atomic audit and no other grant/membership write.

## Review Focus

- First-ever anonymous visit with no form-page cookie and failed cart POST.
- Cart edits while checkout totals refresh, empty-cart edits and network ambiguity.
- Stored quotes/HTML/event-handler text in product/import/GIS fields.
- Opposite-domain active workspace, staff-only PII readers and forged selectors.
- Backward chat history while forward polling advances or access is revoked.
- Forecast dates/model provenance/observed comparison and historical advisory misuse.

### Task 1: Public customer flow safety and checkout coherence

**Files:** templates/public/base_public.html, checkout.html, products.html, home.html quick-add script and product_detail.html as required; apps/public_web/alphatech_ai.py, checkout_review.py and cart/checkout view methods as needed; tests/test_defense_public_flows.py; tests/js/public_defense_flows.test.js.
**Interfaces:** Existing cart JSON API remains authoritative; dispatch a documented successful-cart-change event for checkout, without replaying uncertain POSTs. Existing guest success route remains ownership protected.

- [x] Write/execute failing fresh-cookie CSRF, drawer-injection, stale-summary and guest-link tests.
- [x] Bootstrap token through the shared shell; use safe DOM text/attributes/URLs; safely refresh the entire checkout review and gate its submit while unknown. Remove failed-POST GET fallback; report errors.
- [x] Preserve form drafts and fulfillment computations. Test failed update/no mutation, empty cart, latest totals, foreign guest denial and old regressions.
- [x] Verify signed UI review against locked server products before placement. A late cart POST cannot change a reviewed order; reject stale/missing/invalid review before business writes, retain submitted draft. Retire state-mutating GET after confirmed POST-only shipped-caller inventory. Version drawer reads against later mutations.
- [x] Run focused Django and actual shipped JS tests; capture output and obtain scoped review.

### Task 2: Mapping and internal GIS correctness

**Files:** apps/mapping/services.py; templates/integration/import.html; templates/mapping/mapping_studio.html; apps/gis/views.py; templates/retail/gis.html; templates/service_ops/gis.html; scoped new tests.
**Interfaces:** Real Task.assigned_to relation; existing preview/apply envelopes; explicit X-Workspace-ID on GIS fetches using page context, existing permission codenames.

- [x] Write/execute failing Task apply, hostile preview/popups, partial/zero import and opposite-workspace/staff-only PII regressions.
- [x] Correct the field; render data as text; show partial counts and retain errors; bind every GIS API read to the authorized page workspace; remove is_staff-only PII bypass, retain explicit permissions/superuser.
- [x] Run mapping/import/GIS regressions and behavioral JS harnesses, preserving deny/rollback cases.
- [x] Obtain scoped review; no route/domain/security redesign.

### Task 3: Older chat history and independent-session evidence

**Files:** apps/notifications/chat_service.py, views.py, ui_views.py as needed; static/js/internal_team_chat.js; templates/notifications/team_chat.html (actual path to inspect); scoped tests.
**Interfaces:** Existing workspace selector and 3-second polling. Add mutually exclusive positive before_id paging, <=50 rows, chronological response. Keep forward cursor separate from backward page cursor.

- [x] Write/execute >100-message backward paging and independent manager/employee client tests, including foreign selector/revocation.
- [x] Add accessible Vietnamese load-older control; prepend/de-duplicate without losing scroll position or overwriting draft. Handle failure/hidden tabs and exhaustion without polling gaps.
- [x] Run collaboration Django/JS regressions and scoped review. No new model/WebSocket/provider.

### Task 4: Saved forecast to explainable advisory rule

**Files:** apps/recommendations/forecast_rules.py (new focused module), rules.py, views.py, services.py and templates/recommendations/index.html only for integration/presentation; tests/test_forecast_backed_recommendations.py.
**Interfaces:** evaluate_forecast_recommendations(workspace, *, include_historical=False) -> list[Recommendation]; existing evaluation endpoint accepts explicit boolean include_historical_forecast. Existing recommendation state exposes advisory/historical status.

- [x] Write/execute source-run/date/observed comparison RED tests and endpoint/RBAC/idempotency tests.
- [x] Implement spec's daily revenue >10% decline rule, saved-model/source references, eligibility guards and serialized dedup. Invoke from existing evaluation with historical opt-in only; malformed flag returns400.
- [x] Historical outputs cannot become current executable recommendations or approvals. Existing observed rules/actions remain unchanged.
- [x] Run recommendation/forecast/approval regression groups and scoped review.

### Task 5: Whole-system verification and defense handoff

**Files:** docs/DEFENSE_READINESS_2026_11_02.md (new); docs/CURRENT_STATUS.md; docs/CHANGELOG_AI.md; docs/PROJECT_CONTEXT.md only changed contracts; existing CI workflow only to include new regression commands.
**Interfaces:** Dated source/route/Word/evidence matrix. No changes to approved Word or 97 ledger.

- [x] Run full test suite on isolated TEST DB with source fingerprints, all JS regressions, check/drift, configured security scans. Retain intermediate failures and fix causes.
- [ ] Exercise real HTTP journeys and attempt browser customer/manager UAT; identify tooling/auth/provider gates distinctly.
- [x] Fresh whole-branch review and regression verification of important findings.
- [ ] Produce Vietnamese report with exact tested source/counts, repairs, proposal alignment and accepted scope exceptions. Commit/push/deploy only after evidence gates, keeping the dirty main workspace untouched.

#### Security gate extension after first full run

Actual installed-package audits found outdated application and tooling dependencies.
Add only security floors for existing dependencies and patched installer bootstrap;
no new feature/model/schema, no global Python upgrade or changes to numerical study.
Files: requirements.txt, build.sh, quality.yml, test_dependency_security_floors.py.

- [x] Observe offline policy tests RED, apply floors/branch exclusions and bootstrap,
      then GREEN; preserve every existing CI test/audit and fresh review the delta.
- [x] Create an independent venv without system packages, record exact resolved
      inventory and pip check, audit it without ignoring advisories, and rerun
      framework/full/JS gates. Retain the original old-runtime full receipt separately.
- [x] Disclose the upstream Twisted IMAP advisory's unresolved patch/reachability
      uncertainty; zero package audit is not an application security certificate.

### Task 6: Preserve existing unpublished public demo policy

Late comparison found owner-approved Oct12 code only in dirty main. Restore
isolated hunks, never overwrite defended public files wholesale. Files: existing
main policies.py/policy.html/policies.css/test_public_demo_policies.py/canonical
Markdown as new scoped files here; isolated views/urls/AI/email and public links.

- [x] Record original policy/Markdown hashes; observe original15tests RED for the
      missing implementation, preserve all assertions and cases after restoration.
- [x] Publish narrow AT-DEMO-1.1/date02Nov correction to model-storage wording;
      keep every commercial/demo boundary, original main files and old outbox
      dedup/retry snapshots. Add explicit regression for this factual correction.
- [x] Verify links/routes, consent, copilot, email and latest strict-checkout
      regressions on patched isolated TEST; fresh scoped review, update inventory/CI.
- [ ] Rerun final full source-freeze and release gates after integration; clearly
      distinguish local/HTTP proof from unavailable browser UAT.

Final integrated local full fbb85bb:1591/1591OK337.286s,892inputs unchanged,
own randomizedTEST destroyed;JS73PASS and5transportgroups. No runtime/test/CI
edits after this receipt. Remaining external push/CI/live/HTTP actions are recorded
create-only under D:/AlphaTech_Private/defense_readiness_20261102, not assumed
from these checkboxes. Browser initialization remains an explicitly unverified
visual gate even when local/HTTP/release gates pass.

### Browser-observed follow-up after first live release

Alternative installedChrome headless enabled actual desktop/mobile-size checks,
not interactive Windows or physicalphone. Four scenarios found only retry CSS
visibility defect (62/64); preserve driver-error evidence and do not reset accounts.

- [x] Diagnose hiddenattribute versus authorbuttonCSS in actual browser, scoped
      temporaryCSS/error/retry/recovery hypothesis12PASS; source/render RED→GREEN.
- [x] Restore explicitly approved2EMPLOYEEreadgrants with atomic audit113,
      preserving all other grants/userflags/memberships, no-op retry verified.
- [ ] Verify the final scoped CSS/test source with fresh full/CI/live/HTTP/browser
      receipts before closure; do not reuse first-live or hypothesis evidence.
