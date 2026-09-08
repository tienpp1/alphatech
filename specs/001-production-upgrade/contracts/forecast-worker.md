# Forecast worker contract

- Enqueue: create one `ForecastRun(status=PENDING)` with immutable dimensions and parameters.
- Claim: worker changes PENDING to RUNNING under row lock and receives a lease token.
- Heartbeat: worker extends lease only while token and status match.
- Recovery: expired RUNNING jobs return to PENDING until the bounded attempt limit, then FAILED; cancellation is terminal.
- Completion: training and future results publish only with a valid token; stale workers fail closed.
