from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request, ProxyHandler
from django.test import SimpleTestCase, override_settings
from config.provider_http import open_provider_request, RejectProviderRedirects
from apps.public_web.views import _google_urlopen


class ProviderHTTPBoundaryTests(SimpleTestCase):
    @patch('config.provider_http.build_opener')
    def test_invalid_endpoints_never_open_socket(self, opener):
        urls = ['file:///etc/passwd', 'http://oauth2.googleapis.com/token',
                'https://oauth2.googleapis.com.evil.test/token',
                'https://evil.test/?next=oauth2.googleapis.com',
                'https://user:secret@oauth2.googleapis.com/token',
                'https://oauth2.googleapis.com:444/token',
                'https://oauth2.googleapis.com/token#fragment']
        for url in urls:
            with self.subTest(url=url), self.assertRaises(URLError):
                open_provider_request(url, allowed_hosts={'oauth2.googleapis.com'}, timeout=5)
        opener.assert_not_called()

    def test_redirects_rejected_without_echoing_url_or_credentials(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status), self.assertRaisesRegex(URLError, '^<urlopen error Provider redirect rejected>$'):
                RejectProviderRedirects().redirect_request(None, None, status, '', {}, 'https://evil.test/?key=private')

    @override_settings(GOOGLE_OAUTH_USE_ENV_PROXY=False)
    @patch('config.provider_http.build_opener')
    def test_google_proxy_default_and_request_preserved(self, opener):
        req = Request('https://oauth2.googleapis.com/token', data=b'fixture')
        _google_urlopen(req, 12)
        handlers = opener.call_args.args
        self.assertTrue(any(isinstance(h, RejectProviderRedirects) for h in handlers))
        self.assertTrue(any(isinstance(h, ProxyHandler) and h.proxies == {} for h in handlers))
        opener.return_value.open.assert_called_once_with(req, timeout=12)

    @override_settings(GOOGLE_OAUTH_USE_ENV_PROXY=True)
    @patch('config.provider_http.build_opener')
    def test_google_userinfo_and_environment_proxy_opt_in(self, opener):
        _google_urlopen(Request('https://www.googleapis.com/oauth2/v3/userinfo'), 5)
        self.assertFalse(any(isinstance(h, ProxyHandler) for h in opener.call_args.args))
