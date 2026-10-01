"""Existing external executable assets must work before CSP enforcement."""
import re
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from config.middleware import SecurityHeadersMiddleware


class CSPAssetCompatibilityTests(SimpleTestCase):
    def test_every_template_script_origin_is_explicitly_allowed(self):
        policy = SecurityHeadersMiddleware.CSP
        directive = next(part for part in policy.split(';') if part.strip().startswith('script-src '))
        origins = set(directive.split()[1:])
        self.assertNotIn('https:', origins)
        self.assertNotIn('*', origins)
        checked = 0
        for path in (Path(settings.BASE_DIR) / 'templates').rglob('*.html'):
            for url in re.findall(r'<script\b[^>]*\bsrc=["\'](https://[^"\']+)', path.read_text(encoding='utf-8'), re.I):
                parsed = urlsplit(url)
                self.assertIn(f'{parsed.scheme}://{parsed.netloc}', origins, str(path))
                checked += 1
        self.assertGreater(checked, 0)

    @override_settings(CSP_ENFORCE=True, CSP_REPORT_ONLY=True)
    def test_enforcement_emits_real_policy_not_report_only(self):
        response = SecurityHeadersMiddleware(lambda request: HttpResponse()).process_response(
            RequestFactory().get('/'), HttpResponse())
        self.assertIn('Content-Security-Policy', response)
        self.assertNotIn('Content-Security-Policy-Report-Only', response)
        self.assertIn("object-src 'none'", response['Content-Security-Policy'])
        self.assertIn("frame-ancestors 'none'", response['Content-Security-Policy'])
