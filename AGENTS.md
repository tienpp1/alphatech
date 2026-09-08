# AI Business Platform agent guide

1. Read `docs/PROJECT_CONTEXT.md` first, then `docs/CURRENT_STATUS.md`.
2. Read the relevant source, migrations, routes, and tests before changing code. The repository is the final source of truth when documentation differs.
3. Preserve workspace isolation and workspace-scoped queries. A unified internal UI must not weaken workspace security.
4. Preserve RBAC and the separation between the public customer website and internal management. Public customers must never receive internal membership or permissions.
5. Reuse existing models, routes, services, and conventions; do not create parallel systems or duplicate domain concepts.
6. Never reset a development or production database, rewrite migrations, or modify data unless explicitly requested.
7. Never silently weaken, delete, or skip tests. Run relevant tests after changes.
8. Keep customer-facing UI in Vietnamese unless explicitly requested otherwise.
9. Update `docs/CURRENT_STATUS.md` when implementation status materially changes.
10. Add significant architectural or behavioral changes to `docs/CHANGELOG_AI.md`; do not log cosmetic edits.
11. Update `docs/PROJECT_CONTEXT.md` only when architecture, security invariants, or business behavior changes.
