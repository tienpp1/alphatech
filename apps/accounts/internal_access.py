"""Google-linked customer identities never authorize internal operations."""
from django.http import JsonResponse
from django.db.models import Q

AUTH_METHOD_KEY = "platform_auth_method"


def has_internal_role(user):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    # Check before the legacy superuser bypass: linking Google classifies this
    # identity as public-only, even with an old password, role, or API token.
    if user.social_identities.filter(provider="GOOGLE").exists():
        return False
    if user.is_superuser:
        return True
    from apps.workspaces.models import WorkspaceMembership
    return WorkspaceMembership.objects.filter(
        Q(role__name__iexact="ADMIN") | Q(role__name__iexact="MANAGER")
        | Q(role__name__iexact="EMPLOYEE"),
        user=user, is_active=True, workspace__is_active=True,
    ).exists()


def is_public_only_session(user, session):
    if (user and user.is_authenticated and
            user.social_identities.filter(provider="GOOGLE").exists()):
        return True
    method = session.get(AUTH_METHOD_KEY)
    if method == "google":
        return True
    if method == "password":
        return False
    return False


def can_access_internal(request):
    return (has_internal_role(request.user) and
            not is_public_only_session(request.user, request.session))


def is_public_view(view):
    return view.__module__.startswith("apps.public_web.")


def is_public_destination(url):
    from urllib.parse import urlsplit
    from django.urls import resolve, Resolver404
    try:
        return is_public_view(resolve(urlsplit(url).path).func)
    except Resolver404:
        return False


class InternalAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or is_public_view(view_func):
            return None
        if view_func.__module__ == "django.views.static":
            return None  # Public MEDIA_URL serving in DEBUG; WhiteNoise handles assets.
        # Password reauthentication and logout must remain reachable.
        name = request.resolver_match.url_name
        if view_func.__module__ == "apps.accounts.ui_views":
            return None
        if name in ("health_check", "api_health_check"):
            return None
        if request.path == "/api/v1/auth/login/":
            return None
        if not can_access_internal(request):
            if request.path == "/noibo/" and not is_public_only_session(request.user, request.session):
                from django.shortcuts import redirect
                return redirect("/tai-khoan/?notice=customer_only")
            return JsonResponse({"detail": "Cổng nội bộ chỉ dành cho ADMIN, MANAGER và EMPLOYEE đăng nhập bằng mật khẩu."}, status=403)
