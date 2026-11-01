# XGBoost Level-Adaptive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair absolute-level non-adaptation offline and measure fresh fixed-seed performance honestly.
**Architecture:** Past-only MA7-anchored, scaled direct-horizon residual XGBoost; standalone V2 experiment reuses unchanged V1 evidence primitives and generators.
**Tech Stack:** Python3.14/NumPy/pandas/XGBoost3.4.1,unittest; no new dependency.
**Spec:** docs/superpowers/specs/2026-10-19-xgboost-level-adaptive-design.md

## Global Constraints

- Offline synthetic only; no database/network/runtime/migration/97-ledger changes.
- Preserve V1 sources, outputs and all tests; no tuning after fresh final opens.
- Frozen4fits×2alphas grid; 15development/25final cases; equal-case MAE ratio.
- Scope is worktree only; no commit/push/merge/deploy, retain evidence ledger.

## Review Focus

- Horizon targets must remain inside training cutoff; future actuals never enter features.
- Zero/spiky levels must produce finite nonnegative predictions, not divide by zero.
- Baselines and candidate share exact origins,targets,horizons; no unseen oracle labels.
- Resume must reject changed source/runtime/receipt and retain failed artifacts.
- Metric gates and selection must use unrounded complete-case values, never final tuning.

### Task 1: Direct normalized residual model

**Files:** Create scripts/forecast_level_adaptive.py; tests/test_forecast_level_adaptive.py.
**Interfaces:** `supervised_pairs(history,horizon=14)` -> (X,y,weights,trace); `fit_direct(history,params)` -> model; `predict_direct(model,history,dates,alpha=1.)` -> ndarray. No database imports.

- [x] Write failing tests: hand-derived anchor/scale/reconstruction; pairing cutoff; input rejection; zero/constant; real model replay and recent-level shift.
- [x] Run unittest file; expected missing implementation assertions, not test typo.
- [x] Implement model/features with single origin snapshot for all14days; persist explicit schema/params.
- [x] Run new tests and existing18synthetic tests; expect all pass, no weakened assertion.

### Task 2: Frozen V2 orchestration

**Files:** Create scripts/forecast_level_benchmark.py; tests/test_forecast_level_benchmark.py.
**Interfaces:** Task1fit/predict; V1make_series,origin_blocks,recursive_baselines,fit_xgb,evidence helpers. `freeze/run/resume` and results with numeric gate status.

- [x] Write failing tests: immutable inputs/runtime; candidate selection excludes final; failed/incomplete/tampered receipt; equal unrounded ratio; final predictions invariant to future at first origin.
- [x] Run tests RED; implement locked8candidate protocol +40inputs + checkpointed dev/final artifacts, direct vs recursive explicit.
- [x] Run GREEN and combined three synthetic modules; add newtest inventory without changing old tests.
- [x] Freeze protocol before any fitting; run once in background,threads1,network guard; retain logs and failures.

### Task 3: Review, audit and delivery

**Files:** New dated report; append CURRENT_STATUS/CHANGELOG_AI; inventory doc only; ignored evidence package.
**Interfaces:** Frozen experiment manifests,CSV/model/selection/results; existing full-suite snapshot helper.

- [x] Independent review of implementation and protocol; fix Important/Critical with RED→GREEN, ledger minor issues.
- [x] Independent arithmetic/hash audit and real saved-model replay, no fitting for audit; all gates report actual outcome.
- [x] Run project full-suite snapshot, Bandit/compile/diff checks; compare runtime/V1/ledger hashes.
- [x] Write report and package isolated source/evidence with SHA; no secrets or database dumps, no universal/prod superiority claim.
