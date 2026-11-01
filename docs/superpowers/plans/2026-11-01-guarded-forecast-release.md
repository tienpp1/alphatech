# Guarded Forecast Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Checkbox steps track actual evidence.

**Goal:** Deploy truthful validation-guarded XGB/MA7 forecasts and portable verified model snapshots without rewriting history.
**Architecture:** Reuse Config/Run/Result, opt-in guarded strategy, unchanged legacy path. Separate pure engine/artifacts, integrate under existing lease transaction, append audited release records only after CI/deploy.
**Tech Stack:** Existing Django/PostGIS/NumPy/pandas/XGBoost; no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-01-guarded-forecast-release-design.md

## Global Constraints

- Preserve tenant/RBAC/public separation,97ledger, dirtymain and frozenV1–V4.
- No migrations/newtables/paidservices/user-role changes/synthetic business writes.
- `guarded_direct_v1`; artifact `alphatech_guarded_forecast_v1`; <=1,048,576UTF8bytes.
- Two calendar modes; default L1/depth2/200/.05/random42/n_jobs1; minfit70/daily/horizon<=14.
- Min49periods; test=max(14,int(n*.2)),val=max(28,int((n-test)*.25)); past-only complete14blocks.
- XGB gate:gain>=10%,gain>3pairedSE,blockwins>=80%,>=2usableblocks; not a confidence guarantee.
- Final serving refit never scores holdout; imputed gaps not scored; all losses/negativeR² retained.
- Explicit apply/new-version/idempotent release only; GitHub/Render verified before Neon activation.
- A selected model that loses matched holdout MAE fails deployment qualification,
  never gets reselected with holdout; publication rolls back only its new rows.

## Review Focus

- Legacy schema/horizons/weekly runs must not be interpreted as normalized residuals.
- Holdout perturbations may change evaluation/serving refit, never selection or initial shadowfits.
- Missing/tampered/oversized artifact and snapshot: failclosed, no path traversal or pickle.
- Lease loss, rollback and retry: no overwrite of old results/configs or double publication.
- MA7 must not be advertised as XGB or data-current when source forecast window is historical.

### Task 1: Pure guarded model and portable artifact core

**Files:** new apps/forecasting/adaptive.py, guarded.py, artifacts.py; new tests/test_guarded_forecast_engine.py and tests/test_guarded_forecast_artifacts.py.
**Interfaces:** Exact functions/result keys/format in spec; no Django/DB imports in core, base_dir/artifacts_dir passed explicitly.

- [x] RED tests for real normalized feature/schema/reconstruction and JSONroundtrip, fixedparams/bounded overrides.
- [x] RED tests for minhistory/weekly/long-horizon explicit fallback, finite/nonnegative input, constant/tie/zero-error baselines.
- [x] RED future-truth perturbation test: selection unchanged; first holdout block prediction unchanged when only its truth changes.
- [x] RED paired arithmetic10%/3SE/80% boundaries, missing-observed blocks and gapmask; no scenario/seed inputs.
- [x] RED trusted-path/SHA/size/strictJSON/snapshot recovery, disk tamper cannot recover silently, save never calls DBsave.
- [x] Implement minimal core; GREEN standalone unittest suites. Tests use tiny real XGB fits; no performance claims from mocks.
- [x] Combined source review and scoped fix; commit only assigned core/test files and new design/plan.

### Task 2: Existing lifecycle, truthful UI and append-only release

**Files:** training.py,prediction.py,services.py,serializers.py,diagnostics.py,academic_reporting.py; templates/forecasting/index.html; narrowly scoped forecast prose in apps/knowledge/services.py/config/views.py if it hardcodes model identity; new management/commands/publish_guarded_forecasts.py; tests/test_guarded_forecast_integration.py and tests/test_guarded_forecast_publication.py.
**Interfaces:** consume Task1 result/artifact APIs. New saved provenance.strategy/effective_model/selection/evaluation, artifact_snapshot body excluded from serializer. Latest active config selection remains scoped; legacy absent strategy unchanged.

Training calls `fit_guarded` with exactly estimator/depth/rate overrides and separate test_size. Engine baseline_metrics is nested ma7/seasonal_naive_7: adapt to existing flat moving_average_7_* and naive_* fields without losing raw dictionaries. New strategy holds no calibrated bounds. `generate_future_forecast` accepts optional `history_snapshot=None` for the same canonical frame used by training; new strategy validates saved dataset fingerprint before predictions. No historical result replacement in publication: append new run, then activate new config only after success. Source hashes include adaptive.py,guarded.py,artifacts.py,prediction.py for new strategy. Guarded provenance records actual evaluation method, actual model label, candidate params vs selected baseline and serving-refit history; no raw holdout_rows or native booster in provenance/API. Run serializer must not mutate the original job_parameters while redacting body. Config with no active version but existing disabled entries fails explicitly, never silently reactivates old config. Bounds/legacy outputs remain unchanged for absent strategy.

- [x] RED guarded train/predict real DB integration, source snapshot consistency, legacy compatibility, latest-active config, weekly/long horizon, metadata label and snapshot redaction.
- [x] RED lease loss/no completion, prediction failure/no old-result loss, expected SHA rejection and missing-disk verified-inline inference.
- [x] RED publish command defaults to plan/no writes, explicit apply appends config/run/results, idempotency, rollback and original-row hashes/tenancy.
- [x] Integrate strategy branch within existing train try and final fenced transaction; do not rewrite legacy implementation or metrics.
- [x] Label actual model in chart/quality/template/academic export; preserve stale/R²/baseline warnings and no-key boundaries.
- [x] Implement scoped publication under workspace lock, own config version, new-only activation and truthful system audit.
- [x] GREEN focused suites plus old forecast/queue/RBAC/reporting tests on disposable TEST; fresh review and fixes; commit explicit files only.

### Task 3: Scientific verification, release and Neon proof

**Files:** new scripts/forecast_guarded_benchmark.py/test; dated report; docs CURRENT_STATUS/CHANGELOG/PROJECT_CONTEXT updates; existing quality.yml focused test additions only.
**Interfaces:** core `fit_guarded` and holdout_rows to frozen offline evidence, publication command to explicit Neon subprocess.

- [x] Freeze20new-series inputs/policy/source; run once and preserve every failure/loss/negativeR²; old2236 separate SEEN demonstration.
- [x] Audit raw paired MAE/gates/selection chronology and model roundtrip; do not tune/reseed after final.
- [x] Full worktree suite, framework/drift/Bandit/diff/source freeze and oldartifact/97hash guards; fullfresh branch review (operator preconditions separately addressed before use).
- [ ] Push isolated code branch, verify GitHub CI; fast-forward shared main only with expected oldSHA; noforce or unrelated dirtymain staging.
- [ ] Deploy existing Free Render, verify exact commit/live state and readiness; no paid services or insecure credential workarounds.
- [ ] Private read-only canonical backup/fingerprints; apply append-only Neon release for the two workspace defaults, optionally all four existing targets with --all-targets after qualification.
- [ ] Read-only check model SHA/DB snapshot/in-memory serving, old-row/business invariants, release idempotency and actual labels/HTTP where credentials allow.
- [ ] Report actual outcomes, exact commit/CI/deploy/release IDs and any unverified boundary. Update no97progress.
