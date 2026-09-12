# Customer journey review — 2026-09-10

## Follow-up: dedicated restore database

Operator clarified staging is seeded/test data; restore database was created
using TEMPLATE rather than a production dump. Inspected the named restore
database using the staging connection host/credentials and the explicit database
name ai_business_platform_db_restore. No credential was printed.

- Both connections: PostgreSQL 18.6, PostGIS 3.6.2.
- Column definitions, 51 migration records and audit triggers match.
- Restore: 6 users, 2 workspaces, 85 customers, 160 orders, 427 items, 22 audit rows.
- Current staging: 7 users, 3 workspaces, 85 customers, 160 orders, 22 audit rows.
  Counts are not identical; no claim of complete snapshot equality is made.
- Restore has zero service/customer and order/customer workspace mismatches,
  zero duplicate normalized nonempty email groups, zero pending migrations.
- Django ORM order/customer and service/customer reads succeed. PostGIS point
  SRID result is 4326.
- No-op audit UPDATE on restore is rejected with SQLSTATE P0001. The test
  transaction always rolled back; no production or staging writes performed.

Result: existing TEMPLATE clone passes these post-clone checks. A file-based
backup/restore drill with artifact ID, timestamps and recovery timing is still
needed to establish recoverability independent of the source database. Production
backup recovery, offsite retention, RPO/RTO and exact data equality remain unproven.

## Scope and execution contract

Reconcile repository and live deployment first; preserve other agents' changes.
Review registration/verification, account ownership, transactional delivery,
checkout, CI and mobile usability. Fix evidence-backed defects, verify focused
regressions, and distinguish local implementation from live acceptance.
Do not create production orders/accounts or restore over the active database.

Working tree was clean at dbad3f26 at the start. Current changes are local only.

## Implemented

1. Pickup stock: validate the entire cart before deductions. Previously an early
   line was saved before a later stock rejection returned normally from atomic(),
   committing an incomplete stock deduction without an order.
2. Registration and checkout use Django email validation; unsupported delivery
   methods cannot bypass the home-delivery/pickup validation branches.
3. Outbox locks/reloads one row before sending. Separate database connections and
   stale instances cannot resend a record already marked SENT. Lock duration
   includes transport timeout. Unknown provider outcomes still require review.
4. Product.primary_image consumes prefetched images rather than creating extra
   queries per product. Selection retains primary-first and fallback ordering.
5. ui-ux-pro-max guided mobile/form accessibility review. Header wraps at small
   widths; auth fields expose appropriate autocomplete; search has an accessible
   name. No redesign of product branding or routes.
6. CI additionally runs existing verification/OAuth/outbox/public-auth tests.

## Verification

Commands use PYTHONPATH=D:\ai_business_platform\.venv-quality\Lib\site-packages.

Baseline command:
```
python manage.py test tests.test_customer_account_identity tests.test_customer_email_outbox_and_oauth_security tests.test_google_oauth_and_email_notifications tests.test_public_ecommerce_cart_and_checkout tests.test_public_auth_and_customer_experience tests.test_deployment_boundaries tests.test_brevo_email_backend --keepdb --noinput
```
78 tests passed, 347.486s. This process started before edits.

Final affected backend command:
```
python manage.py test tests.test_brevo_email_backend tests.test_customer_email_outbox_and_oauth_security tests.test_public_ecommerce_cart_and_checkout --keepdb --noinput
```
46 tests passed, 254.760s. Includes stale/concurrent outbox, invalid email/method,
multi-line stock rejection and zero-query prefetched-image regressions.
No full-suite claim. Existing tests/assertions were retained.

`python manage.py check`: zero issues.
`python manage.py makemigrations --check --dry-run`: no changes.

Browser: live registration has no horizontal overflow at viewport 375x812.
Live catalog had content width 610 vs client width 360; patched local catalog
has 360/360, visible login/cart/menu controls and functioning mobile menu.
Patched local landscape viewport 812x375 also has matching content/client width
797/797. Local login DOM confirms username/current-password autocomplete.
Live add-to-cart and cart page verified in a temporary guest browser session.
This is not checkout/order completion or complete accessibility certification.

## Live evidence and limits

- Render service srv-dafrcr5g1s2s73frbl1g: live dbad3f26d0c2e0c01ac3e1b143c4098cc5845eb3,
  finished 2026-09-10T06:28:36.943689Z.
- Canonical public and Google callback URLs use alphatech-26uv.onrender.com HTTPS.
- Brevo selected; key present; DEBUG false; secure session/CSRF cookies and SSL
  redirect true. Sentry DSN/database URL present; no secrets retained in evidence.
- Homepage/login/register/catalog HTTP 200 (single warm samples 0.31–0.74s).
  Unauthenticated /noibo/ redirects to /accounts/login/. DENY and nosniff headers
  observed. These are not load benchmarks or exhaustive authorization checks.
- User reports Google login works. Previous local HTTPS diagnostic emails reached
  both user-designated inboxes. Production registration/order/contact email
  receipt has not been checked in this pass.
- https://github.com/tienpp1/alphatech/actions/runs/34428931579 is FAILED solely
  at Static security scan; migration/dependency audit/test/coverage steps passed.
- Local Bandit: 69 findings, 5 medium/64 low/0 high. Medium: B104 forbidden-host
  string in integration parser; B310 in Google OAuth and knowledge transports.
  Other findings include demo passwords, noncryptographic randomness and swallowed
  exceptions. Findings need individual review; no blanket exclusion added.

## Remaining work in priority order

1. Review/fix or individually justify security findings, then rerun real CI on
   the new commit before deploying. Current Render auto-deploy previously allowed
   a commit with failing CI to go live; enforce CI-dependent rollout operationally.
2. Complete authenticated production registration/verification/order/contact with
   controlled test accounts and inbox confirmation; existing demo student accounts
   may have historical elevated privileges and are not safe public-RBAC fixtures.
3. Add a database-level case-insensitive User.email uniqueness gate after a
   read-only collision audit. Current public registration normalization/tests
   pass; the model's unique email constraint is case-sensitive for other writers.
4. After the operator updated the External URL, read-only staging connection
   succeeds: ai_business_platform_db_staging, PostgreSQL 18.6, PostGIS installed.
   Database name differs from production. It contains 59 public tables, 51
   migrations, 7 users, 160 orders and 85 customers. Do not overwrite this populated
   target without explicit authorization. Its data provenance and an actual
   restore drill remain unverified. PostgreSQL 18 pg_dump/pg_restore tools are
   available locally. Use a separate empty restore target or establish existing
   restoration evidence, then record backup ID, duration and post-restore checks.
5. Confirm Sentry event arrival using project access/operator receipt, then review
   CSP reports before enforcement. DSN presence alone is insufficient.
6. Broaden mobile checks to authenticated checkout, landscape and reduced motion;
   measure page/image transfer and query timings under realistic load.

No new migration, production data mutation, paid infrastructure, secret rotation,
AI/forecast-model changes or commit/push/deploy was performed in this pass.
