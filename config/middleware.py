"""Small operational middleware shared by all public and internal routes."""

import uuid

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class RequestCorrelationIdMiddleware:
    """Attach a bounded correlation id to every request and response."""

    header_name = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = (request.META.get("HTTP_X_REQUEST_ID") or "").strip()
        # Accept only a small printable token; never reflect arbitrary input.
        if supplied and len(supplied) <= 128 and all(ch.isalnum() or ch in "-_." for ch in supplied):
            correlation_id = supplied
        else:
            correlation_id = uuid.uuid4().hex
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response[self.header_name] = correlation_id
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Emit a conservative CSP in report-only mode before enforcement.

    The public and internal UIs still contain a small number of legacy inline
    scripts and third-party map/chart assets. Report-only mode makes policy
    violations observable without silently breaking those workflows; an
    operator can opt into enforcement after reviewing the reports.
    """

    CSP = (
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
        "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com; "
        "frame-src https://accounts.google.com; form-action 'self' https://accounts.google.com"
    )

    def process_response(self, request, response):
        if getattr(settings, "CSP_ENFORCE", False):
            response["Content-Security-Policy"] = self.CSP
        elif getattr(settings, "CSP_REPORT_ONLY", True):
            response["Content-Security-Policy-Report-Only"] = self.CSP
        return response
