"""Canonical management POSTs and the shared, actor-scoped chat context."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.utils import translation

from apps.notifications.chat_members import (
    AddEmployeeForm, CreateEmployeeForm, create_chat_employee, invite_chat_employee,
)
from apps.notifications.chat_service import (
    can_manage_chat_members, get_chat_workspaces, get_recent_team_messages,
    get_workspace_colleagues, verify_chat_access,
)
from apps.notifications.services import resolve_collaboration_workspace


def team_chat_page_context(request, workspace, employee_form=None,
                           add_employee_form=None, chat_management_panel=''):
    if not verify_chat_access(request.user, workspace):
        raise PermissionDenied('Bạn chưa được cấp quyền tham gia kênh trao đổi này.')
    history = get_recent_team_messages(workspace, request.user, limit=50)
    oldest_id = history[0].id if history else 0
    can_manage = can_manage_chat_members(request.user, workspace)
    return {
        'active_workspace': workspace,
        'authorized_workspaces': get_chat_workspaces(request.user),
        'messages_list': history,
        'colleagues': get_workspace_colleagues(workspace, request.user),
        'latest_message_id': history[-1].id if history else 0,
        'oldest_message_id': oldest_id,
        'has_older_messages': bool(history and get_recent_team_messages(
            workspace, request.user, limit=1, before_id=oldest_id)),
        'can_manage_chat': can_manage,
        'employee_form': (employee_form if employee_form is not None else CreateEmployeeForm()) if can_manage else None,
        'add_employee_form': (add_employee_form if add_employee_form is not None else AddEmployeeForm(request.user, workspace)) if can_manage else None,
        'chat_management_panel': chat_management_panel if can_manage else '',
    }


def _managed_workspace(request):
    workspace = resolve_collaboration_workspace(
        request, request.POST, allowed_workspaces=get_chat_workspaces(request.user))
    # A query selector must not disagree with the submitted workspace either.
    if 'workspace_id' in request.GET:
        queried = resolve_collaboration_workspace(
            request, request.GET, allowed_workspaces=get_chat_workspaces(request.user))
        if not queried or not workspace or queried.pk != workspace.pk:
            raise PermissionDenied('Không gian làm việc không hợp lệ.')
    if workspace is None or not can_manage_chat_members(request.user, workspace):
        raise PermissionDenied('Chỉ quản lý được quản lý thành viên kênh trao đổi này.')
    return workspace


def _form_error(form, error, field=None):
    if hasattr(error, 'error_dict'):
        for name, errors in error.error_dict.items():
            form.add_error(name if name in form.fields else None, errors)
    else:
        form.add_error(field, error)


@login_required(login_url='/accounts/login/')
@require_POST
@translation.override('vi')
@sensitive_post_parameters()
@sensitive_variables()
def chat_employee_create_view(request):
    workspace = _managed_workspace(request)
    form = CreateEmployeeForm(request.POST)
    if form.is_valid():
        try:
            create_chat_employee(workspace=workspace, actor=request.user, **form.cleaned_data)
        except ValidationError as error:
            _form_error(form, error)
        else:
            messages.success(request, 'Đã tạo tài khoản nhân viên. Hãy thêm nhân viên vào kênh trao đổi khi sẵn sàng.')
            return redirect(f'/noibo/trao-doi/?workspace_id={workspace.pk}')
    return render(request, 'notifications/team_chat.html', team_chat_page_context(
        request, workspace, employee_form=form, chat_management_panel='create'), status=400)


@login_required(login_url='/accounts/login/')
@require_POST
@translation.override('vi')
def chat_employee_add_view(request):
    workspace = _managed_workspace(request)
    form = AddEmployeeForm(request.user, workspace, request.POST)
    if form.is_valid():
        try:
            invite_chat_employee(workspace=workspace, actor=request.user,
                                 membership_id=form.cleaned_data['membership'].pk)
        except ValidationError as error:
            _form_error(form, error, 'membership')
        else:
            messages.success(request, 'Nhân viên đã được thêm vào kênh trao đổi.')
            return redirect(f'/noibo/trao-doi/?workspace_id={workspace.pk}')
    return render(request, 'notifications/team_chat.html', team_chat_page_context(
        request, workspace, add_employee_form=form, chat_management_panel='add'), status=400)
