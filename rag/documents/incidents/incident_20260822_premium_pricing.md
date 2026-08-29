# Incident Report: INC-20260822 — Premium Pricing Rule Push Reduces Conversion

- **Date / Time**: `2026-08-22 09:00:00 UTC`
- **Severity**: SEV-2 (Commercial Revenue Risk)
- **Impacted Systems**: `pricing-engine`, `promotions-api`, `cart-service`
- **Products Affected**: Electronics, Apparel
- **Segments Affected**: New, Returning (non-Premium)
- **Event Type**: pricing_change
- **Status**: Monitoring (not rolled back — intentional business decision)

## Summary

On 2026-08-22 the pricing team deployed pricing-engine v3.1.0 and promotions-api v2.8.0 implementing a "Premium Margin Recapture" initiative. The change:

1. Increased list prices for Electronics (+18%) and Apparel (+12%) to recover margin lost during Q2 clearance sales.
2. Suppressed discount codes for New and Returning customer segments (discounts now restricted to Premium and Enterprise).

## Impact

- Average Order Value (AOV) increased from ~₹1,590 baseline → ~₹1,940 in analysis window (+22%)
- Conversion Rate declined from ~3.94% baseline → ~2.84% in analysis window (-28%)
- Sessions remained stable (traffic unchanged, -0.2%)
- Net Revenue: -12% despite higher per-order value (volume loss overpowered AOV gain)
- Marketing team reported improved ROAS (+35%) due to higher AOV on attributed conversions

## Contradiction Note

Marketing dashboards reported strong campaign performance with ROAS above 2.0 across all channels. However the revenue ledger showed an -12% decline over the same period. This apparent contradiction arises because:

- ROAS is computed on attributed conversions (customers who did buy)
- Revenue decline is driven by the volume of customers who did NOT buy (abandoned cart due to higher prices)
- The two metrics measure different sub-populations and are not directly comparable

## Business Context

The pricing team views this as an acceptable short-term trade-off with a planned 4-week re-assessment. The commercial analytics team is tracking funnel abandonment weekly.
