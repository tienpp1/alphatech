# Validation quickstart

## Local

```powershell
python manage.py migrate --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test tests.test_customer_account_identity tests.test_approval_state_integrity tests.test_forecasting_queue tests.test_forecasting_dataset --keepdb --noinput
python manage.py test tests.test_public_ecommerce_cart_and_checkout tests.test_public_auth_and_customer_experience tests.test_phase10_demonstration_scenarios --keepdb --noinput
```

Queue smoke test:

```powershell
python manage.py forecast_worker --once
python manage.py forecast_monitor --limit 20
```

## Production acceptance

Run only with deployment/operator access: rotate exposed credentials, configure HTTPS redirect URI, run redacted diagnostics, test OAuth with a real account, send diagnostic SMTP, verify Inbox/Spam arrival, test invalid SMTP warning/retry, and perform a backup/restore drill. Record timestamps and message IDs without private content. Unavailable evidence remains BLOCKED.
