import json
from django.test import SimpleTestCase
from scripts.check_release_secrets import scan_text, decode_source


class ReleaseSecretScanTests(SimpleTestCase):
    def test_utf16_reports_are_scanned_not_skipped(self):
        token = 'GOCSPX' + '-' + 'x' * 30
        text = decode_source(token.encode('utf-16'))
        self.assertEqual(len(scan_text('report.txt', text)), 1)

    def test_token_values_are_never_in_output(self):
        for prefix in ['GOCSPX' + '-', 'gh' + 'p_', 'xkey' + 'sib-']:
            token = prefix + 'a' * 45
            results = scan_text('candidate.py', 'key=' + token)
            self.assertEqual(len(results), 1)
            self.assertNotIn(token, json.dumps(results))

    def test_private_key_and_url_report_only_location(self):
        text = '-----BEGIN ' + 'PRIVATE KEY-----\npostgresql://user:' + 'a' * 20 + '@host/db'
        self.assertEqual([r['line'] for r in scan_text('candidate.txt', text)], [1, 2])

    def test_placeholder_is_not_a_secret(self):
        self.assertEqual(scan_text('.env.example', 'GOOGLE_CLIENT_SECRET=\nBREVO_API_KEY=your-key'), [])
