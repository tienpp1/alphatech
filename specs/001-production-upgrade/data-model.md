# Data model

## Customer ownership

`retail.Customer.user` is nullable, points to the custom User, and has a unique `(workspace, user)` constraint. Authenticated submissions use `(workspace, user)`; guests create an unowned Customer. Submitted email is a notification/delivery value, not proof of ownership.

## Public event entities

`public_web.ContactSubmission`: optional workspace/user, name, email, phone, message, public UUID, deduplication key, created timestamp. Workspace can be null when routing is not configured.

`public_web.OrderDeliveryAddress`: one-to-one order snapshot containing recipient, email, phone, address, district, city, delivery method, and created timestamp.

## Forecast lifecycle

`forecasting.ForecastRun`: PENDING/RUNNING/COMPLETED/FAILED/CANCELLED, parameters, attempt count, lease token/expiry, heartbeat, cancel flag, training timestamps, metrics and artifact path. A worker may publish only while holding a valid lease token.

## Approval lifecycle

`approvals.ApprovalRequest`: workspace, requester, action, immutable parameters, idempotency key, reviewer, status, decision and execution result. Database constraint: unique `(workspace, idempotency_key)`.

## Production evidence

External evidence is documented in `docs/CURRENT_STATUS.md` and the checklist; secrets and mailbox contents are never stored in repository artifacts.
