# Incident Report: INC-91024 - Unintended Sitewide Pricing Discount

- **Date / Time**: `2026-08-26 14:00:00 UTC`
- **Severity**: SEV-1 (Revenue Margin Drop)
- **Impacted Systems**: `pricing-engine`, `cart-service`, `promotions-api`
- **Summary**:
  - Global sitewide promotional rule applied an unintended 30% discount to all completed cart checkouts.
  - Average Order Value (AOV) plummeted from ₹1,000 to ₹700 (-30%).
  - Total order volume and visitor sessions remained stable at normal capacity (5,000 orders / 100,000 sessions).
- **Immediate Action**: Ops paged; disabling the invalid promotion rule on `promotions-api`.
