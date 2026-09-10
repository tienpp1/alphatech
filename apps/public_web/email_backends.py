"""HTTPS transactional transport; outbox owns retry and recipient isolation."""
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class EmailTransportError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class BrevoEmailBackend(BaseEmailBackend):
    """One recipient per message prevents leaks and ambiguous partial retries."""

    def send_messages(self, email_messages):
        accepted = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                self._send(message)
            except EmailTransportError:
                if not self.fail_silently:
                    raise
            else:
                accepted += 1
        return accepted

    def _send(self, message):
        import requests
        key = getattr(settings, "BREVO_API_KEY", "")
        if not key:
            raise EmailTransportError("BREVO_CONFIG_MISSING")
        if len(message.to) != 1 or message.cc or message.bcc or message.attachments:
            raise EmailTransportError("BREVO_UNSUPPORTED_MESSAGE")
        name, sender = parseaddr(message.from_email)
        _, recipient = parseaddr(message.to[0])
        try:
            validate_email(sender)
            validate_email(recipient)
        except ValidationError:
            raise EmailTransportError("BREVO_INVALID_ADDRESS") from None
        payload = {"sender": {"email": sender}, "to": [{"email": recipient}],
                   "subject": message.subject, "textContent": message.body}
        if name:
            payload["sender"]["name"] = name
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = content
        if message.content_subtype == "html":
            payload["htmlContent"] = message.body
            payload.pop("textContent", None)
        if message.reply_to:
            _, reply = parseaddr(message.reply_to[0])
            payload["replyTo"] = {"email": reply}
        # Never follow redirects with the API credential or retry POST implicitly.
        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": key, "Accept": "application/json"},
                json=payload, timeout=(5, 15), allow_redirects=False,
            )
        except requests.Timeout:
            raise EmailTransportError("BREVO_TIMEOUT_UNKNOWN_DELIVERY") from None
        except requests.RequestException:
            raise EmailTransportError("BREVO_NETWORK_ERROR") from None
        try:
            if response.status_code != 201:
                code = {401: "AUTH", 403: "FORBIDDEN", 429: "RATE_LIMIT"}.get(
                    response.status_code, "REJECTED")
                raise EmailTransportError("BREVO_" + code)
            try:
                result = response.json()
            except ValueError:
                raise EmailTransportError("BREVO_INVALID_RESPONSE") from None
            if not isinstance(result, dict) or not isinstance(result.get("messageId"), str) or not result["messageId"].strip():
                raise EmailTransportError("BREVO_INVALID_RESPONSE")
            # Provider acceptance is not proof of inbox delivery.
            message.provider_message_id = result["messageId"]
        finally:
            response.close()
