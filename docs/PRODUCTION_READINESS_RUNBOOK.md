# Production readiness runbook

This runbook is intentionally operator-driven. The repository can validate
configuration and build artifacts, but it cannot prove Google Console changes,
Inbox delivery, staging deployment or database restoration without access to
those systems.

## 1. Redacted application diagnostic

```powershell
python manage.py platform_readiness --json
python manage.py platform_readiness --production --strict --json
```

The command never prints `EMAIL_HOST_PASSWORD`, OAuth client secrets, database
passwords or token values. `READY` proves configuration checks only, never live
production acceptance. Archive the output and separately verify every external
gate below. DEBUG=True must not be mistaken for production readiness.

### 2026-09-08 measured blockers

Local native runtime audit found 62 advisories in 5 installed packages:
Django 6.0.2 (27), Pillow 12.1.1 (26), sqlparse 0.5.5 (5), pip 26.1.1 (3),
Click 8.3.1 (1). This is an installed-environment scan, not a locked dependency
or deployment audit. Do not upgrade the machine-wide interpreter blindly.
Create a project-specific runtime, update compatible dependencies, audit the
resolved environment again, and run domain/security regressions before cutover.

Bandit scanned 28,454 lines with 67 findings (0 high, 5 medium, 62 low).
The B104 at the integration parser is a forbidden-host entry, not a bind address.
Four B310 findings concern Google/OpenAI HTTP calls and still need focused
transport/redirect review. No findings were suppressed to manufacture a pass.
Raw local scan files remain in ignored `.quality/`; do not publish them without
review because static scanner output can contain source snippets.

Docker/gh commands were not found on this host during this pass. The development
Compose file remains development-only, not a production deployment artifact.

## 2. Staging release gate

1. Provision PostgreSQL/PostGIS from the same image family used by CI.
2. Load secrets through the deployment secret manager, never `.env` committed
   to source control.
3. Run `python manage.py migrate --plan`, review it, then `migrate --noinput`.
4. Confirm `audit.0002_auditlog_append_only_trigger` is applied.
5. Run focused security, identity, checkout, forecasting and approval tests.
6. Verify `/health/` and `/noibo/status/` from the staging ingress.
7. Review `Content-Security-Policy-Report-Only` violations. Keep report-only
   during rollout, then set `CSP_ENFORCE=True` only after the report is clean
   and the Google/Map/chart origins required by the deployment are confirmed.
8. Configure `SENTRY_DSN` or `OTEL_EXPORTER_OTLP_ENDPOINT` and verify a test
   event/span arrives in the selected backend.

## 3. Backup and restore evidence

Use the platform provider's encrypted PostgreSQL backup tooling. Record:

- backup identifier and UTC timestamp;
- source database version and PostGIS version;
- restore target identifier;
- migration/check result after restore;
- a read-only smoke test against a non-sensitive workspace;
- operator and incident/change reference.

Never paste dump files, credentials or customer data into issue trackers.

## 4. OAuth and email acceptance

Rotate every credential previously exposed in chat before testing. Verify the
HTTPS redirect URI in Google Console, then test a real account. Send a real
diagnostic email and confirm arrival in Inbox and Spam using timestamps/message
IDs. SMTP acceptance alone is not Inbox proof.

## 5. Rollback

Keep the previous application artifact available until health, OAuth, email and
restore checks pass. If a migration or release fails, stop traffic, restore the
previous artifact, and follow the database provider's tested point-in-time
restore procedure. Do not run destructive `flush`, reset or ad-hoc data edits.
