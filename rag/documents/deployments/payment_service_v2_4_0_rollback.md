# Deployment Record: payment-service v2.4.0 (Rollback)

- **Date / Time**: `2026-08-24 14:05:00 UTC`
- **Service**: `payment-service`
- **Version**: `v2.4.0`
- **Status**: completed
- **Deployed By**: `ops-on-call`
- **Environment**: production
- **Event Type**: rollback

## Summary

Emergency rollback of payment-service from v2.4.1 to v2.4.0 executed by on-call engineer at 14:05 UTC in response to SEV-1 incident INC-20260824.

## Rollback Scope

- Reverted HTTP connection pool timeout: 5s → 30s
- Reverted retry-on-timeout policy change
- All active sessions rebalanced within 3 minutes of rollback

## Validation

- Error rate returned to baseline (< 0.5%) by 15:30 UTC
- Checkout conversion rate recovered to pre-deployment levels
- Payment failure rate confirmed normal by 15:45 UTC

## Related Incident

INC-20260824 — See incident report for full root-cause analysis.
