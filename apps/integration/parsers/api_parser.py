"""
REST API Ingestion Parser with Robust SSRF & Network Protection.
Fetches external records from configured HTTP endpoints (including mock external APIs),
validates JSON schema structure, and produces standardized raw staging records.
"""

import io
import json
import os
import socket
import ipaddress
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from django.test import Client

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
DEFAULT_TIMEOUT = 10  # 10 seconds
MAX_TIMEOUT = 15
MAX_REDIRECTS = 3

FORBIDDEN_HOST_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".corp",
    ".lan",
    ".home",
    ".arpa",
)

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
    "metadata.azure.com",
    "169.254.169.254",
}


def is_ip_allowed(ip_obj: Any) -> bool:
    """
    Checks if an IP address is a publicly routable global address.
    Rejects loopback, private, link-local, multicast, reserved, unspecified, and CGNAT.
    """
    if (
        ip_obj.is_loopback
        or ip_obj.is_private
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return False

    # Carrier-grade NAT (100.64.0.0/10)
    cgnat = ipaddress.ip_network("100.64.0.0/10")
    if isinstance(ip_obj, ipaddress.IPv4Address) and ip_obj in cgnat:
        return False

    return True


def validate_safe_remote_url(url_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a remote URL is safe from SSRF attacks.
    - Scheme must be http or https
    - Hostname cannot be localhost, cloud metadata, or private domain suffix
    - Resolved IP addresses cannot be private, loopback, link-local, or multicast
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Forbidden URL scheme '{scheme}'. Only HTTP and HTTPS are allowed."

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        return False, "URL is missing a valid hostname."

    # Direct hostname check
    if hostname in FORBIDDEN_HOSTNAMES:
        return False, f"Access to restricted hostname '{hostname}' is blocked (SSRF Protection)."

    for suffix in FORBIDDEN_HOST_SUFFIXES:
        if hostname.endswith(suffix):
            return False, f"Access to internal domain suffix '{suffix}' is blocked (SSRF Protection)."

    # If hostname is a raw IP literal
    try:
        ip_str = hostname.strip("[]")
        ip_obj = ipaddress.ip_address(ip_str)
        if not is_ip_allowed(ip_obj):
            return False, f"Access to private or loopback IP address '{ip_obj}' is blocked (SSRF Protection)."
        return True, None
    except ValueError:
        # Hostname is a domain name, proceed to DNS resolution
        pass

    # Resolve DNS to check IP addresses
    try:
        port = parsed.port or (443 if scheme == "https" else 80)
        addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        resolved_ips = set()
        for family, socktype, proto, canonname, sockaddr in addr_info:
            resolved_ips.add(sockaddr[0])

        if not resolved_ips:
            return False, f"Could not resolve hostname '{hostname}'."

        for ip_str in resolved_ips:
            ip_obj = ipaddress.ip_address(ip_str)
            if not is_ip_allowed(ip_obj):
                return False, f"Hostname '{hostname}' resolves to restricted IP '{ip_str}' (SSRF Protection)."

    except socket.gaierror:
        return False, f"DNS resolution failed for hostname '{hostname}'."
    except Exception as e:
        return False, f"Network validation failed for '{hostname}': {str(e)}"

    return True, None


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Intercepts HTTP redirects and verifies destination URL against SSRF policy."""
    def __init__(self, max_redirects: int = MAX_REDIRECTS):
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise urllib.error.HTTPError(req.full_url, code, "Excessive redirects encountered.", headers, fp)

        is_safe, error_msg = validate_safe_remote_url(newurl)
        if not is_safe:
            raise urllib.error.HTTPError(req.full_url, code, f"Redirect to unsafe destination blocked: {error_msg}", headers, fp)

        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_and_parse_api(
    endpoint_url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Fetches JSON records from a REST endpoint with SSRF protections.
    Supports both local relative URLs (via Django test client) and remote URLs (via urllib.request).

    Returns:
    {
        "columns": List[str],
        "rows": List[{
            "row_number": int,
            "raw_data": Dict[str, Any],
            "is_valid": bool,
            "errors": List[str],
        }],
        "total_rows": int,
        "source_url": str,
        "warnings": List[str],
        "is_valid": bool,
        "error_message": Optional[str],
    }
    """
    if not endpoint_url or not endpoint_url.strip():
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": "",
            "warnings": [],
            "is_valid": False,
            "error_message": "Endpoint URL is required.",
        }

    url = endpoint_url.strip()
    effective_timeout = max(1, min(timeout, MAX_TIMEOUT))
    raw_json = None
    warnings = []

    try:
        if url.startswith("http://") or url.startswith("https://"):
            # 1. Validate remote URL for SSRF protection
            is_safe, error_msg = validate_safe_remote_url(url)
            if not is_safe:
                return {
                    "columns": [],
                    "rows": [],
                    "total_rows": 0,
                    "source_url": url,
                    "warnings": [],
                    "is_valid": False,
                    "error_message": f"Security Validation Error: {error_msg}",
                }

            # 2. Execute remote request with SafeRedirectHandler & size streaming limit
            req = urllib.request.Request(url, headers=headers or {})
            opener = urllib.request.build_opener(SafeRedirectHandler())

            with opener.open(req, timeout=effective_timeout) as response:
                if response.status != 200:
                    return {
                        "columns": [],
                        "rows": [],
                        "total_rows": 0,
                        "source_url": url,
                        "warnings": [],
                        "is_valid": False,
                        "error_message": f"API request failed with HTTP status {response.status}",
                    }

                # Read response in chunks up to MAX_RESPONSE_SIZE
                chunks = []
                total_bytes = 0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_RESPONSE_SIZE:
                        return {
                            "columns": [],
                            "rows": [],
                            "total_rows": 0,
                            "source_url": url,
                            "warnings": [],
                            "is_valid": False,
                            "error_message": f"Response size exceeded the maximum allowed limit of {MAX_RESPONSE_SIZE // (1024 * 1024)} MB.",
                        }
                    chunks.append(chunk)

                content = b"".join(chunks).decode("utf-8")
                raw_json = json.loads(content)

        elif url.startswith("/"):
            # Local / relative mock endpoint (e.g. /api/v1/mock-external/...)
            # Disallow scheme-relative URLs (//)
            if url.startswith("//"):
                return {
                    "columns": [],
                    "rows": [],
                    "total_rows": 0,
                    "source_url": url,
                    "warnings": [],
                    "is_valid": False,
                    "error_message": "Invalid relative endpoint format.",
                }

            client = Client()
            resp = client.get(url, data=params or {}, **{f"HTTP_{k.upper().replace('-', '_')}": v for k, v in (headers or {}).items()})
            if resp.status_code != 200:
                return {
                    "columns": [],
                    "rows": [],
                    "total_rows": 0,
                    "source_url": url,
                    "warnings": [],
                    "is_valid": False,
                    "error_message": f"Local API endpoint returned HTTP status {resp.status_code}.",
                }
            raw_json = resp.json()
        else:
            return {
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "source_url": url,
                "warnings": [],
                "is_valid": False,
                "error_message": f"Invalid URL scheme or format for '{url}'. Remote URLs must start with 'http://' or 'https://', and local endpoints must start with '/'.",
            }

    except urllib.error.HTTPError as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": f"HTTP Error ({e.code}): {e.reason}",
        }
    except urllib.error.URLError as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": f"Network Connection Error: {e.reason}",
        }
    except json.JSONDecodeError as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": f"Invalid JSON response returned by endpoint: {str(e)}",
        }
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": f"Network error connecting to endpoint: {str(e)}",
        }

    # Extract record array from raw_json
    records_list = []
    if isinstance(raw_json, list):
        records_list = raw_json
    elif isinstance(raw_json, dict):
        # Unpack envelope: check common container keys
        for key in ("data", "results", "items", "records", "orders", "customers", "products", "tickets", "technicians"):
            if key in raw_json and isinstance(raw_json[key], list):
                records_list = raw_json[key]
                break
        if not records_list:
            # Single object response: wrap as single record
            records_list = [raw_json]
    else:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": "JSON response root must be an array or envelope object.",
        }

    if not records_list:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": ["Endpoint returned an empty dataset."],
            "is_valid": False,
            "error_message": "External API returned zero records.",
        }

    # Extract columns as the union of all keys across objects
    col_set = []
    for item in records_list:
        if isinstance(item, dict):
            for k in item.keys():
                if k not in col_set:
                    col_set.append(k)

    if not col_set:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "source_url": url,
            "warnings": [],
            "is_valid": False,
            "error_message": "No structured dictionary records found in API response.",
        }

    # Standardize rows into RawImportRecord representation
    rows = []
    for idx, item in enumerate(records_list, start=1):
        if not isinstance(item, dict):
            rows.append({
                "row_number": idx,
                "raw_data": {"_raw_value": str(item)},
                "is_valid": False,
                "errors": [f"Row {idx} is not a valid JSON object."],
            })
        else:
            # Flatten or format any complex sub-objects to strings/dicts
            clean_record = {}
            for k in col_set:
                val = item.get(k)
                clean_record[k] = val

            rows.append({
                "row_number": idx,
                "raw_data": clean_record,
                "is_valid": True,
                "errors": [],
            })

    return {
        "columns": col_set,
        "rows": rows,
        "total_rows": len(rows),
        "source_url": url,
        "warnings": warnings,
        "is_valid": True,
        "error_message": None,
    }
