# Review of the September 7–8 updates

This is a source review and focused regression checkpoint, not a full-system certification.
Most application files remain untracked relative to the last Git commit, so exact
per-agent attribution cannot be established from Git history. Changelog claims
were checked against relevant source, not accepted as evidence of verification.

## New functionality found

- Public Copilot and JSON cart API; public homepage and navigation updates.
- Executive printable report, CSV export, browser-local inline editing.
- AI/GIS telemetry page and academic evaluation command/documents.
- New permission fallbacks on retail/service analytics and assistant UI.
- Changelog reports manual promotion of accounts to superusers. This review does
  not change accounts or confirm that those promotions were intended.

## Corrections implemented

- Removed catalog-to-analytics and Knowledge-to-chat permission fallbacks.
- Copilot order lookup uses explicit authenticated ownership or the guest order
  session, exact order codes, and no nonexistent Order.delivery_method field.
- Report/export/telemetry require existing capabilities within each workspace;
  membership alone is insufficient. Audit counts are workspace scoped.
- Removed simulated latency offsets and fixed accuracy/drift claims from telemetry.
  Displayed timings describe count queries and HTTP health, not model inference.
- Readiness fails closed when migration inspection fails. --production evaluates
  deployment settings even with DEBUG enabled; output explicitly limits its scope
  to configuration and never certifies live delivery.

## Revised priority

1. Finish security and evidence review of the new surfaces, including unified
   dashboard aggregation, CSV formula handling, public Copilot input limits and
   SLA promises. Run the relevant negative permission and ownership tests.
2. Replace report/evaluation claims with measured values: resolved-ticket ratio
   is not SLA compliance; a display hash does not authenticate editable report
   content; academic GIS expected distances need an independent reference.
3. Run reproducible CI with security scans/coverage and record all failures;
   the old 607-test count is historical and must be rediscovered.
4. Provision staging with a production server and supervised forecast worker.
   Current Compose uses runserver, DEBUG and development defaults.
5. Rotate exposed credentials; validate HTTPS OAuth, mailbox arrival, monitored
   errors and backup/restore in the actual target environment.
6. Extend reorder/workload contracts only after domain transactions and
   compensating operations are specified and tested. These remain incomplete.

The previous production checklist remains necessary. New security regressions
and misleading measurement claims take priority over additional feature expansion.
No production deployment, external credential rotation, inbox confirmation or
restore drill is claimed by this checkpoint.

## Verification

- `python manage.py test tests.test_authorization_convergence tests.test_production_readiness --keepdb --noinput`: 7 passed (before the two additional readiness tests).
- `python manage.py test tests.test_executive_reporting_and_telemetry tests.test_public_copilot_and_cart_api tests.test_production_readiness --keepdb --noinput`: 18 passed, 102.828 seconds. Initial new fixtures omitted required order_timestamp; fixtures were corrected, assertions retained.
- `python manage.py check`: zero issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `python manage.py platform_readiness --production --strict --json`: exit 1,
  BLOCKED for debug_enabled, https_oauth_redirect, secure_transport_cookies;
  database reachable, zero pending migrations. Credential presence is not
  evidence of rotation or actual delivery.
