# Approval contract

- Every mutation has a registered action, required permission, schema-required parameters, workspace-scoped handler, and idempotency key.
- Mutation proposals are type-checked and validate every referenced entity inside the active workspace before an ApprovalRequest is created; invalid quantity/price/state transitions fail closed.
- Recommendation acceptance is allowed only for a registered MUTATION action and a non-expired recommendation. Read-only, unknown, or speculative actions are rejected.
- Duplicate key with identical request returns the existing pending/executed result; duplicate key with changed action or parameters is rejected.
- Reviewer must have workspace approval permission and cannot be requester except explicit superuser policy.
- Rejected, cancelled, expired and executed requests are terminal and cannot be silently replayed.
- PostgreSQL deployments install an append-only AuditLog trigger; stock-transfer now has a transactional, idempotent execution and compensating rollback service. Stock-reorder/workload actions remain unmapped until equivalent domain handlers exist.
