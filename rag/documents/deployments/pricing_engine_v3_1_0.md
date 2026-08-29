# Deployment Record: pricing-engine v3.1.0

- **Date / Time**: `2026-08-22 08:55:00 UTC`
- **Service**: `pricing-engine`
- **Version**: `v3.1.0`
- **Status**: completed
- **Deployed By**: `pricing-team`
- **Environment**: production
- **Event Type**: feature_deployment

## Summary

Deployed pricing-engine v3.1.0 implementing the Q3 "Premium Margin Recapture" initiative approved by the Commercial Analytics team on 2026-08-20.

## Changes

1. **List price adjustments**: Electronics +18%, Apparel +12% effective immediately
2. **Discount suppression**: Promotional discount codes for `New` and `Returning` segments disabled; `Premium` and `Enterprise` discount eligibility unchanged
3. **Cart abandonment threshold**: Increased abandoned cart follow-up email trigger from 30 min → 60 min (to reduce operational cost)

## Expected Business Impact

- AOV target: +15–20% for Electronics and Apparel
- Short-term conversion trade-off accepted per commercial strategy memo (CSM-2026-081)
- 4-week re-assessment checkpoint: 2026-09-19

## Monitored Metrics

| Metric             | Pre-Deploy (Baseline) | Target        |
|--------------------|----------------------|---------------|
| AOV (All)          | ~₹1,590              | ₹1,850–1,950  |
| Conversion Rate    | ~3.94%               | ≥3.0% acceptable |
| Revenue            | Baseline week        | ≥-8% acceptable |
