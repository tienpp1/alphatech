# Guarded forecast release — 01/11/2026

## Intent and approvals

User requests a real GitHub/Neon rollout after the remaining V4 noise loss.
User explicitly approves validation selection between XGBoost and MA7, truthful
effective-model labels, and a bounded SHA-verified JSON artifact snapshot in
existing ForecastRun metadata on Neon. No new tables/services/paid hosting.
This replaces the former pure-XGB-only restriction, not the security boundaries.

V4 remains frozen. Its noise2236 loss is1.0068943836×MA7; validation genuinely
favored XGB6.49%, so a simple validation-winner selector does not fix it. This
is finite-sample variation, not proof of leakage or a guaranteed fixable defect.
No claim of universal dominance, no rewriting the99/100 result. An old-case
demonstration of MA7 selection is a SEEN diagnostic, not fresh accuracy evidence.

## Builder decisions (not separately attributed to user)

Use the existing ForecastModelConfig/Run/Result and workspace/RBAC/lifecycle.
New opt-in strategy `guarded_direct_v1`; absence preserves legacy behavior.
Reuse the V4 normalized MA7-anchored direct-horizon mathematics in a cohesive
runtime module, never import benchmark orchestration from scripts in production.
Only none/full calendar schemas; no scenario/seed/case identifiers as inputs.
Fixed candidate defaults: L1/depth2/200trees/rate.05/subsample1/colsample1/
lambda1/random42/n_jobs1; supported estimator/depth/rate overrides must be
honored and recorded. No unbounded parameter injection.

History is finite nonnegative regular DAILY or WEEKLY `target` DataFrame.
The normalized XGB candidate is eligible only for DAILY,horizon<=14 and at
least70 initial fit rows. MA7 is seven periods, not seven days for weekly data.
For validation/holdout require at least49 periods: test=max(14,int(n*.2)),
validation=max(28,int((n-test)*.25)), initialfit=remaining (>=7). test_size may
be honored within existing valid bounds; do not use holdout to select. Shorter
history raises a clear data error. Canonical Neon retail currently90days/74
observed, service125days/66observed; do not fabricate transactions to qualify.

Fit both calendar candidates on initialfit only. Score complete14-period
rolling validation blocks; each origin sees only actuals available before it.
Choose calendar mode with one-SE simplicity (none/full). Adopt XGB only if
mean MAE improves MA7 by at least10%, paired gain exceeds3 sample-SE, and it
wins at least80% of usable blocks (at least2). These are conservative builder
risk heuristics, not calibrated99% confidence or thresholds independently
discovered before seeing V4. Freeze them before any new-cohort execution.
Otherwise select MA7, recording exact reason/losses/eligibility. Predictable
ineligibility is a baseline fallback; unexpected fit errors must not be hidden.

Honor `observed_period_dates` source metadata: imputed zero periods remain features but are excluded from scored
losses. Empty validation blocks are not fake zero losses; insufficient usable
blocks selects MA7. Holdout without observed truth must fail, not invent metrics.
All model/MA7/seasonal-naive comparisons use paired identical origins/truth.

After selection refit XGB (if selected) through validation, evaluate heldout
complete blocks, freeze metrics, then refit serving XGB on all available history.
Never evaluate heldout using the final serving refit. MA7 model metrics are MA7,
not mislabeled XGB candidate metrics; persist selected type/reason/columns,
partition dates/counts, actual params, evaluation method, source observed policy.
Negative R², null undefined metrics, all losses and stale-source labels remain.
No calibrated interval claim; guarded prediction bounds may remain null.

Runtime promotion has a separate deployment qualification: if the already
selected model loses to matched MA7 on holdout MAE, refuse completion/promotion
and retain the reason. This is NOT holdout-based model reselection: do not switch
to MA7 after observing holdout. Normal training records a failed new run; the
publication transaction rolls back its new rows. Old runs remain untouched.
Qualification is reported separately from selection and research scores;
accuracy of only the published subset is not an unbiased holdout estimate.

## Runtime interfaces

`apps.forecasting.adaptive`: normalized direct features/fit/predict/JSON helpers.
`apps.forecasting.guarded.fit_guarded(series, *, horizon=14, granularity='DAILY',
 params=None, test_size=.20, observed_dates=None) -> dict` returns artifact,
 selection, model_metrics, baseline_metrics, feature_importances, evaluation,
 and holdout_rows. Holdout_rows are for controlled diagnostics, not copied into
 public metadata or database provenance. Artifact format
 `alphatech_guarded_forecast_v1`, effective_model MA7 or XGBOOST_DIRECT, calendar
 mode, columns, params and native booster JSON when applicable.
