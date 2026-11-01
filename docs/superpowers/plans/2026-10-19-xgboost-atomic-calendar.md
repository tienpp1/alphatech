# XGBoost Atomic Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound calendar ablation to full/none, preserve V2 quality with past-only selection and honest fresh-seed evidence.
**Architecture:** Reuse V3 real model adapters and immutable V1–V3 primitives; add two-mode selector and separate frozen experiment, never modify runtime/oldstudies.
**Tech Stack:** Existing Python/NumPy/pandas/XGBoost/unittest; no installs.
**Spec:** docs/superpowers/specs/2026-10-19-xgboost-atomic-calendar-design.md

## Global Constraints

- Offline managedworktree only; no production/DB/schema/97/oldsource mutation.
- Fixed2modes/fixedparams/alpha1,115series/100final;10sourcehashes; one final protocol.
- Shadowfit438/validate140; freeze115choices; refit584/final140. Never final tuning.
- All V3gates retained; add overallV2<=1 +finiteV2; keep every loss.
- Onehiddenheavyjob/thread1/networkguard; no commit/push/deploy.

## Review Focus

- V4 cannot load/fit weekly schemas or silently change prior full/none outputs.
- Selector requires complete2×10finite losses and deterministic ties, rejects overflow.
- Every selection precedes final; failedcalibration forbids all final evaluation.
- Resume bindssource/runtime/case/selection; no retry silently erasing failures.
- Allpairedtruth/metrics and full100uniqueexpectedcases gate; badV2ratio cannot pass.

### Task 1: Atomic calendar model/selector

**Files:** new scripts/forecast_atomic_calendar.py; tests/test_forecast_atomic_calendar.py.
**Interfaces:** `fit_atomic(history,mode,params=None)` -> existingCalendarModel; `load_atomic(path)` -> same; `choose_atomic(losses)` -> selected_mode/best_mode/SEM/threshold/means/rule. Onlynone/full.

- [x] RED4tests: hand1SE9±3/SEM1/tie/zeroSEM; invalidpartial/bool/NaN/overflow; realfit/load/invariance; weeklyfit/load rejected.
- [x] Minimal wrapper reusing V3 without editing it; pure2mode selector.
- [x] GREEN new4+existing21, record real output.

### Task 2: Frozen V4 experiment

**Files:** new scripts/forecast_atomic_benchmark.py; tests/test_forecast_atomic_benchmark.py; inventorydoc.
**Interfaces:** `protocol/freeze/verify/calibrate/outer/gates/run`; Task1fit/select -> unchangedV2evaluate/score +V3gates +V1caseevidence.

- [x] RED5tests:115freshinput/runtime/tamper; realfutureperturbation+fitcutoff;115failuresretained/no final; allchoices frozen+resume rejects tamper; overallV2/nonfinite gate handarithmetic.
- [x] Implement boundedpipeline/receipts/checkpoints, finitecomplete gates, overallV2 field; update inventory.
- [x] GREEN25+5tests; onefreshwhole-code reviewer, fix Important/Critical RED→GREEN before freeze. Two added review regressions:32/32 OK189.837s.
- [x] Run once115calibration then100final; independentaudit,2predeclaredreplays,2oldSEENdiagnostics; keep FAIL if it occurs. V4all10gatesPASS; oldFAILunchanged.

### Task 3: Verification and delivery

**Files:** datedV4report/CURRENT_STATUS/CHANGELOG; ignoredaudit/full/packagingreceipts.
**Interfaces:** Immutableinputs/selections/models/CSVs -> independentaudit/fullsourcefreeze -> hashverifiedDdelivery.

- [x] Independent metrics/oneSE/modelJSON/hash audit, report completecase/horizon/family/overall/performanceflags; no phantomtestcount. Main+seenPASS/0errors.
- [x] Fullworktreesuite on ownTESTDB; framework/drift/Bandit/compile/diff; oldstudies/97/businessCSV hashguards.1452/1452OK312.229s/0skip/775sourceunchanged;handoff609non-doc/old2140+new1310entries/97CSVpreserved.
- [x] New report/source/evidence ZIP onD, verifyeveryentry/hash; no production/universalwin claim, no overwriteoldarchive. Preserveworktree.1454entries/16576706bytes/readbackPASS/old3archivesSHAunchanged;Task3task-donepackageexit0.
