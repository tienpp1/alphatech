"""HTTPS transport for fixed provider endpoints; credentials never follow redirects."""
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


class RejectProviderRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise URLError('Provider redirect rejected')


def open_provider_request(request, *, allowed_hosts, timeout, use_env_proxy=True):
    url = request.full_url if hasattr(request, 'full_url') else request
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname in allowed_hosts
                 and parsed.port in (None, 443) and not parsed.username
                 and not parsed.password and not parsed.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise URLError('Provider endpoint rejected')
    handlers = [RejectProviderRedirects()]
    if not use_env_proxy:
        handlers.append(ProxyHandler({}))
    return build_opener(*handlers).open(request, timeout=timeout)
