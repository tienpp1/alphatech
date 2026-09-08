"""
Web UI Authentication Views (Session-based Login & Logout).
Handles browser authentication flow, session establishment, and safe URL redirection.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.authtoken.models import Token

from apps.accounts.services import authenticate_user
from apps.workspaces.models import WorkspaceMembership


def login_ui_view(request):
    """
    GET /accounts/login/
    POST /accounts/login/
    Renders login template and establishes authenticated browser session.
    """
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    # If user is already authenticated, redirect immediately
    if request.user.is_authenticated:
        if (
            next_url
            and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
            and not next_url.startswith("/accounts/login")
            and not next_url.startswith("/accounts/logout")
        ):
            return redirect(next_url)
        return redirect("/noibo/")

    error_message = None
    logged_out_notice = request.GET.get("logged_out") == "1"

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate_user(username, password)
        if user:
            # 1. Establish Django session authentication
            login(request, user)

            # 2. Get or create DRF Token
            Token.objects.get_or_create(user=user)

            # 3. Establish default active workspace in session
            memberships = (
                WorkspaceMembership.objects.filter(user=user, is_active=True)
                .select_related("workspace", "role")
                .order_by("-is_default", "joined_at")
            )
            if memberships.exists():
                default_membership = memberships.first()
                request.session["active_workspace_id"] = str(default_membership.workspace.id)

            # 4. Safe redirection respecting ?next=...
            if (
                next_url
                and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
                and not next_url.startswith("/accounts/login")
                and not next_url.startswith("/accounts/logout")
            ):
                return redirect(next_url)

            return redirect("/noibo/")
        else:
            error_message = "Tên đăng nhập hoặc mật khẩu không chính xác, hoặc tài khoản đã bị khóa."

    context = {
        "next": next_url,
        "error": error_message,
        "logged_out": logged_out_notice,
    }
    return render(request, "accounts/login.html", context)


def logout_ui_view(request):
    """
    GET /accounts/logout/
    POST /accounts/logout/
    Flushes session, deletes active token, and redirects to public website root (/).
    """
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user).delete()
        logout(request)
    return redirect("/")

