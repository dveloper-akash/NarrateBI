# Incident Report: INC-84920 - Payment Gateway Timeout Storm

- **Date / Time**: `2026-08-26 14:15:00 UTC`
- **Severity**: SEV-1 (Critical Revenue Impact)
- **Impacted Systems**: `checkout-web`, `payment-service`, `gateway-proxy`
- **Summary**:
  - Spike in checkout errors observed at 14:15 UTC (15 mins following v2.4.1 release).
  - Upstream gateway endpoints responded with HTTP 504 Gateway Timeout on checkout requests.
  - Overall checkout conversion dropped sharply by ~18% across mobile and web platforms.
- **Immediate Action**: Ops on-call paged; investigating connection pool configuration on payment-service v2.4.1.
