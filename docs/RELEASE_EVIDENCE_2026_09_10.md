# Release evidence — 2026-09-10

## Authenticated Render API inspection

Local operator-supplied API key authenticated successfully. Read-only requests
were restricted to service srv-dafrcr5g1s2s73frbl1g and its environment/deploys.
Service alphatech is a native Python free instance in Singapore; domain is
https://alphatech-26uv.onrender.com, branch main, auto-deploy enabled.
Live deploy dep-dah0jiu1egvs73c210lg uses caa6a1a454c33c618aed7483940431d45b415a68
(created 2026-09-10T01:37:15.839814Z), before the local release-safety patch.
Actual dashboard build command installs requirements, collects static files and
runs migrate; it does not use build.sh. Start command is Gunicorn WSGI.

Remote DEBUG is false, but PUBLIC_BASE_URL and GOOGLE_REDIRECT_URI still use
HTTP localhost. SMTP is Gmail on port 587 with credentials present. Secure-cookie
and SSL-redirect settings are absent from the returned service environment.
Google credentials, SECRET_KEY, DATABASE_URL and SENTRY_DSN are present; their
values were not printed or persisted. Presence is not functional verification.

Render's free-service documentation explicitly blocks outbound SMTP ports
25/465/587: https://render.com/docs/free. Current SMTP cannot satisfy the live
email gate on this compute plan. Operator must choose a paid compute instance
or authorize an HTTPS email-provider integration (which requires provider setup).
No paid plan change, environment mutation, deployment, live email, database
mutation or application-account modification was made during this inspection.

Canonical production URL confirmed by operator: https://alphatech-26uv.onrender.com.
Account inbox: minhtien147896325@gmail.com. Distinct form inbox:
1250080194@sv.hcmunre.edu.vn. Earlier alphatech.onrender.com URLs are not the
confirmed production target. A separate staging deployment is not yet verified.

Operator confirms Google/SMTP credential rotation, Sentry configuration and
database/backup readiness. These confirmations are not inbox receipt, telemetry
ingestion or restore-drill evidence.

GitHub API independently confirms run 34353691709 completed successfully:
https://github.com/tienpp1/alphatech/actions/runs/34353691709
Commit: caa6a1a454c33c618aed7483940431d45b415a68.
Run timestamps: 2026-09-09T12:53:35Z to 2026-09-09T12:57:54Z.
Installed dependency audit, focused tests, coverage and artifact steps succeeded.
This workflow runs selected tests, not the full suite. Its Bandit command used
--exit-zero, so the successful run does not prove zero static security findings.

## Local corrections awaiting release

- Remove automatic migration, demo seeding and administrator password reset
  from WSGI startup. Build only installs dependencies and collects static files;
  migration must run explicitly once at release, before starting the new app.
- Remove public global business counts/workspace names from health metrics.
- Restore the blocking Bandit exit status.
- Limit Render host/CSRF trust to configured hosts, not every onrender.com site.
- Default Sentry PII collection off. Set canonical URL and secure cookies in
  the Render blueprint. Existing dashboard settings must be reconciled explicitly.

The existing seed_student_admin command resets passwords and promotes accounts.
It must not be run on production. Removing its automatic invocation does not
revoke accounts, sessions or API tokens already created. Review those accounts
and rotate their passwords/revoke tokens through an authenticated operator
workflow before reopening production acceptance. No existing records were edited.

## Pending evidence

Authenticated Render access to inspect deployed commit, environment, plan and
release mechanism; Google Console callback confirmation; real login and per-inbox
mail receipt; Sentry test-event ID; separate restore target with backup ID,
timestamp and read-only smoke results; a new CI run on the corrected commit.
No live Render migration, account change, email or deployment occurred in this pass.

Local validation: `python manage.py test tests.test_deployment_boundaries
tests.test_health tests.test_production_readiness --keepdb --noinput`: 12 passed
in 6.296 seconds. Initial SimpleTestCase cursor mock conflicted with Django's
database guard at teardown; using transactional TestCase resolved that test
harness issue with all assertions retained. `python manage.py check` passed;
`python manage.py makemigrations --check --dry-run`: no changes detected.
`git diff --check`: clean. Browser automation could not initialize because its
kernel assets path was unavailable, so authenticated Render inspection is pending.
