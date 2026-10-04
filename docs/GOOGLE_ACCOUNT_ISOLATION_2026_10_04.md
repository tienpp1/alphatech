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
