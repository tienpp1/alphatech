# Online AI demonstration design

User request: push and deploy the prepared algorithm demonstration to the existing
Render website for the defense. Owner previously delegated implementation choices
and questions; proceed with safe defaults, not a new paid service. User explicitly
approved push/deploy. This is a separate online lab, not a production database seed.

## Architecture and scope

Add `/noibo/mo-phong-ai/` to the existing internal Django application and a
CSRF-protected POST `/noibo/mo-phong-ai/run/`. Reuse authentication, selected
workspace, roles, base template and pure algorithm components. No new domain
models, migrations, dependencies, provider calls or business-data writes.
Normal existing login/session middleware remains unchanged.

The local launcher/source worktree at155ee33 is immutable for the existing demo.
Work in the new managed online-ai-demo checkout, branch
`codex/online-ai-demo-20261118`. Do not touch dirty D:/ primary or its .env.

Render remains on the existing Free service srv-dafrcr5g1s2s73frbl1g/main;
no paid compute/storage, new services or changed production LLM/DB settings.
Official Free compute:512MB/0.1CPU; no persistent disk. Avoid training in a
web request. Pretrain the exact pre-holdout model offline and commit its bounded
native JSON plus synthetic CSV; Render executes inference and recalculates scores.
Make that distinction explicit in the UI and handoff; never call this live training.

## Demonstrations

Allow exactly these fixed cases, no arbitrary questions, uploads, model parameters,
object IDs or workspace selectors in the POST body:

1. `forecast`: existing weekly_calendar seed2026110121,730 daily synthetic rows.
   Select calendar/model by existing past-only validation. Freeze the584-row
   pre-holdout XGBoost model, not the730-row serving refit. Call existing
   guarded prediction over ten fixed14-step origins and recalculate MAE/RMSE
   for140 paired targets against MA7 and seasonal lag7. Show actual model,
   training cutoff, holdout146/140 scored, elapsed time and sample rows. Expected
   known reference MAE:896681.5191052415 /4919190.032356063 /2181772.22 approx;
   these are test references, never response constants. Six dates omitted by
   the fixed complete-block protocol; no holdout-driven reselection/retraining.
2. `retrieval`: canonical deterministic hash embedding, cosine and lexical scores
   on two fixed Vietnamese synthetic snippets and one fixed query. Return source
   excerpt and deterministic extractive answer. Label retrieval-component demo,
   no live LLM, no semantic-embedding API or full production RAG certification.
3. `mapping_pending` and `mapping_confirmed`: same fixed Customer row/columns,
   canonical heuristic suggestions and unsaved MappingRule objects. Real transformer
   skips pending rules and transforms accepted ones. Show before/after/errors;
   no canonical import is applied. Confidence is a heuristic match, not accuracy.
4. `recommendation`: canonical technician scoring on fixed fictional candidates,
   explicit distance/workload weights0.5/0.5 and skill0, availability gate.
   Include canonical tool metadata and schema-only contract validation with
   `check_domain=False`. Approval stages are illustrative/previews: no approval
   executor, real object lookup or persisted audit. Link this distinction to the
   actual authorized business features without automatically invoking them.

Global label: `DEMO — dữ liệu mô phỏng; không ghi dữ liệu nghiệp vụ; không gọi
dịch vụ AI`. Show exact mode per result and generation time. No simulated email,
policy, fixture entity or algorithm score is presented as commercial evidence.
Do not mix the separate112-day native local forecast with this730-day lab.

## Security and runtime

Both methods and navigation share one policy function on the currently verified
request.active_workspace. Denied/missing/inactive context always rejects, even
for superuser; the lab must never search another workspace for a permission.
Existing middleware's session/default resolution remains unchanged, including
replacement of a revoked old session choice with an authorized default. The
lab uses and displays the resulting verified selection; explicit invalid,
blank or conflicting request selectors are rejected. No new claim of globally
fail-closed stale-session behavior is made. Internal non-Google active
MANAGER/ADMIN with forecasting.manage_forecast in this workspace may access;
eligible existing superuser follows canonical internal policy. Employee or a
manager only in another workspace cannot use a misgranted permission to bypass.
Reject malformed/blank/conflicting explicit workspace selectors consistently.

GET renders only, no fit/inference. POST requires CSRF, form-urlencoded body at
most512bytes, one allowlisted case and optional single CSRF field; extra/duplicate
fields and unsupported methods fail. One process-local nonblocking execution
lock returns409 busy; no automatic retry. Never accepts caller-supplied artifacts.
Load fixed bounded assets with SHA and cutoff/schema/row-count checks; reject
corrupt inputs. Do not expose booster JSON in responses. Use existing pure
prediction APIs; no fit call during serving. Catch safe failures without private
paths/keys and return a truthful503. Responses no-store; previous UI result may
remain only if labeled as the previous successful execution, with its timestamp.

## UI and verification

Vietnamese, existing dark internal shell, single scenario selector and run button,
readable numeric tables and explanations. No new fonts/CDNs/chart packages. Use
associated labels, visible keyboard focus, busy status/disabled button, explicit
success/error and reduced-motion. No page-wide horizontal overflow at375px,
812px landscape or1440px; wide tables may have labeled inner scrolling.
Add conditional AI-menu item `Mô phỏng AI` only for the same eligible policy.

TDD boundaries: anonymous/customer/Google/employee/revoked/cross-workspace deny,
CSRF, invalid bodies/methods, no compute on GET, asset corruption/leakage, real
inference parity and numeric recomputation, no provider/domain writes for all
cases. Keep tests intact; register new modules in academic test inventory.
Update CURRENT_STATUS, CHANGELOG_AI and PROJECT_CONTEXT for new boundary; keep
teacher Word and97 ledger unchanged. Full local suite, security/JS/UI checks,
independent review, then branch CI success on exact SHA, fast-forward main and
verify exact Render LIVE SHA plus authenticated online button execution.

Chosen defaults are controller decisions to preserve Free reliability and data
integrity; they are not claims that the owner specifically chose offline training.