`predict_artifact(artifact, history, horizon=14, granularity='DAILY') -> ndarray`.
An XGB artifact cannot silently change to MA7 for an unsupported later horizon.

`apps.forecasting.artifacts.save_run_artifact(run, payload, *, base_dir,
 artifacts_dir)` writes an atomic trusted-directory JSON and sets artifact_path,
 provenance.artifact_sha256 and job_parameters.artifact_snapshot, without DBsave.
`load_run_artifact(run, *, base_dir, artifacts_dir) -> dict`: verify path, SHA,
 UTF8 JSON/format, strict finite/unique-key JSON and <=1,048,576bytes. Disk
 mismatch is an error, not silent recovery. If disk is missing, verified Neon
 snapshot may serve in memory without writing filesystem/GET side effects.
Snapshot stores body string, bytes, format and SHA, never pickle or executable.
Run serializer strips body (but exposes small artifact/serving metadata).
Saved payload adds binding scope(workspace_id,run_id,target_type); loading
rejects a foreign binding even if its hash matches. Standalone engine artifact
need not have scope; storage adds it without mutating the caller's dictionary.
Snapshot keys are body,bytes,format,sha256; body is canonical UTF8JSON text.
Metadata effective_model is MA7 or XGBOOST_DIRECT; baseline artifact has null
booster/calendar_mode and empty columns. Engine tolerates the storage scope.
Result keys from fit_guarded are artifact,selection,model_metrics,baseline_metrics,
feature_importances,evaluation,holdout_rows. Store raw unrounded MAE in selection;
UI metrics can retain existing rounding. Validation/holdout rows pair date,
origin,step,actual,prediction,ma7,naive,observed. Core uses no scenario/seed ID.

Training dispatches only opted-in config, preserves final lease fencing and
atomic completion/results. Prediction uses saved strategy/config, legacy loader
unchanged. A supplied training history snapshot prevents a second-fetch race;
new strategy validates its source fingerprint. Extend provenance source hashes.
Default config resolution chooses latest active version; no historical config
deactivation/deletion. UI/chart/report/assistant quality uses actual model label.

## Append-only release on Neon

Management command `publish_guarded_forecasts --release-id <id> --workspace
 <code> [--workspace ...] --apply` defaults to read-only plan. Explicit apply
allocates a new version under workspace lock, uses canonical target aggregates,
creates only new config/run/results plus audit, activates new config only with
successful completion. One release/workspace/target is idempotent. On failure,
transaction rolls back new records; old results/configs/business data untouched.
System audit actor must be truthful, never impersonate a human approver.

Default targets remain retail revenue and service ticket volume. Optional
`--all-targets` includes the existing retail order-volume and product-demand
targets too; all four remain subject to identical qualification. Idempotency is
release/workspace/target scoped. No new domain target is introduced.

Deployment order: tested code -> GitHub CI -> verified existing Free Render
deployment -> Neon append/promotion -> read-only serving/model snapshot checks.
No synthetic transactions, copying local demo, reset/restore, role/user changes,
97ledger changes, or paid infrastructure. Local .env DATABASE_URL points at old
staging: do not silently switch development onto production. Use explicit Neon
DSN only in guarded operator subprocess, no credential printing/committing.
Pooler probe uses READ ONLY transaction/SET LOCAL, not unsupported startup options.
Capture private before/after old-forecast/business fingerprints and release receipt.

## Evidence and stopping condition

Preserve all V1–V4 sources/results/archives. New study uses unchanged V1 generator
and frozen20cases (five families×seeds2026110121..2026110124), no reseeding after
final. Freeze policy/sources/input manifests first; native/thread1/offline job.
Show all raw predictions/metrics; mean ratioMA7<=1, worstcase<=1.15, weekly and
trend group means<1 plus chronology/integrity gates. FAIL is retained and blocks
production activation, not relaxed. Old2236 diagnostic scored separately.
Local fullsuite on disposable loopback PostgreSQL/PostGIS; no weakened/skipped
tests. Security/source/artifact/schema checks and fresh review before push.
Do not report external success without actual CI/deploy/Neon evidence. Missing
authority/credentials/provider state is reported and asked for, never simulated.
