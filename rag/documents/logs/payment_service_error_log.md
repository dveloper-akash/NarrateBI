# Operational Log Extract: payment-service

```
2026-08-26 14:14:58 [INFO] payment-service: Healthcheck OK (v2.4.1)
2026-08-26 14:15:02 [ERROR] payment-service: Gateway timeout HTTP 504 on POST /v2/charges
2026-08-26 14:15:10 [ERROR] payment-service: Connection pool exhausted (active: 50, queued: 120)
2026-08-26 14:15:22 [WARN] checkout-router: Circuit breaker tripped for provider-primary
2026-08-26 14:16:00 [ERROR] payment-service: Transaction failed: id=txn_98242 code=TIMEOUT_ERR
```
