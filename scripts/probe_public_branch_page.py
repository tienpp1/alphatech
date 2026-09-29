"""Bounded public HTTP probe; never authenticates or serializes cookies/tokens.

Optional one explicit public-place search goes through the app's CSRF/rate gate.
No device location, personal address or business record is submitted.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests


def main(base, output, search=False):
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or parsed.netloc != 'alphatech-26uv.onrender.com' or parsed.path not in ('', '/'):
        raise ValueError('Only the user-approved public HTTPS deployment is in scope')
    base = base.rstrip('/')
    report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'url': base + '/chi-nhanh/',
              'browser_verified': False, 'deployment_sha_verified': False}
    with requests.Session() as session:
        try:
            page = session.get(report['url'], timeout=(5, 20), allow_redirects=False)
            report['status'] = page.status_code
            report['headers'] = {name: page.headers.get(name) for name in (
                'Content-Security-Policy', 'Content-Security-Policy-Report-Only',
                'Strict-Transport-Security', 'X-Content-Type-Options', 'X-Frame-Options')}
            report['cookies'] = [{'name': c.name, 'secure': c.secure,
                                  'httponly': c.has_nonstandard_attr('HttpOnly'),
                                  'samesite': c.get_nonstandard_attr('SameSite')} for c in session.cookies]
            report['contains_branch_page'] = 'tim-dia-diem' in page.text and 'leaflet' in page.text.lower()
            csrf = session.cookies.get('csrftoken')
            if search and page.status_code == 200 and report['contains_branch_page'] and csrf:
                response = session.post(base + '/chi-nhanh/tim-dia-diem/',
                                        data={'q': 'Bưu điện Trung tâm Sài Gòn', 'csrfmiddlewaretoken': csrf},
                                        headers={'Referer': report['url']}, timeout=(5, 20), allow_redirects=False)
                report['search_status'] = response.status_code
                try:
                    payload = response.json()
                    report['result_count'] = len(payload.get('results', []))
                    report['attribution_present'] = 'OpenStreetMap' in payload.get('attribution', '')
                except (ValueError, AttributeError, TypeError):
                    report['search_error'] = 'invalid_json_shape'
            else:
                report['search_not_run'] = 'not requested or expected page/CSRF absent'
        except requests.RequestException as exc:
            report['transport_error'] = type(exc).__name__
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='https://alphatech-26uv.onrender.com')
    parser.add_argument('--search-public-place', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.output, args.search_public_place)
