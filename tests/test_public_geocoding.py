import json
from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase, RequestFactory, Client, override_settings
from apps.public_web import geocoding


@override_settings(OSM_GEOCODER_SEARCH_URL="https://nominatim.openstreetmap.org/search", PUBLIC_BASE_URL="https://alphatech-26uv.onrender.com")
class PublicGeocodingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_normalization_rejects_bad_coordinates(self):
        rows = [{"lat":"10.7", "lon":"106.7", "display_name":"Chợ Bến Thành"},
                {"lat":"nan", "lon":0, "display_name":"bad"}, {"lat":100,"lon":1,"display_name":"bad"}, None]
        self.assertEqual(geocoding.normalize_results(rows), [{"lat":10.7,"lng":106.7,"label":"Chợ Bến Thành"}])

    def test_post_and_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/chi-nhanh/tim-dia-diem/').status_code,405)
        self.assertEqual(client.post('/chi-nhanh/tim-dia-diem/', {'q':'Ben Thanh'}).status_code,403)

    def request(self, query):
        request = RequestFactory().post('/chi-nhanh/tim-dia-diem/', {'q':query})
        request._dont_enforce_csrf_checks = True
        return geocoding.public_geocode_view(request)

    def test_short_query_does_not_call_provider(self):
        with patch.object(geocoding, 'lookup') as lookup:
            self.assertEqual(self.request('a').status_code,400)
            lookup.assert_not_called()

    def test_busy_and_failure_are_truthful(self):
        with patch.object(geocoding, 'lookup', side_effect=BlockingIOError):
            response = self.request('Ben Thanh')
            self.assertEqual(response.status_code,429)
            self.assertEqual(response['Retry-After'],'2')
        with patch.object(geocoding, 'lookup', side_effect=ValueError):
            self.assertEqual(self.request('Ben Thanh').status_code,503)

    def test_success_returns_only_sanitized_public_coordinates(self):
        with patch.object(geocoding, 'lookup', return_value=[{"lat": 10.7, "lng": 106.7, "label": "Chợ Bến Thành"}]):
            response = self.request('Ben Thanh')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.content), {"results": [{"lat": 10.7, "lng": 106.7, "label": "Chợ Bến Thành"}], "attribution": "© OpenStreetMap contributors"})

    def test_shared_gate_denies_concurrent_requests_before_http(self):
        with patch.object(geocoding, 'connection') as conn, patch.object(geocoding.transaction,'atomic'), patch.object(geocoding,'upstream_search') as upstream:
            conn.vendor = 'postgresql'
            conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (False,)
            with self.assertRaises(BlockingIOError): geocoding.lookup('Ben Thanh')
            upstream.assert_not_called()

    def test_cache_and_cooldown_apply_to_success(self):
        with patch.object(geocoding, 'connection') as conn, patch.object(geocoding.transaction,'atomic'), patch.object(geocoding,'upstream_search',return_value=[]) as upstream, patch.object(geocoding.time,'sleep') as sleep:
            conn.vendor = 'postgresql'
            conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
            self.assertEqual(geocoding.lookup('Ben Thanh'),[])
            self.assertEqual(geocoding.lookup('Ben Thanh'),[])
            upstream.assert_called_once()
            sleep.assert_called_once_with(1.1)

    def test_cooldown_applies_on_upstream_failure(self):
        with patch.object(geocoding, 'connection') as conn, patch.object(geocoding.transaction,'atomic'), patch.object(geocoding,'upstream_search',side_effect=ValueError), patch.object(geocoding.time,'sleep') as sleep:
            conn.vendor = 'postgresql'
            conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
            with self.assertRaises(ValueError): geocoding.lookup('Ben Thanh')
            sleep.assert_called_once_with(1.1)

    def test_upstream_identification_no_redirect_and_vietnam_scope(self):
        with patch.object(geocoding.requests,'get') as get:
            get.return_value.status_code=200
            get.return_value.json.return_value=[]
            self.assertEqual(geocoding.upstream_search('Ben Thanh'),[])
            kwargs=get.call_args.kwargs
            self.assertFalse(kwargs['allow_redirects'])
            self.assertEqual(kwargs['params']['countrycodes'],'vn')
            self.assertIn('AlphaTechBranchFinder',kwargs['headers']['User-Agent'])
