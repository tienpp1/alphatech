# Google identity / internal portal boundary

Owner-confirmed policy: Google-linked identities are public-only, even if legacy
data still has superuser flags, memberships, a password or an API token. Separate
non-Google ADMIN/superuser, MANAGER and EMPLOYEE accounts retain password login.
Ordinary public customers have no internal role. No schema or account data changes.

The common access policy is enforced by internal login, HTTP middleware, DRF token
authentication, workspace context, telemetry authorization and public navigation.
Google callbacks clear the active workspace and only redirect to public views.
Old password sessions cannot bypass the identity restriction. Existing grants are
re-read rather than cached across membership revocation. Standard role fixtures
retain their original permission grants; denied VIEWER/custom roles are tested.

Validation (2026-10-04):
- Initial focused run: 54 tests, one failure in a new test using the wrong login
  form key. Corrected username to username_or_email; application behavior unchanged.
- Exact staged release tree a193df38ebf3b88bf3b0773b64503247f8aa97ca: 72 tests,
  11.988 seconds, OK. Evidence output/auth_release_2zfutn7f/tests.log.
- Full dirty-worktree snapshot: 1197 tests, 276.170 seconds, OK; 711 source
  fingerprints unchanged. Evidence output/acceptance_verification/20261004T032256Z.
- Fast password hashing was confined to disposable test processes, never production.
- Django check: no issues. Migration drift: none. git diff --check: pass.

Release intentionally excludes unrelated policy-copy/UI edits and the 97-item
ledger. Neither local tests nor this record constitutes proof of deployment or
live Google UAT; those results must be recorded after verification.

## Deployment and live observations

- Pushed eef91502469ba80608a58f8cbf8697d642c7c9b7 to origin/main.
- Render deploy dep-db0sgrvavr4c7395c590 is live at that exact SHA.
- Reused the authorized Google test account through the real account chooser.
  Its session existed before deployment. Reload after deployment removes the
  internal banner and internal links; customer profile and cancelled test orders
  remain visible. Screenshot output/uat_20261004/google-banner-removed.png.
- Direct browser navigation to /noibo/ was ERR_BLOCKED_BY_CLIENT with no captured
  response; do NOT cite this as a live HTTP 403. Denial 403 is proven by automated
  regressions, not that blocked browser navigation.
- Real HTTPS password logins for admin, manager, employee all return 200/success;
  all three can GET /noibo/ with 200. Verification sessions/tokens logged out.
  Redacted evidence output/internal_live_auth_20261004.json.
- No migrations, customer data or password changes in this fix. No 97-item
  progress changes. Other pre-existing dirty edits remain uncommitted.

## Independent HTTPS denial observation (04/10 follow-up)

The browser still blocks JSON navigation; a separate read-only HTTPS diagnostic
reused an already-issued session belonging to the authorized Google-linked test
identity. Public /tai-khoan/ returned 200 with the expected authenticated account.
/noibo/, /noibo/retail/orders/162/ and /api/v1/auth/me/ each returned 403.
No synthetic session was created. No cookie, token, session data or credential
was retained in output/google_http_live_20261004.json. The production DB connection
was read-only. This supplies the HTTP evidence missing from the browser attempt.
