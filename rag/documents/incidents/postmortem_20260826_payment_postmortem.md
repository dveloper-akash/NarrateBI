# Post-Mortem Report: INC-20260824 — Payment Gateway Timeout Storm

- **Date / Time**: `2026-08-26 10:00:00 UTC`
- **Service**: `payment-service`
- **Severity**: SEV-1
- **Event Type**: post_mortem
- **Status**: Closed

## Executive Summary

On 2026-08-24 at 13:02 UTC, a payment-service deployment (v2.4.1) caused a cascade of 504 timeout errors that reduced checkout conversion by ~40% for 2.5 hours across all regions. Approximately ₹24M in revenue was lost. The root cause was an overly aggressive connection pool timeout reduction (30s → 5s) that was insufficient for card tokenization under peak load.

## Timeline

| Time (UTC)   | Event |
|--------------|-------|
| 13:00        | payment-service v2.4.1 deployed |
| 13:02        | 504 errors detected |
| 13:22        | Circuit breaker OPEN |
| 14:05        | Rollback to v2.4.0 initiated |
| 15:30        | Service restored to baseline |

## Contributing Factors

1. Missing load-test coverage for tokenization latency at P99 (8–15s under peak)
2. No canary deployment — change went straight to 100% production traffic
3. Alerting threshold was 5 minutes, allowing ~5 minutes of undetected degradation

## Corrective Actions

- [x] Rollback to v2.4.0 completed (2026-08-24 15:30)
- [ ] Add P99 tokenization latency SLO to deployment checklist
- [ ] Implement canary deployment policy (10% traffic before full rollout)
- [ ] Lower alert threshold from 5 min → 90 seconds for payment error rate

## Impact Quantification

- Revenue loss: ~₹24M (2.5-hour window)
- Checkout sessions abandoned: ~46,000
- Peak payment failure rate: 11–14% (baseline: 0.4%)
- Peak checkout error rate: 180–600 errors/hour (baseline: 10–30/hour)
