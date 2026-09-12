"""Explicit public-place lookup. Shared PostgreSQL gate bounds total upstream traffic.

No autocomplete, coordinate/reverse lookup, background queries, or query logging.
Only public place names belong here, never personal/confidential information.
"""
import hashlib
import math
import time
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

GATE_ID = 714830219  # Shared by all app instances using the same database.


def normalize_results(payload):
    if not isinstance(payload, list):
        raise ValueError("invalid_geocoder_response")
    results = []
    for row in payload[:5]:
        try:
            lat, lng = float(row["lat"]), float(row["lon"])
            label = row["display_name"]
            if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
                continue
            if not isinstance(label, str) or not label.strip():
                continue
            results.append({"lat": lat, "lng": lng, "label": label[:500]})
        except (KeyError, TypeError, ValueError):
            continue
    return results


def upstream_search(query):
    endpoint = settings.OSM_GEOCODER_SEARCH_URL
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("invalid_geocoder_configuration")
    response = requests.get(
        endpoint,
        params={"q": query, "format": "jsonv2", "limit": 5, "countrycodes": "vn", "accept-language": "vi"},
        headers={"User-Agent": f"AlphaTechBranchFinder/1.0 (+{settings.PUBLIC_BASE_URL}/chi-nhanh/)", "Accept": "application/json"},
        timeout=(3, 8), allow_redirects=False,
    )
    # Redirects may issue additional requests outside the global request budget.
    if response.status_code != 200:
        raise ValueError("geocoder_unavailable")
    return normalize_results(response.json())


def lookup(query):
    key = "branch-geocoder-v1:" + hashlib.sha256((settings.OSM_GEOCODER_SEARCH_URL + query.casefold()).encode()).hexdigest()
    found = cache.get(key)
    if found is not None:
        return found
    # Fail closed rather than silently use per-process rate limits on other DBs.
    if connection.vendor != "postgresql":
        raise ValueError("shared_geocoder_gate_unavailable")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [GATE_ID])
            if not cursor.fetchone()[0]:
                raise BlockingIOError("geocoder_busy")
        found = cache.get(key)
        if found is not None:
            return found
        try:
            found = upstream_search(query)
            cache.set(key, found, 86400)
            return found
        finally:
            # Hold the shared transaction lock for >1s AFTER the HTTP attempt,
            # including failed attempts. Concurrent clients get 429, not a queue.
            time.sleep(1.1)


@sensitive_post_parameters("q")
@require_POST
@csrf_protect
def public_geocode_view(request):
    query = " ".join(request.POST.get("q", "").split())
    if not 3 <= len(query) <= 200 or any(ord(c) < 32 for c in query):
        return JsonResponse({"error": "Địa điểm cần từ 3 đến 200 ký tự."}, status=400)
    try:
        results = lookup(query)
    except BlockingIOError:
        response = JsonResponse({"error": "Dịch vụ đang có người sử dụng. Vui lòng chờ vài giây rồi bấm Tìm lại."}, status=429)
        response["Retry-After"] = "2"
        return response
    except (requests.RequestException, ValueError):
        return JsonResponse({"error": "Chưa kết nối được dịch vụ OSM. Hãy thử lại hoặc chọn điểm trên bản đồ."}, status=503)
    response = JsonResponse({"results": results, "attribution": "© OpenStreetMap contributors"})
    response["Cache-Control"] = "no-store"
    return response
