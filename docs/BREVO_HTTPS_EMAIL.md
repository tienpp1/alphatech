# AlphaTech HTTPS email on Render Free

Local validation: 25 tests passed in 78.569 seconds using
`python manage.py test tests.test_brevo_email_backend tests.test_production_readiness tests.test_google_oauth_and_email_notifications --keepdb --noinput`.
PYTHONPATH points to `.venv-quality/Lib/site-packages` for installed requests.
Django check and migration drift pass. Tests simulate HTTP responses, not inbox
delivery. Initial test import failed because global Python lacked requests;
the isolated quality packages resolved it without changing the global runtime.

Backend: apps.public_web.email_backends.BrevoEmailBackend.
Transport: POST https://api.brevo.com/v3/smtp/email (HTTPS port 443).
The existing Django mail calls, rendered content, recipient resolution and
CustomerEmailDelivery outbox remain in use. No database migration is required.

## Operator setup

1. Create a Brevo account and complete any required transactional-email account
   activation. Do not select a paid plan automatically.
2. In Settings, open Senders / Senders, domains & dedicated IPs. Add the intended
   From address and finish email verification. A Gmail sender cannot authenticate
   gmail.com; provider rewriting/restrictions and deliverability must be checked.
   The Render subdomain does not provide ownership of an email-sending domain.
3. Settings > SMTP & API > API Keys & MCP > Generate a new API key.
   Use an ordinary API key, not an SMTP key or MCP key.
4. Save BREVO_API_KEY in the local ignored .env for authorized deployment work.
   Never send the key in chat or commit it.
5. After sender/account verification, set on Render:

```
EMAIL_BACKEND=apps.public_web.email_backends.BrevoEmailBackend
BREVO_API_KEY=<secret>
DEFAULT_FROM_EMAIL=<verified sender address>
PUBLIC_BASE_URL=https://alphatech-26uv.onrender.com
GOOGLE_REDIRECT_URI=https://alphatech-26uv.onrender.com/accounts/google/callback/
```

Do not change the active backend before deploying the corresponding code and
verifying the credential. No Render plan/environment change has been made yet.

## Delivery and evidence

Only HTTP 201 plus a nonempty messageId counts as provider acceptance. Existing
SENT status means provider/backend accepted, not confirmed Inbox arrival. The
backend exposes provider_message_id on the message object; existing outbox rows
do not yet persist that field. Use provider transactional logs for live evidence.
Each outbox record sends to exactly one address. Multi-recipient/CC/BCC and
attachments are rejected, never silently dropped. Existing transactional emails
and password reset use single-recipient plain/HTML messages.

No redirect or implicit HTTP retry is allowed. Error codes distinguish missing
configuration, authentication, permission, quota, invalid response and network
failure without retaining provider response bodies. A timeout records unknown
delivery outcome: inspect Brevo logs before manual retry to avoid duplicates.
Existing outbox retry does not provide provider-side exactly-once delivery.

Acceptance: verify registration and login, then checkout/contact for account
minhtien147896325@gmail.com plus form inbox 1250080194@sv.hcmunre.edu.vn.
Check Inbox and Spam in both, record provider IDs/timestamps, and verify a failed
send preserves the business event and can retry. No inbox receipt is claimed by
mocked backend tests.

References:
- https://developers.brevo.com/reference/send-transac-email
- https://help.brevo.com/hc/en-us/articles/209467485-Create-and-manage-your-API-keys
- https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email
