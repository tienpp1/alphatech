# Trao đổi riêng cho quản lý và nhân viên

User approved the complete description in chat on17/11/2026. Build on the
existing workspace chat; no new chat/identity/technician model.

## Required behavior

- Only active non-Google, non-superuser MANAGER and invited EMPLOYEE members
  of the selected active workspace can read/send chat or appear in its roster.
  ADMIN (including superuser), VIEWER/custom roles and public users are denied.
- MANAGER can create a new password-based EMPLOYEE account directly from chat:
  full name, work email, username, password and confirmation. Reuse User and
  WorkspaceMembership; fixed EMPLOYEE role, no staff/superuser/model permissions.
  No promotion/reset of any existing customer/account, even with matching email.
- New employee membership defaults to chat-disabled. A separate manager-only
  button selects an existing active non-Google EMPLOYEE in THIS workspace and
  enables chat. Creating the account alone never authorizes chat.
- Keep pre-existing employee access when migrating, and preserve all messages.
  This compatibility default is the implementer's decision communicated before
  work. New memberships default false; only managers bypass the invitation flag.
- All UI/API/service entry points enforce role/workspace/invitation checks.
  No broad accounts.manage_user grant. Invitation is idempotent and audited;
  creating identity/membership/audit is atomic. Never log credentials or email.
- Keep 3s polling, ID history cursor, drafts, bulletin behavior and public-vs-
  internal isolation. Revoked access stops future polls/sends without reload.
- UI Vietnamese, existing dark styling, keyboard labels/errors, mobile usable.
  No real employee/customer/message production fixture writes for tests.
- No resets, no migration rewrites, no97-ledger structure/progress change.

## Persistence and interfaces

Add `WorkspaceMembership.team_chat_enabled = BooleanField(default=False,
db_default=False)`. New0002 AddField initially uses defaultTrue/db_defaultTrue,
then AlterField changes both defaultsFalse (verify migration state matches the
model). This preserves existing rows and lets an old app version omit the new
column during rolling deployment without NOTNULL errors. Existing rows are not
otherwise edited. Tests explicitly opt in fixture EMPLOYEEs when needed.

Existing chat_service exports stay; add `can_manage_chat_members(user,workspace)`
and `get_chat_workspaces(user)` (QuerySet). No superuser bypass.

New module `apps/notifications/chat_members.py` provides scoped provisioning
and invitation services and Django forms. New module `chat_member_views.py`
provides manager-only CSRF-protected POST endpoints. Canonical routes:
`/noibo/trao-doi/nhan-vien/tao/`, `/noibo/trao-doi/thanh-vien/them/`.
On success redirect to canonical chat workspace URL; on invalid form render
chat with status400 and bound non-password fields; forbidden returns403.

Chat template context: `can_manage_chat`, `employee_form` (full_name,email,
username,password1,password2), `add_employee_form` (`membership` ModelChoice),
`chat_management_panel` = 'create'/'add'/''. Manager sees both forms/buttons;
EMPLOYEE never receives account-directory/form data. Context processor exposes
`can_use_team_chat` for navigation based on actual permitted chat workspaces.

## Out of scope

No HR/payroll/technician records, departments, phone fields, attachments,
private DMs, new channels, Google/internal role linking, adminUI restoration,
new broad account editor, or worker/provider infrastructure changes.
