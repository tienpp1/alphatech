"""Connector validation, recursive output redaction and consumed-byte receipts."""
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit
from django.utils import timezone


SECRET_KEY = re.compile(r'password|passwd|pwd|secret|token|key|auth|credential|cookie', re.I)


def safe_endpoint(value):
    """Endpoint identity only: never persist userinfo, query values or fragments."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        if ':' in host:
            host = '[' + host + ']'
        if parsed.port:
            host += ':' + str(parsed.port)
        return urlunsplit((parsed.scheme, host, parsed.path, '', ''))
    except (TypeError, ValueError):
        return '[invalid endpoint]'


def redact(value, *, secret_source=None):
    """Copy a presentation payload; mask credential keys and any echoed values."""
    secrets = set()

    def collect(item, sensitive=False):
        if isinstance(item, dict):
            for key, child in item.items():
                collect(child, sensitive or bool(SECRET_KEY.search(str(key))))
        elif isinstance(item, (list, tuple)):
            for child in item:
                collect(child, sensitive)
        elif sensitive and isinstance(item, (str, int, float)) and not isinstance(item, bool):
            text = str(item)
            if text and text != '******':
                secrets.add(text)
                if text.lower().startswith(('bearer ', 'basic ')) and text.split(' ', 1)[1]:
                    secrets.add(text.split(' ', 1)[1])

    collect(value if secret_source is None else secret_source)
    ordered_secrets = sorted(secrets, key=len, reverse=True)

    def copy(item):
        if isinstance(item, dict):
            return {str(k): '******' if SECRET_KEY.search(str(k)) else copy(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [copy(child) for child in item]
        if isinstance(item, str):
            for secret in ordered_secrets:
                item = item.replace(secret, '******')
            if item.lower().startswith(('http://', 'https://', '/')):
                return safe_endpoint(item)
        return item

    return copy(value)


def validate_connection_config(config):
    if not isinstance(config, dict):
        raise ValueError('Cấu hình nguồn dữ liệu phải là đối tượng JSON.')
    for key in ('headers', 'params'):
        if key in config and not isinstance(config[key], dict):
            raise ValueError('headers và params phải là đối tượng JSON.')
    for key in ('url', 'endpoint_url', 'sheet_name', 'encoding'):
        if key in config and not isinstance(config[key], str):
            raise ValueError('Thuộc tính cấu hình không đúng kiểu dữ liệu.')
    delimiter = config.get('delimiter')
    if delimiter is not None and (not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '\r\n\x00'):
        raise ValueError('Dấu phân tách CSV phải là một ký tự hợp lệ.')
    headers = config.get('headers', {})
    if any(not isinstance(k, str) or not isinstance(v, str) or '\r' in k + v or '\n' in k + v for k, v in headers.items()):
        raise ValueError('HTTP headers không hợp lệ.')
    params = config.get('params', {})
    for key, value in params.items():
        values = value if isinstance(value, list) else [value]
        if not isinstance(key, str) or any(not isinstance(v, (str, int, float, bool, type(None))) for v in values):
            raise ValueError('HTTP params không hợp lệ.')
    return config


def consumed_receipt(content, transport, endpoint=''):
    return {'version': 1, 'transport': transport, 'classification': 'KNOWN_SYNTHETIC' if transport == 'LOCAL_MOCK' else 'UNKNOWN',
            'sha256': hashlib.sha256(content).hexdigest(), 'byte_count': len(content),
            'consumed_at': timezone.now().isoformat(), 'endpoint': safe_endpoint(endpoint)}


def display_source_metadata(metadata):
    result = redact(metadata) if isinstance(metadata, dict) else {}
    result.setdefault('ingestion_provenance', {'version': 1, 'classification': 'UNKNOWN', 'evidence': 'LEGACY_UNRECORDED'})
    return result
