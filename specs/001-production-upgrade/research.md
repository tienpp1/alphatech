# Research decisions

## Decision: PostgreSQL-backed forecast worker

The repository has no Celery/RQ broker or deployment configuration. A durable `ForecastRun` queue with row locks, expiring lease tokens, heartbeat, bounded retry and a supervised management command satisfies restart recovery without introducing a parallel queue system.

## Decision: explicit ownership, additive migration

`Customer.user` is nullable for safe historical/guest records and unique per workspace. Existing records are not merged by email/name/phone without evidence. `ContactSubmission` and `OrderDeliveryAddress` preserve event-time facts.

## Decision: dimensions in immutable job parameters

Product, category and branch identifiers are validated against the workspace before aggregation and stored in the run snapshot. Forecast artifacts remain trusted local files.

## Decision: production evidence is a separate gate

Local tests cannot prove secret rotation, HTTPS callback, Inbox arrival, staging observability or database restore. Those items remain BLOCKED until operator evidence is supplied.
