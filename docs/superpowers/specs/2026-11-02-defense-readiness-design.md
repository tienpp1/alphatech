# Academic defense readiness repair

## Purpose and authority

Exercise the existing customer and internal-management workflows, fix confirmed
defects, and close implementation gaps against the approved proposal. The source
proposal is the unchanged teacher_review_v2 DOCX with SHA-256
9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
This is not a new platform, a visual redesign, or a rewrite of the proposal.

The owner requests continuous execution and delegates implementation choices.
Keep Django/DRF, existing models/services, Vietnamese UI and Render Free. Preserve
the accepted deterministic/no-live-LLM, historical-data, local-storage and disabled
production async-worker boundaries. Never reinterpret a mock as live evidence.
Preserve the structure and progress of the 97-item ledger.

## Confirmed repair scope

1. Public shell: bootstrap CSRF for first-time guests; remove executable product
   text from the drawer; synchronize checkout review with drawer mutations and
   block submission while its amount/items are stale or unknown. Guest-owned
   tracking links must use the existing guest-session-owned confirmation page.
   Do not weaken CSRF or ownership, or silently mutate cart via failed-POST GET.
   Bind actual browser checkout forms to a signed bounded/expiring server review
   of items/quantities/prices/method/totals and verify it under product locks before
   writes. GET after an aborted POST is not a settlement proof. A missing/invalid
   issued review must fail closed, preserving contact draft and requiring review.
   Legacy direct-POST clients outside the actual browser UI keep their old contract;
   this is not a claim of universal review enforcement for all API clients.
   Shipped cart-add callers are all POST; retire the legacy mutating GET with405.
   Review issuance must not create/write a session; a missing session key yields
   no usable token. The JSON cart/review GET uses a copied read-only cart snapshot,
   not persisted stale-item cleanup. The explicit browser review query enforces
   validation even if a legacy session marker is absent or overwritten.
2. Data integration/mapping: fix Task assignment to its real assigned_to field;
   escape arbitrary source/preview/suggestion values; display partial and zero-row
   apply outcomes truthfully and retain rejection details.
3. Internal GIS: every layer/proximity request must use the page's authorized
   workspace explicitly. is_staff alone must not grant customer-location PII.
   Treat stored names/addresses as text in popups, not executable HTML.
4. Collaboration: retain existing polling; add bounded older-history access to
   the existing chat API/UI. Forward and backward cursors must not interfere.
   Exercise two independent employee/manager sessions, persistence and isolation.
5. Forecast-backed recommendation: connect actual saved forecast evidence to a
   deterministic advisory rule using existing Recommendation types. Start with
   daily workspace-wide RETAIL_REVENUE (existing primary academic target), no
   dimensions. Compare the next complete seven forecast days with the preceding
   seven observed calendar days of COMPLETED-order revenue. A predicted decline
   strictly greater than 10% produces a clearly forecast-based review suggestion.
   This reuses the existing observed-revenue rule's illustrative 10% threshold;
   it is not an approved commercial intervention or a claimed causal effect.

## Forecast evidence contract

Use the latest active target config (updated_at/id) and its latest run
(created_at/id) regardless of status, then require that exact run to be completed
and eligible. Never fall back from a newer bad/incomplete run. Require
workspace-bound config/results and finite nonnegative values. Require complete,
daily, contiguous seven-day predicted dates immediately after dataset_period_end;
do not use actual_value as predictions. Require known training provenance and
actual model label. Reject missing/foreign/failed/cancelled runs, dimensions,
weekly cadence, mismatched result targets, missing dates and invalid provenance.
Do not backfill a bad latest run with an older apparently good result.

Eligibility requires at least 14 observed holdout periods with validated counts.
Guarded runs also require deployment_qualification=true; unknown legacy evidence
is not inferred from current configuration. Default operational evaluation skips
stale runs (source older than seven days or any compared forecast day <= today),
future source dates, unqualified guarded runs and insufficient observed holdout
evidence. An explicit historical-analysis option may analyze stale snapshots,
but must label them HISTORICAL, record dates/limitations, remain advisory and
never create an ApprovalRequest or permit acceptance as a current action.
Missing observations are unknown, not measured zero days: require seven actual
source-observed days for the comparison; a zero total cannot be a denominator.
The baseline is current canonical COMPLETED orders for that historical interval,
read in one aggregate query at evaluation time, not a recovered training snapshot.
Record baseline_source=canonical_completed_orders_at_evaluation and evaluation
time; freeze those aggregates in the first recommendation. A repeat for the same
run never rewrites the comparison even if business records later change.
Historical opt-in bypasses only stale/past dates, never future source dates,
qualification, observed-count, provenance or dimensional guards.
Persist run/model/config/date/result IDs and threshold/comparison facts, not the
native model JSON. Current snapshots retain warnings, negative metrics and MA7
labels. Re-evaluation of the same source run must not duplicate the suggestion;
serialize creation with the existing workspace row lock (no schema migration).

## Engineering and safety

Write reproducing tests before product changes. Use actual Django services and
HTTP clients on randomized loopback PostgreSQL/PostGIS TEST databases. JS harnesses
execute shipped JS; no source-string assertions substituted for behavior. Retain
all previous tests and intermediate failures. No schema/model migrations, production
data seeding, user/permission changes, secret disclosure or paid API/deployment.

Parallel file ownership is allowed for independent repairs; serialize native ML
and full test jobs to avoid prior desktop resource pressure. Root owns commits,
shared docs, broad verification, integration and any authorized release.

## Completion evidence and limits

Run focused regressions, complete Django suite, JS suites, migration/check gates,
security scans and source fingerprints. Review each repair and the whole branch.
Maintain a new dated requirement/route/evidence matrix, not a modified 97 ledger.
Attempt actual browser journeys as customer and manager; record exact failures
of tooling/provider/auth rather than fabricating visual acceptance. At task start
both CUA and Node REPL fail to initialize kernel assets even after reset; HTTP,
database TEST and JS execution evidence must remain distinct from browser UAT.

No finite test suite proves an optimally smooth system on all devices. Report
confirmed improvements, remaining user/external gates and accepted scope
deviations explicitly. Do not activate live Gemini or claim the final report/
slides have been approved; only an approved proposal is currently identified.

## Restoring unpublished owner-approved demo policy

Late source comparison found the owner's Oct12 AT-DEMO-1.0 implementation only
in the dirty main workspace; remote-derived source still sent consent links to
About. This is not an accepted scope omission. Restore its canonical public
module/assets and isolated integration hunks without copying whole modified
files or publishing internal SOPs. Keep all existing15policy test assertions.

Only the outdated all-models-local wording is corrected for the current guarded
ForecastRun JSON snapshots; media/legacy local and noS3/offsite limits remain.
Publish this narrow version as AT-DEMO-1.1 dated02Nov, preserving original1.0
hashes in evidence and leaving dirty-main files intact. Public routes stay GET/
HEAD-only; new email snapshots may carry links/version, but old dedup material
and retry snapshots must remain unchanged. No schema or97ledger changes.

## Explicit operational exception and actual-browser follow-up

Owner approved exactly2existing EMPLOYEE readgrants after live source-vs-role
drift was proven; add-only audited reconciliation, no customer memberships,
management rights or resets. This supersedes only the original no-grants scope
for those two codes, not general authority to change roles.

InstalledChrome headless is available as a separate browser test runner despite
nativeCUA kernel failure. Record viewport-emulated versus physical-device limits.
Its retry-hidden CSS finding is fixed only for the existing ID+[hidden] control,
preserving failed-request visibility, submit gate and all animation/other styling.
