# Production upgrade execution contract

Status: in progress; not a production acceptance certificate.

Implement against current source, preserve unrelated changes and never infer
customer ownership from submitted email, phone or name. Use additive migrations;
do not silently merge historical customer records. Keep Vietnamese UI and RBAC.

Ordered checkpoints:
1. Explicit workspace-local customer account identity; structured address/contact records.
2. Durable forecasting worker with leases, bounded recovery/retry and cancellation.
3. Scoped SKU/category/branch datasets, chronological backtests and model monitoring.
4. Validated recommendation action contracts, human approval and compensation semantics.
5. Database idempotency and append-only audit; concurrent execution regressions.
6. Ground the two demonstration failures in canonical data; repair stale fixtures honestly.
7. CI PostgreSQL/PostGIS gates, staging/observability and backup/restore runbooks.
8. Real deployment acceptance: secret rotation, HTTPS OAuth, inbox receipt and restore drill.

For each checkpoint inspect source and tests, implement, run focused regressions,
then record exact results. Passing simulations cannot satisfy live acceptance.
External steps remain blocked until evidence is supplied; do not claim all eight done.
