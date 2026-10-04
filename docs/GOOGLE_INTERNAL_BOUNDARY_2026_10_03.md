# Google session / internal portal boundary — 2026-10-03

## Contract confirmed by owner

Google-authenticated sessions are customer-only, even for an existing privileged
identity. ADMIN/superuser, MANAGER and EMPLOYEE may reauthenticate by password at
`/accounts/login/`. VIEWER and staff flags alone do not grant entry. Existing
workspace permissions continue to constrain business operations. Identity linking
does not delete or add memberships. No new migration or business data updates.

## Implementation

- `apps/accounts/internal_access.py`: shared entry policy, authenticated internal
  HTTP boundary, public-only Google/legacy sessions, public redirect destinations.
- `apps/accounts/authentication.py`: existing password-issued tokens recheck role
  eligibility; Google sessions cannot retrieve tokens via the profile endpoint.
- OAuth callback records server-side `platform_auth_method=google`; password
  entry records `password`. Unknown old Google-linked sessions fail closed for
  internal access until password reauthentication. Ordinary customer dashboard
  redirects remain compatible.
- Public account/home/navigation use the policy, not Django staff flags alone.
  UI/UX skill applied to consistent authorization visibility and password-manager
  autocomplete, without redesigning existing layout or animation.
- Telemetry checks current DB identity/permissions and reloads persisted session
  state to reject a socket after its session is switched to Google or logged out.

## Verification

First run: 59 tests, 378.943s, 1 failure + 5 errors. The Channels database adapter
closed a TestCase atomic connection; its real synchronous policy is now tested
without that adapter inside the atomic transaction. The cascading fixture errors
are resolved. The VIEWER navigation test now asserts denial explicitly, while
retaining all badge/logout assertions for the permitted roles.

Second group: 43 tests, 253.380s, 2 failures. Preserved the existing normal-customer
`/noibo/` redirect; updated a stale product test expecting unconditional stock
availability to the confirmation wording introduced by the previous policy patch.
Command Center fixture now uses EMPLOYEE with explicit permissions instead of a
custom CC_VIEWER role. Permission-denial/revocation assertions remain intact.

Focused retests with default password hasher: 16/16 in 121.892s; 2/2 in 14.327s.
Final combined run: **110/110 in 38.051s, exit 0**. Google HTTP transport mocked;
email uses test outbox, not live delivery. Disposable local test DB only.

Reproduction in PowerShell (test-only fast hasher; no production config changes):

```powershell
.venv-acceptance/Scripts/python.exe -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings_evidence_test'; import django; from django.conf import settings; settings.PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']; django.setup(); from django.core.management import call_command; call_command('test', 'tests.test_google_internal_boundary', 'tests.test_auth', 'tests.test_web_auth_routing', 'tests.test_google_oauth_and_email_notifications', 'tests.test_public_policy_copy', 'tests.test_command_center_security', 'tests.test_public_auth_and_customer_experience', 'tests.test_public_website_and_portal_separation', 'tests.test_rbac', interactive=False, verbosity=1)" test
.venv-acceptance/Scripts/python.exe manage.py check
.venv-acceptance/Scripts/python.exe manage.py makemigrations --check --dry-run
```

Checks: 0 Django issues; no migration drift. No tests deleted or skipped.
No changes to the 97-item ledger. No push/deploy or live Google UAT performed
for this patch. Deploy/restart is required before the new policy is active online.
