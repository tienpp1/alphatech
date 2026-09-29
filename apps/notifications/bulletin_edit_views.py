"""Scoped editorial update; no client-controlled author or publication state."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.notifications.bulletin_forms import BulletinEditForm
from apps.notifications.bulletin_service import can_manage_bulletins, update_bulletin
from apps.notifications.models import InternalBulletin
from apps.notifications.services import get_user_authorized_workspaces


def _authorized_workspace(user, workspace_id):
    if not workspace_id:
        raise PermissionDenied("Vui lòng chọn không gian làm việc.")
    try:
        workspace = get_user_authorized_workspaces(user).filter(pk=workspace_id).first()
    except (ValidationError, ValueError, TypeError):
        workspace = None
    if workspace is None or not can_manage_bulletins(user, workspace):
        raise PermissionDenied("Bạn không có quyền cập nhật bản tin trong không gian này.")
    return workspace


@login_required(login_url="/accounts/login/")
@require_http_methods(["GET", "POST"])
def bulletin_edit_ui(request, pk):
    data = request.POST if request.method == "POST" else request.GET
    workspace = _authorized_workspace(request.user, data.get("workspace_id"))
    bulletin = get_object_or_404(InternalBulletin, workspace=workspace, pk=pk)
    form = BulletinEditForm(request.POST if request.method == "POST" else None, instance=bulletin)
    if request.method == "POST" and form.is_valid():
        update_bulletin(workspace, request.user, pk, **form.cleaned_data)
        messages.success(request, "Đã cập nhật bản tin.")
        return redirect(f"/noibo/bang-tin/?workspace_id={workspace.pk}")
    return render(request, "notifications/bulletin_edit.html", {
        "form": form, "bulletin": bulletin, "active_workspace": workspace,
    }, status=400 if request.method == "POST" else 200)


@login_required(login_url="/accounts/login/")
@require_http_methods(["POST"])
def bulletin_update_api(request, pk):
    try:
        data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Dữ liệu không hợp lệ."}, status=400)
    if not hasattr(data, "get"):
        return JsonResponse({"error": "Dữ liệu không hợp lệ."}, status=400)
    workspace = _authorized_workspace(request.user, data.get("workspace_id"))
    bulletin = get_object_or_404(InternalBulletin, workspace=workspace, pk=pk)
    form = BulletinEditForm(data, instance=bulletin)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    bulletin = update_bulletin(workspace, request.user, pk, **form.cleaned_data)
    return JsonResponse({"status": "success", "id": bulletin.pk, "title": bulletin.title})
