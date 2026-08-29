# Incident Report: INC-20260824 — Payment Gateway Timeout Storm

- **Date / Time**: `2026-08-24 13:02:00 UTC`
- **Severity**: SEV-1 (Critical Revenue Impact)
- **Impacted Systems**: `checkout-web`, `payment-service`, `gateway-proxy`
- **Regions Affected**: All regions (North, South, East, West, Metro)
- **Event Type**: service_outage
- **Status**: Resolved (2026-08-24 15:30 UTC)

## Summary

At 13:02 UTC on August 24, 2026, a cascade of HTTP 504 Gateway Timeout errors began propagating from the payment-service v2.4.1 deployment completed 2 minutes earlier at 13:00 UTC.

The updated connection pool timeout from 30 s → 5 s proved insufficient under peak load, causing checkout requests to time out before upstream tokenization completed.

## Impact

- Checkout conversion rate dropped ~40% across Web and Mobile App channels during 13:02–15:30 UTC
- Approximately 46,000 checkout sessions abandoned in the 2.5-hour window
- Payment failure rate increased from ~0.4% baseline to 11–14% peak
- Checkout error rate: 180–600 errors/hour (baseline: 10–30/hour)
- Revenue impact: ~₹24M shortfall during incident window

## Timeline

| Time (UTC)   | Event |
|--------------|-------|
| 13:00        | payment-service v2.4.1 deployed (connection pool timeout: 30s → 5s) |
| 13:02        | First 504 errors detected on /v2/charge endpoint |
| 13:04        | Connection pool exhausted (active: 50, queued: 128) |
| 13:07        | Checkout aborted errors begin surfacing in checkout-web |
| 13:15        | Retry storm: 1,240 failed tokenization requests/60s |
| 13:22        | Circuit breaker OPEN: gateway-proxy isolates payment-service |
| 13:35        | On-call paged; incident declared SEV-1 |
| 14:05        | Rollback to v2.4.0 initiated |
| 15:30        | Rollback complete; error rate returning to baseline |

## Root Cause

The v2.4.1 release reduced gateway HTTP connection pool timeout from 30s to 5s, intended to improve latency for fast responses. However, card tokenization under peak load regularly takes 8–15s, causing the shortened timeout to trigger premature connection failures and a cascading retry storm.

## Corrective Actions

- Rolled back to v2.4.0 immediately
- Post-mortem scheduled for 2026-08-26
- Timeout floor set to 20s minimum in deployment checklist
