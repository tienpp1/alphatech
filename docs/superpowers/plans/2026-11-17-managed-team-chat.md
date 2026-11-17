# Managed team chat implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Manager-controlled employee account creation and opt-in workspace chat.

**Architecture:** Reuse User/WorkspaceMembership and existing chat endpoints.
One additive membership flag distinguishes internal employment from chat access.
Fixed-role provisioning/invitation lives in a small scoped service module.

**Tech Stack:** Django/PostGIS, templates/forms, existing polling JavaScript.

**Spec:** docs/superpowers/specs/2026-11-17-managed-team-chat-design.md

## Global constraints

- Only MANAGER and invited EMPLOYEE, never ADMIN/superuser/Google/public.
- No broad accounts.manage_user grant; preserve workspace and public boundaries.
- Reuse models/services, no business DB reset or old-migration rewrite.
- Preserve old messages and migrated employee access; new memberships opt in.
- No progress/structure edits to97ledger; Vietnamese UI; secrets never in logs.

## Review focus

- Forged workspace/user/role/staff fields must not expand authority.
- Existing-email collisions, revoked manager rights and duplicate submits safe.
- Pending EMPLOYEE cannot read through API/history/fallback HTML or roster.
- ADMIN remains allowed elsewhere, but cannot bypass chat via superuser flag.
- Mobile manager forms remain reachable despite currently hidden chat sidebar.

### Task1: Scoped backend, migration and acceptance contracts

**Files:** apps/workspaces/models.py, migrations/0002_team_chat_enabled.py,
context_processors.py; apps/notifications/chat_service.py, ui_views.py,
chat_members.py, chat_member_views.py; config/urls.py; tests/test_managed_team_chat.py
and existing chat fixture/contracts; existing CI/acceptance test manifest if needed.

**Interfaces:** Spec names/context above are authoritative. Forms/routes share
their existing workspace selector resolver and standard CSRF login protection.

- [ ] Write HTTP/service tests first; observe missing behavior RED using isolated
  loopback evidence DB, including role matrix, pending/invited/revoked access,
  cross-workspace selectors, collisions, rollback, password validation/audit.
- [ ] Add the new flag and forward-only migration preserving historical rows.
- [ ] Implement scoped role/invitation helpers, fixed-role creation and views.
  Add `team_chat_page_context(request,workspace,employee_form=None,
  add_employee_form=None,chat_management_panel='')` to chat_member_views for
  consistent bound-error and ordinary page context; avoid circular module imports.
- [ ] Update existing authorized-chat fixtures to explicit invitations and replace
  old ADMIN-chat expectations with manager fixtures plus explicit ADMIN-denial
  tests. Preserve all isolation/history/bulletin/Google/security assertions.
- [ ] Focused tests GREEN; migration-state dry-run no drift on TEST only.

### Task2: Accessible Vietnamese management UI

**Files:** templates/notifications/team_chat.html, templates/base.html,
tests/test_managed_team_chat_ui.py (render/HTTP tests).

**Consumes:** Task1 context/form contracts; canonical POST URLs above.
**Produces:** two manager-only actions, current roster and friendly invite notice.

- [ ] Write rendering tests for manager controls vs EMPLOYEE/no controls, error
  field preservation/no password echo; observe RED before template changes.
- [ ] Add create and invite panels using labelled native controls/CSRF/forms,
  visible workspace/fixed role, inline errors and accessible error summary.
  Put actions above chat so mobile users can access; retain draft/history IDs.
- [ ] Wrap Trao đổi nav in can_use_team_chat. Keep chat scrollbar/composer usable
  on375px. No new JS dependency or polling changes.
- [ ] UI tests GREEN; browser local manager/create/pending/invite/employee-send,
  admin-denial and cross-workspace checks on a disposable test DB only.

### Task3: Integration, evidence and release

**Files:** docs/PROJECT_CONTEXT.md, CURRENT_STATUS.md, CHANGELOG_AI.md;
local output/managed_team_chat_20261117 scripts/receipts, not committed secrets.

- [ ] Independent read-only review; repair important findings with regression tests.
- [ ] Run full Django suite once source freezes, aggregate JS and security/secret
  scan. Report any failures faithfully, never skip tests to green.
- [ ] Apply only task diff to dirty primary checkout; preserve all unrelated work.
- [ ] Scoped commit/push, existing RenderFree deploy after verified migration;
  read-only production manager UI + retired ADMIN denial, no real employees made.
- [ ] Record exact test/CI/live evidence and user-facing operating instructions.
