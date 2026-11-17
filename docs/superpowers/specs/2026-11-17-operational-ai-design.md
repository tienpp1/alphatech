# Operational data and AI integrity — design

Owner request: repair four operational concerns, not merely presentation, use available skills, choose reasonable answers autonomously while the owner is away. Base release ab007d5. Work in the existing linked worktree; preserve the dirty primary checkout.

## Goals and non-goals

1. Correctly ingest actual file/HTTP bytes with traceable, sanitized provenance and no fabricated empty rows.
2. Make mapping suggestions safe, optionally LLM-assisted, and explicitly human-confirmed before any business import.
3. Make forecasting operate on eligible closed-period canonical observations with honest freshness, coverage, horizon and metric semantics. Preserve saved results and the validation-selected MA7/XGBoost engine.
4. Make recommendation acceptance and human approval safely execute the existing canonical domain action only when evidence and permissions are still valid.

Do not manufacture transactions, evidence of partner access or independent model superiority. Actual HTTP retrieval is not evidence that its contents are real commercial transactions. Legacy source classification stays UNKNOWN. No promise that XGBoost always beats MA7.

No new domain model, schema migration, database reset, destructive cleanup or rewriting of existing rows. No change to Word or the 97-item ledger. Retain RBAC, workspace, Google/public separation and audited/idempotent mutations. Real production business mutations remain human actions, not autonomous acceptance testing.

## Decisions delegated by the owner

- Reuse current Django modules and JSON metadata; do not add a parallel integration, forecasting or approval platform.
- Remote integration remains a bounded credentialless HTTP(S) JSON connector unless genuine partner configuration is supplied. Do not invent endpoints, credentials, commercial terms or completeness attestations.
- Add Groq only as explicit schema-only suggestion mode. No raw samples, customer records, business totals, tenancy IDs, connector configuration or provider formulas leave the server. Guard column names and limit schema/output sizes. Use current fixed Groq HTTPS endpoint/model and strict output validation; fail safely to clearly labeled heuristics.
- Keep heuristics as a valid fallback, repair their candidate/type/enum/duplicate defects, and never represent a heuristic score as measured accuracy.
- Evaluate forecast readiness before operational training; retain explicit historical evaluation. Old transactions and frozen holdout scores are never rewritten. Missing observations are not verified zero sales.
- Preserve historical recommendations and approvals. Derive current/history queues without writes on GET. Revalidate evidence immediately before a real mutation; block stale or changed conditions.
- Sandbox E2E uses a randomized disposable loopback PostgreSQL/PostGIS TEST database only. Production verification is login/GET only; provider smoke uses at most two reviewed schema-only calls. No paid-service provisioning.

## Module boundaries

- Integration owns source parsing/config validation/redaction and `ImportJob.source_metadata.ingestion_provenance` (version1). Receipt exposes observed transport, exact consumed byte hash/count, timing and safe endpoint identity. Known local mock implementation may be KNOWN_SYNTHETIC; remote/upload contents remain UNKNOWN. Mapping can carry this receipt identity into its audit, never infer real/synthetic from a name.
- Mapping owns suggestion generation/validation/confirmation and transformation gating. It must keep type/config attached to the chosen target, avoid duplicate targets and implicit lifecycle defaults, and reject foreign source/profile/job binding. Signed server-generated suggestions bind user/workspace/profile/schema and expire. Existing manually configured mappings retain explicit documented semantics.
- Forecasting owns selectors, readiness, fit/evaluation metadata, chart/date alignment and business-day defaults. It does not change recommendation business definitions or call its mutation handlers. No test/demo inference from notes or names.
- Actions owns recommendation freshness/deduplication, approval revalidation/replay and canonical service dispatch. It consumes forecast diagnostics as evidence, not as authority to bypass human review.
- Root owns shared configuration, integration documentation, manifests, CI, source/data census, broad verification and release decisions. Workers must request shared-file edits instead of editing each other's files.

## Acceptance and external limits

Each concrete bug gets a failing regression before the fix and passes afterward. Existing tests must remain meaningful; do not delete, skip or weaken them. Finish with full Python/JS regressions, security/secret checks, independent reviews and browser verification. Separate real provider/HTTP proof from mocked-transport tests, and separate sandbox canonical mutation proof from production UAT.

Engineering completion is not external business acceptance: genuine partner credentials/exports, fresh eligible operational observations and real-world human approvals cannot be invented. Missing items must be reported specifically, with the system refusing unsupported claims/actions rather than silently fabricating success.
