# Deployment Record: Payment Service v2.4.1

- **Service**: `payment-service`
- **Version**: `v2.4.1`
- **Timestamp**: `2026-08-24 13:00:00 UTC`
- **Deployed By**: Release Automation Pipeline (`release-bot`)
- **Environment**: production
- **Event Type**: deployment

## Changes in v2.4.1

- Reduced gateway HTTP connection pool timeout: **30s → 5s** (intended latency improvement)
- Upgraded third-party checkout SDK bindings (stripe-java 4.2 → 4.5)
- Enabled aggressive retry policy on card tokenization endpoints (max_retries: 1 → 3)
- Added request-level tracing headers for observability

## Deployment Status

Completed successfully without deployment pipeline errors or smoke-test failures. Load test was conducted in staging with 20% of production traffic volume — the connection pool issue only manifested at full production peak load.

## Rollback

- Initiated: `2026-08-24 14:05:00 UTC` by `ops-on-call`
- Completed: `2026-08-24 15:30:00 UTC`
- Rollback version: `v2.4.0`
