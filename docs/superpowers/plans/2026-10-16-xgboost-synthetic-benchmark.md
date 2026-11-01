# XGBoost Synthetic Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build and execute an honest, bounded offline synthetic revenue benchmark comparing real XGBoost with MA7 and other existing baselines.

**Architecture:** Reuse the canonical application feature builder and metrics without Django setup, network or business DB. New scripts own deterministic synthetic inputs, validation-only model selection, nonoverlapping recursive evaluation and immutable evidence bundles. Existing historical failure/runtime remain untouched.

**Tech Stack:** Python, NumPy, pandas, installed XGBoost; unittest and the existing isolated Django test runner for final regression.

**Spec:** docs/superpowers/specs/2026-10-16-xgboost-synthetic-benchmark-design.md (user approved offline scope).

## Global Constraints

- 5 scenarios × 6 fixed seeds × 730 days = 30 standalone synthetic series; no business rows/PII/provider/DB calls.
- Development seeds 2026101601/02/03; final seeds 2026101611/12/13; raw chronological 438/146/146 split.
- 12 fixed XGB candidates: objective squarederror/absoluteerror × depth2/4 × trees100/250/400; random_state42/n_jobs1; other parameters fixed to reference.
- Candidate selected on development validation only, equal per-series relative MAE, positive MA7 denominator required, fixed tie order. Missing/failed series invalidates candidate.
- 10 nonoverlapping14-day blocks per146-day partition; disclose6 omitted trailing days. No actuals within a forecast block, no refit between origins.
- Save protocol/data/source hashes before training and selection before final fitting. Preserve failures; no automatic retry/tuning or overwrite.
- No production/runtime/schema/97 changes; reduce resource pressure with one heavy process/native thread1.

## Review Focus

- Corrupt/truncated checkpoint or changed protocol/source must never silently resume as success.
- Candidate failure on one series must not win by omitting that series.
- Final target mutation must not change selection or the evaluated model/first-origin forecasts.
- All-zero/degenerate inputs need honest undefined ratios/R² rather than invented gains.
- Report must include every seed/scenario/failure; no winner-only selection.

## Task 1: Deterministic synthetic data and frozen protocol

**Files:** Create scripts/forecast_synthetic_data.py; tests/test_forecast_synthetic_benchmark.py.

**Interfaces:** `make_series(scenario: str, seed: int) -> DataFrame[target]`; `freeze_inputs(output: Path) -> dict`; `build_protocol() -> dict`. Downstream reads dataset.csv/metadata.json indexed date and immutable protocol.json.

- [x] Write tests: assert 730 finite nonnegative daily rows, deterministic same seed/different noise seed, unknown scenario rejected, all30 files labeled synthetic/no business writes, chronological438/146/146, no overwrite.
- [x] Run unittest task1, observe feature absent RED; implement fixed formula/calendar/noise/control scenarios and freeze metadata/source hashes.
- [x] Run task1 GREEN; record commands/results, preserve existing source untouched. Integration commit deferred until all evidence/review is complete to avoid partial dirty-worktree integration.

## Task 2: Validation selection and recursive evaluation

**Files:** Create scripts/forecast_synthetic_benchmark.py; extend same test module.

**Interfaces:** Consume task1 inputs; `origin_blocks(partition, horizon=14) -> list`; `evaluate_methods(models, history, partition) -> DataFrame`; `select_from_scores(trials, expected_case_ids) -> dict`; `fit_xgb(history, params) -> (model, columns)`.

- [x] Write hand-checkable tests:146dates→10blocks/140unique/6omitted; recursiveMA7 first value27 and second192/7 for history1..30; selected mean ratios accounts for all cases; a failed/missing case invalidates candidate; zero baseline invalidates ratio; models trained strictly before final target.
- [x] Observe RED; implement using canonical build_features/recursive_feature_predictions/evaluation (do not duplicate feature math). Clamp predictions nonnegative like runtime.
- [x] Run task1+2 GREEN and existing offline/feature/metric regressions. No assertions demanding XGB wins.

## Task 3: Durable bounded run and evidence

**Files:** Extend runner/test module; ignored output/forecast_synthetic_20261016 is evidence only.

**Interfaces:** `run(output: Path, resume=False) -> dict`; CLI `--output PATH [--resume]`; phase statuses INPUTS_FROZEN/SELECTED/EVALUATING/COMPLETED/FAILED. Completed case receipts include artifact hashes and source/protocol identity; case failure retained with sanitized class.

- [x] Add RED tests for no-overwrite, corrupt/changed checkpoint rejection, failed candidate retention/all-invalid search, real small XGB integration, hash verification/replay and final target perturbation isolation.
- [x] Implement checkpoints and final per-case CSV/model/metrics with same reference/baseline histories. Final score aggregate includes15finalcases and both positive/negative outcomes; no inference DB writes.
- [x] Run GREEN; freeze full30inputs/protocol before training; execute one background hidden process with threads1; read checkpoint/log/result and retain interruptions as interruptions.
- [x] Replay a representative real model/prediction case from frozen inputs and verify hashes; recompute aggregate directly from saved predictions as independent arithmetic check.

## Task 4: Review, broad regression and truthful report

**Files:** Create docs/XGBOOST_SYNTHETIC_BENCHMARK_2026_10_16.md; append scoped receipts CURRENT_STATUS/CHANGELOG_AI; no97 ledger changes.

**Interfaces:** Results from task3; user-facing report distinguishes synthetic vs restored history, selectedXGB vs reference, recursive vs one-step, and currentproduction unchanged.

- [x] Read requesting-code-review; fresh reviewer inspects new files/spec/plan and tests for above review-focus cases; fix Important/Critical using RED→GREEN, preserve failures.
- [x] Run existing isolated full-suite wrapper safely against disposable TEST only; check migration drift/systemcheck and git diff --check; do not reuse14/10PASS for new source.
- [x] Verify source/data/97 hashes, complete all-case receipts, final-command exit status; document exact counts/time, exceptions, deferred minor/rulings and limits. Do not commit/push/deploy or claim universal/model commercial superiority.

## Execution notes

User explicitly requested autonomous completion and approved offline design. Use inline implementation plus one fresh final reviewer, not a new implementer for every small function; preserve source/tests owned by other work. Resolve worktree preference before implementation and keep this plan's progress on disk. No repetitive continuation approvals between tasks.
