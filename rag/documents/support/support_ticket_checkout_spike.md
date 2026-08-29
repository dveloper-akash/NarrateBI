# Support Escalation Digest: Customer Checkout Failures — August 24

- **Time Window**: `2026-08-24 13:18 — 15:30 UTC`
- **Service**: `checkout-web`, `payment-service`
- **Severity**: Critical
- **Event Type**: support_escalation
- **Volume**: 312 new tickets created (Normal baseline: 8/hour)

## Top Customer Complaint Themes

- "Card was charged but order confirmation screen never loaded" (92 tickets)
- "Spinning wheel at payment step then 504 error page" (87 tickets)
- "Tried 3 times to checkout — failed every time; had to abandon cart" (74 tickets)
- "Promo code accepted but payment still failed" (41 tickets)
- "App crashed at payment screen after entering CVV" (18 tickets)

## Channel Breakdown

| Channel     | Tickets | % of Total |
|-------------|---------|------------|
| Mobile App  | 143     | 45.8%      |
| Web         | 121     | 38.8%      |
| Marketplace | 48      | 15.4%      |

## Geographic Distribution

| Region | Tickets |
|--------|---------|
| Metro  | 98      |
| North  | 71      |
| East   | 58      |
| West   | 51      |
| South  | 34      |

## Customer Support Action

- Engineering lead tagged as P0 at 13:35 UTC
- Template response sent: "We are aware of checkout issues and engineers are working urgently on a fix."
- 47 customers offered ₹200 voucher for compensation

## Resolution

Checkout errors resolved at ~15:30 UTC following payment-service rollback to v2.4.0.
