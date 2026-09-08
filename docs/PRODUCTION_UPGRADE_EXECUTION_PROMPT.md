# Execution prompt used for the production upgrade

Act as the implementation agent for this Django/PostgreSQL/PostGIS repository.
Read AGENTS.md, docs/PROJECT_CONTEXT.md, docs/CURRENT_STATUS.md and the
`specs/001-production-upgrade/` artifacts before changing code. Preserve dirty
worktree changes, workspace isolation, RBAC, Vietnamese public UI and known AI
failure transparency. Execute tasks in dependency order. For every mutation use
additive migrations, scoped queries, transaction locks, idempotency and focused
regressions. Treat local tests as local evidence only; never claim OAuth HTTPS,
SMTP Inbox arrival, staging, secret rotation, observability or restore success
without operator evidence. At each checkpoint report exact commands, results,
remaining gaps and blockers. Stop before declaring production complete when an
external gate is unavailable.
