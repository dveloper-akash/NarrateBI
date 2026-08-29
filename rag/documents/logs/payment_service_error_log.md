# Application Error Log: payment-service — Aug 24, 2026

- **Date / Time**: `2026-08-24 13:02:00 UTC`
- **Service**: `payment-service`
- **Severity**: SEV-1
- **Event Type**: error_log_digest
- **Status**: Resolved

## Error Log Summary

Extracted from payment-service error stream during INC-20260824 incident window (13:02–15:30 UTC).

```
2026-08-24T13:02:11Z ERROR [payment-service] Gateway timeout: HTTP 504 on /v2/charge endpoint (attempt 1/3)
2026-08-24T13:02:13Z ERROR [payment-service] Gateway timeout: HTTP 504 on /v2/charge endpoint (attempt 2/3)
2026-08-24T13:02:15Z ERROR [payment-service] Gateway timeout: HTTP 504 on /v2/charge endpoint (attempt 3/3) — EXHAUSTED
2026-08-24T13:04:02Z ERROR [payment-service] Connection pool exhausted (active: 50, queued: 128, timeout: 5s)
2026-08-24T13:07:45Z WARN  [checkout-web]    User session checkout aborted: payment unhandled error (session: u-4f92b)
2026-08-24T13:15:18Z ERROR [payment-service] Retry storm: 1,240 failed tokenization requests in 60s
2026-08-24T13:22:01Z FATAL [gateway-proxy]   Circuit breaker OPEN: payment-service upstream unhealthy (error rate: 31%)
2026-08-24T14:00:10Z WARN  [payment-service] Rollback initiated for v2.4.1 connection pool config
2026-08-24T15:30:44Z INFO  [payment-service] Rollback complete — error rate returning to baseline (0.4%)
```

## Aggregate Error Counts

| Time Window  | Error Type          | Count  | Rate/hour |
|--------------|---------------------|--------|-----------|
| 13:00–14:00  | HTTP 504 Timeout    | 14,280 | 14,280    |
| 13:00–14:00  | Checkout Abort      | 8,940  | 8,940     |
| 13:00–14:00  | Payment Failure     | 6,120  | 6,120     |
| 14:00–15:30  | HTTP 504 Timeout    | 4,100  | 2,733     |
| 14:00–15:30  | Payment Failure     | 1,800  | 1,200     |

## Baseline Comparison

Normal error rate: 10–30 checkout errors/hour, 0.4% payment failure rate.
Peak during incident: 180–600 errors/hour, 11–14% failure rate.
