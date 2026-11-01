# XGBoost Calendar Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce weak-noise calendar overfit with a past-only per-series feature gate, preserving pure XGBoost and honest evidence.
**Architecture:** Three feature subsets wrap unchanged V2 normalized direct XGB; select with frozen one-SE validation, refit before fresh final, retain V2 comparator.
**Tech Stack:** existing Python/NumPy/pandas/XGBoost/unittest; no dependency install.
**Spec:** docs/superpowers/specs/2026-10-19-xgboost-calendar-selection-design.md

## Global Constraints

- No V1/V2 source/artifact, main dirty source, runtime app, database or97-ledger mutations.
- Fixed3modes/alpha1/modelparams;65series/50freshfinal; never final tuning or seed/scenario branches.
- Calibration[:438]→[438:584]; refit[:584]→[584:730]; all selections precede any final.
- One heavy thread-capped job, checkpoints, no network; no commit/push/deploy.

## Review Focus

- Feature filtering must persist across save/load and exact prediction reconstruction.
- Refit must not contaminate calibration or choose mode from outer final targets.
- One-SE tie/zero variance/invalid partial inputs must select deterministically or fail closed.
- Resume must bind selected featuremode and receipts/source/runtime, retaining failures.
- Matched observations/completecases and every old/fresh loss must survive metric summarization.

### Task 1: Calendar-mode XGBoost and selector

**Files:** new scripts/forecast_calendar_selection.py; tests/test_forecast_calendar_selection.py.
**Interfaces:** `fit_mode(history,mode,params=None)` -> CalendarModel; `load_mode(path)` -> same; `choose_mode(losses)` -> selectiondict; model.predict(fullX) subsets saved schema and model.save_model(path) persists it.

- [x] Write/run RED tests for no-calendar invariance, real save/load/schema validation, hand-derived one-SE/ties/zeroSEM/partialinputs.
- [x] Implement minimal wrapper and selector using unchanged V2 history/features/reconstruction.
- [x] Run GREEN +existing12V2tests, record exact results.

### Task 2: Frozen V3 experiment

**Files:** new scripts/forecast_calendar_benchmark.py; tests/test_forecast_calendar_benchmark.py; inventorydoc.
**Interfaces:** Task1fit/select wrapper; V2evaluate/score_rows; V1generator/evidencehelpers;65calibrationreceipts,selections.json,50finalreceipts,results/gates.

- [x] RED tests for cutoff and selection before final, fullcoverage/pairedmetrics, tamper/interruption/resume, failed calibration forbids final.
- [x] Implement create-only protocol/inputs/runtime/sourcefreeze and casebound pipeline; add testinventory without touching old tests.
- [x] Run GREEN; fresh reviewer checks all V3; fix Important/Critical RED→GREEN before freeze.
- [x] Run frozen study once with thread/networkguard, then independent audit +predeclared replay/seen1912diagnostic; keep allresults.

### Task 3: Full verification and delivery

**Files:** dated V3report; CURRENT_STATUS/CHANGELOG_AI receipts; ignored source/evidence package.
**Interfaces:** immutable V3inputs/selection/models/CSV/gates, fullsuite snapshot, hashguard.

- [x] Audit metric arithmetic and selection independently, report everycase andperfamily metrics/limits.
- [x] Fullworktree test suite on own disposable PostgreSQL/PostGIS database; framework/drift/Bandit/compile/diff and V1/V2/97hashguards.
- [x] Package new report/source/evidence onD with verified SHA, no secrets/DB and no production/universal-win claim.

Implementation/evidence tasks complete. Performance acceptance NOT passed:
preservationFAIL (level_shift meanV3/V2=1.0560717900772454>1.05). No promotion.
Packaged plan is the pre-package snapshot; deliveryJSON records actual completed
ZIP/hash verification after this final checkbox became eligible to be checked.
