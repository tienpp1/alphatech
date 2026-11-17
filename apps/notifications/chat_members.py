"""Narrow manager-only provisioning; never link or reset an existing identity."""
from django import forms
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.views.decorators.debug import sensitive_variables

from apps.accounts.models import Role, User
from apps.audit.services import log_action
from apps.notifications.chat_service import can_manage_chat_members
from apps.workspaces.models import WorkspaceMembership


class CreateEmployeeForm(forms.Form):
    full_name = forms.CharField(label='Họ và tên', max_length=150)
    email = forms.EmailField(label='Email công việc', max_length=254)
    username = UsernameField(label='Tên đăng nhập', max_length=150,
                             validators=User._meta.get_field('username').validators)
    password1 = forms.CharField(label='Mật khẩu', strip=False, max_length=4096,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = forms.CharField(label='Xác nhận mật khẩu', strip=False, max_length=4096,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email này đã được sử dụng. Không thể thay đổi tài khoản đã có.')
        return email

    def clean_username(self):
        username = User.normalize_username(self.cleaned_data['username'])
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Tên đăng nhập này đã được sử dụng.')
        return username

    @sensitive_variables()
    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password1')
        if password and cleaned.get('password2') and password != cleaned['password2']:
            self.add_error('password2', 'Mật khẩu xác nhận không khớp.')
        if password:
            candidate = User(username=cleaned.get('username', ''), email=cleaned.get('email', ''),
                             first_name=cleaned.get('full_name', ''))
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                for detail in error.error_list:
                    # Django's current minimum-length msgid is not yet present
                    # in its Vietnamese catalog. Keep the validator's actual
                    # threshold/code while localizing this form's error only.
                    if detail.code == 'password_too_short':
                        detail = ValidationError(
                            'Mật khẩu quá ngắn. Cần ít nhất %(min_length)d ký tự.',
                            code=detail.code, params=detail.params,
                        )
                    self.add_error('password1', detail)
        return cleaned


def _employee_memberships(workspace):
    return WorkspaceMembership.objects.filter(
        workspace=workspace, workspace__is_active=True, is_active=True,
        role__name='EMPLOYEE', user__is_active=True, user__is_superuser=False,
    ).exclude(user__social_identities__provider='GOOGLE')


class EmployeeMembershipChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, membership):
        full_name = membership.user.get_full_name()
        username = membership.user.username
        return f'{full_name} ({username})' if full_name else username


class AddEmployeeForm(forms.Form):
    membership = EmployeeMembershipChoiceField(label='Nhân viên', queryset=WorkspaceMembership.objects.none(),
                                               empty_label='Chọn nhân viên cần thêm')

    def __init__(self, user, workspace, data=None, **kwargs):
        super().__init__(data=data, **kwargs)
        self.fields['membership'].error_messages['invalid_choice'] = 'Nhân viên không hợp lệ hoặc không thuộc không gian làm việc này.'
        if can_manage_chat_members(user, workspace):
            pending = Q(team_chat_enabled=False)
            # Accept a repeated POST for the same eligible member, but never list
            # invited people in the ordinary directory or loosen workspace scope.
            selected = data.get('membership') if data is not None else None
            if isinstance(selected, str) and selected.isascii() and selected.isdecimal() and len(selected) <= 19:
                pending |= Q(pk=int(selected))
            self.fields['membership'].queryset = _employee_memberships(workspace).filter(
                pending).select_related('user', 'workspace', 'role').order_by('user__username')


def _lock_manager(actor, workspace):
    # Serialize provisioning with membership updates and recheck current rights.
    membership = WorkspaceMembership.objects.select_for_update().filter(
        user_id=getattr(actor, 'pk', None), workspace=workspace,
    ).first()
    if not membership or not can_manage_chat_members(actor, workspace):
        raise PermissionDenied('Chỉ quản lý của không gian làm việc mới được quản lý thành viên trao đổi.')


@sensitive_variables()
def create_chat_employee(*, workspace, actor, full_name, email, username, password1, password2):
    try:
        with transaction.atomic():
            _lock_manager(actor, workspace)
            form = CreateEmployeeForm(dict(full_name=full_name, email=email, username=username,
                                           password1=password1, password2=password2))
            if not form.is_valid():
                raise ValidationError(form.errors.as_data())
            role = Role.objects.filter(name='EMPLOYEE').first()
            if role is None:
                raise ValidationError('Vai trò nhân viên chưa được cấu hình. Vui lòng liên hệ người vận hành.')
            data = form.cleaned_data
            user = User.objects.create_user(username=data['username'], email=data['email'],
                                            first_name=data['full_name'], password=data['password1'],
                                            is_staff=False, is_superuser=False, is_active=True)
            membership = WorkspaceMembership.objects.create(workspace=workspace, user=user, role=role,
                                                             is_active=True, team_chat_enabled=False)
            log_action(workspace=workspace, actor_user=actor, action='CHAT_EMPLOYEE_CREATED',
                       entity_type='WorkspaceMembership', entity_id=membership.pk,
                       changes={'user_id': user.pk, 'role': 'EMPLOYEE', 'team_chat_enabled': False})
            return membership
    except IntegrityError:
        # The savepoint has rolled back before presenting a safe race/collision error.
        raise ValidationError('Tên đăng nhập hoặc email đã được sử dụng. Vui lòng kiểm tra lại.') from None


@transaction.atomic
def invite_chat_employee(*, workspace, actor, membership_id):
    _lock_manager(actor, workspace)
    try:
        membership = _employee_memberships(workspace).select_for_update().get(pk=membership_id)
    except (WorkspaceMembership.DoesNotExist, ValueError, TypeError, ValidationError):
        raise ValidationError('Nhân viên không hợp lệ hoặc không thuộc không gian làm việc này.') from None
    if not membership.team_chat_enabled:
        membership.team_chat_enabled = True
        membership.save(update_fields=['team_chat_enabled'])
        log_action(workspace=workspace, actor_user=actor, action='CHAT_EMPLOYEE_INVITED',
                   entity_type='WorkspaceMembership', entity_id=membership.pk,
                   changes={'user_id': membership.user_id, 'team_chat_enabled': True})
    return membership
