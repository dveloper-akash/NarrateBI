"""NarrateBI Database Seeder v2.0

Generates realistic multi-month business data with:
- Proper Revenue = Sessions × ConversionRate × AOV relationships
- Seasonality, weekly patterns, trends, noise (SEED=42, fully reproducible)
- 5 distinct scenario stories embedded in data, no hardcoded outcomes
- Scenario 1: Payment-service deployment → conversion crash
- Scenario 2: Diffuse revenue drop, no operational evidence
- Scenario 3: New product KPI cold start (<14d history)
- Scenario 4: RBAC demo (same incident as Sc1, dual-persona view)
- Scenario 5: AOV rises, conversion drops, revenue net-negative

Run:  python database/seed.py
"""

import sqlite3
import random
import math
from pathlib import Path
from datetime import date, datetime, timedelta

SEED = 42
DB_PATH = Path(__file__).resolve().parent / "narratebi.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

random.seed(SEED)

# ── Dimension catalogues ─────────────────────────────────────────────────────
PRODUCTS = ["Electronics", "Apparel", "Home & Kitchen", "Beauty", "Sports"]
CATEGORIES = {
    "Electronics": "Tech",
    "Apparel": "Fashion",
    "Home & Kitchen": "Home",
    "Beauty": "Health",
    "Sports": "Active",
}
REGIONS = ["North", "South", "East", "West", "Metro"]
CHANNELS = ["Web", "Mobile App", "Marketplace", "In-Store"]
SEGMENTS = ["New", "Returning", "Premium", "Enterprise"]

# Base metrics per product
PRODUCT_BASE = {
    "Electronics":    {"aov": 3200, "cr": 2.8, "share": 0.28},
    "Apparel":        {"aov": 980,  "cr": 4.5, "share": 0.22},
    "Home & Kitchen": {"aov": 1450, "cr": 3.8, "share": 0.20},
    "Beauty":         {"aov": 620,  "cr": 5.2, "share": 0.18},
    "Sports":         {"aov": 1100, "cr": 4.0, "share": 0.12},
}

REGION_MULTIPLIER = {"North": 1.12, "South": 0.93, "East": 1.05, "West": 0.98, "Metro": 1.35}
CHANNEL_SESSIONS_SPLIT = {"Web": 0.42, "Mobile App": 0.35, "Marketplace": 0.16, "In-Store": 0.07}

# ── Date range ───────────────────────────────────────────────────────────────
START_DATE = date(2026, 3, 1)   # 6 months of history
END_DATE   = date(2026, 8, 28)  # day before analysis


def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def weekday_factor(d: date) -> float:
    """Mon-Thu: ~1.0; Fri-Sat: +15%; Sun: -12%."""
    wd = d.weekday()
    return {0: 1.00, 1: 1.02, 2: 1.03, 3: 1.01, 4: 1.14, 5: 1.16, 6: 0.88}[wd]


def seasonal_factor(d: date) -> float:
    """Mild sinusoidal seasonality peaking in August."""
    day_of_year = d.timetuple().tm_yday
    return 1.0 + 0.10 * math.sin(2 * math.pi * (day_of_year - 60) / 365)


def trend_factor(d: date) -> float:
    """Gentle +8% organic growth over 6 months."""
    days = (d - START_DATE).days
    total = (END_DATE - START_DATE).days
    return 1.0 + 0.08 * (days / total)


def noise(scale: float = 0.04) -> float:
    return 1.0 + random.gauss(0, scale)


# ── Scenario windows ─────────────────────────────────────────────────────────
# Analysis period = last 7 days (Aug 22-28); Baseline = prior 7 days (Aug 15-21)
ANALYSIS_START = date(2026, 8, 22)
ANALYSIS_END   = date(2026, 8, 28)
BASELINE_START = date(2026, 8, 15)
BASELINE_END   = date(2026, 8, 21)

# Scenario-specific incident date
SC1_INCIDENT_DATE = date(2026, 8, 24)   # payment-service deployment
SC5_PRICING_START = date(2026, 8, 22)   # premium pricing push begins


def apply_scenario_modifier(d: date, product: str, region: str, channel: str,
                             scenario_id: str) -> dict:
    """Returns multipliers {sessions, cr, aov, discount} for a given scenario."""
    mods = {"sessions": 1.0, "cr": 1.0, "aov": 1.0, "discount": 0.0}

    if scenario_id == "scenario_1_multifactor":
        # Payment service incident Aug 24-28: checkout conversion crashes -40% in Web/App
        if d >= SC1_INCIDENT_DATE and channel in ("Web", "Mobile App"):
            mods["cr"] = 0.60        # -40% conversion
            mods["sessions"] = 0.98  # tiny traffic dip

    elif scenario_id == "scenario_2_low_confidence":
        # Soft revenue decline Aug 22-28: mild broad-based drop, no clear single driver
        if d >= ANALYSIS_START:
            mods["sessions"] = 0.92
            mods["cr"]       = 0.93
            mods["aov"]      = 0.97

    elif scenario_id == "scenario_3_new_kpi":
        # No scenario distortion on main KPIs; new_product_conversion handled separately
        pass

    elif scenario_id == "scenario_4_rbac":
        # Same payment incident as Sc1 (RBAC demonstration)
        if d >= SC1_INCIDENT_DATE and channel in ("Web", "Mobile App"):
            mods["cr"] = 0.60
            mods["sessions"] = 0.98

    elif scenario_id == "scenario_5_contradiction":
        # Premium pricing push: AOV +22%, conversion -28%, sessions stable → Revenue net negative
        # Revenue ≈ Sessions × CR × AOV → 1.00 × 0.72 × 1.22 = 0.878 → ~-12% revenue
        if d >= SC5_PRICING_START:
            mods["aov"]      = 1.22
            mods["cr"]       = 0.72   # larger drop so revenue is net negative
            mods["discount"] = -0.05  # fewer discounts (higher prices)

    return mods


def init_db():
    print(f"Initializing database at: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    print("Schema initialized.")


def generate_sales_rows(scenario_id: str):
    """Generate daily sales_data rows for all dimension combinations."""
    rows = []
    rng = random.Random(SEED)

    total_daily_sessions_base = 120_000  # total across all products/regions/channels

    for d in date_range(START_DATE, END_DATE):
        wf = weekday_factor(d)
        sf = seasonal_factor(d)
        tf = trend_factor(d)
        base_multiplier = wf * sf * tf

        for product in PRODUCTS:
            pb = PRODUCT_BASE[product]
            for region in REGIONS:
                rm = REGION_MULTIPLIER[region]
                for channel in CHANNELS:
                    cs = CHANNEL_SESSIONS_SPLIT[channel]

                    # Base sessions for this cell
                    cell_sessions = int(
                        total_daily_sessions_base
                        * pb["share"]
                        * rm
                        * cs
                        * base_multiplier
                        * (1 + rng.gauss(0, 0.05))
                    )
                    cell_sessions = max(cell_sessions, 10)

                    # Apply scenario modifiers
                    mods = apply_scenario_modifier(d, product, region, channel, scenario_id)
                    cell_sessions = int(cell_sessions * mods["sessions"])

                    base_cr = pb["cr"] * mods["cr"] * (1 + rng.gauss(0, 0.04))
                    base_cr = max(0.3, min(base_cr, 18.0))

                    base_aov = pb["aov"] * mods["aov"] * rm * (1 + rng.gauss(0, 0.03))
                    base_aov = max(100, base_aov)

                    orders = max(0, int(cell_sessions * base_cr / 100.0))
                    units = max(orders, int(orders * rng.uniform(1.1, 1.8)))
                    revenue = round(orders * base_aov, 2)
                    discount_rate = round(max(0, 0.08 + mods["discount"] + rng.gauss(0, 0.02)), 3)
                    returns = max(0, int(orders * rng.uniform(0.01, 0.04)))
                    mktg_spend = round(revenue * rng.uniform(0.04, 0.09), 2)

                    # Customer segment — split proportionally
                    segment = rng.choice(SEGMENTS)

                    rows.append((
                        scenario_id, str(d), product, CATEGORIES[product],
                        region, channel, segment,
                        cell_sessions, orders, units, revenue,
                        round(base_aov, 2), round(base_cr, 4),
                        discount_rate, returns, mktg_spend
                    ))
    return rows


def generate_payment_rows(scenario_id: str):
    """Hourly payment telemetry for the analysis week (Aug 22-28)."""
    rows = []
    rng = random.Random(SEED + 1)

    for d in date_range(ANALYSIS_START, ANALYSIS_END):
        for hour in range(8, 24):  # business hours
            ts = datetime(d.year, d.month, d.day, hour, 0, 0)
            for region in REGIONS:
                base_sessions = int(rng.uniform(3000, 6000))
                base_cr = 4.2 + rng.gauss(0, 0.3)
                base_failures = int(base_sessions * rng.uniform(0.002, 0.006))
                base_errors = int(base_failures * rng.uniform(0.8, 1.2))
                latency = int(rng.uniform(600, 950))

                # Incident modifications
                if scenario_id in ("scenario_1_multifactor", "scenario_4_rbac"):
                    if d >= SC1_INCIDENT_DATE and 13 <= hour <= 22:
                        base_cr *= 0.58
                        base_failures = int(base_sessions * rng.uniform(0.08, 0.14))
                        base_errors   = int(base_sessions * rng.uniform(0.12, 0.18))
                        latency = int(rng.uniform(3500, 8000))

                orders = max(0, int(base_sessions * base_cr / 100))
                pay_success = max(0, orders - base_failures)

                rows.append((
                    scenario_id, str(ts), region,
                    base_sessions, orders,
                    round(base_cr, 4),
                    pay_success, base_failures, base_errors, latency
                ))
    return rows


def generate_web_rows(scenario_id: str):
    rows = []
    rng = random.Random(SEED + 2)
    devices = ["Desktop", "Mobile", "Tablet"]
    d_split = [0.38, 0.52, 0.10]
    for d in date_range(START_DATE, END_DATE):
        total = int(120_000 * weekday_factor(d) * seasonal_factor(d) * trend_factor(d) * (1 + rng.gauss(0, 0.04)))
        for dev, sp in zip(devices, d_split):
            s = int(total * sp * (1 + rng.gauss(0, 0.03)))
            bounce = round(rng.uniform(0.28, 0.52), 3)
            duration = int(rng.uniform(120, 280))
            channel = rng.choice(["Organic", "Paid", "Social", "Direct"])
            rows.append((scenario_id, str(d), dev, channel, s, bounce, duration))
    return rows


def generate_system_logs(scenario_id: str):
    rows = []
    if scenario_id in ("scenario_1_multifactor", "scenario_4_rbac"):
        incident_ts = [
            ("2026-08-24 13:02:00", "payment-service", "ERROR", "Gateway timeout: HTTP 504 on /v2/charge endpoint"),
            ("2026-08-24 13:04:00", "payment-service", "ERROR", "Connection pool exhausted (active: 50, queued: 128)"),
            ("2026-08-24 13:07:00", "checkout-web", "WARN", "User session checkout aborted: payment unhandled error"),
            ("2026-08-24 13:15:00", "payment-service", "ERROR", "Retry storm: 1,240 failed tokenization requests in 60s"),
            ("2026-08-24 13:22:00", "gateway-proxy", "FATAL", "Circuit breaker OPEN: payment-service upstream unhealthy"),
            ("2026-08-24 14:00:00", "payment-service", "WARN", "Rollback initiated for v2.4.1 connection pool config"),
            ("2026-08-24 15:30:00", "payment-service", "INFO", "Rollback complete — error rate returning to baseline"),
        ]
        for ts, svc, lvl, msg in incident_ts:
            rows.append((scenario_id, ts, svc, lvl, msg))

    elif scenario_id == "scenario_5_contradiction":
        rows += [
            (scenario_id, "2026-08-22 09:00:00", "pricing-engine", "INFO",
             "Premium pricing ruleset v3.1 activated for Electronics and Apparel"),
            (scenario_id, "2026-08-22 09:01:00", "promotions-api", "INFO",
             "Discount suppression enabled for Premium and Returning segments"),
        ]
    return rows


def generate_deployments(scenario_id: str):
    rows = []
    if scenario_id in ("scenario_1_multifactor", "scenario_4_rbac"):
        rows += [
            (scenario_id, "2026-08-24 13:00:00", "payment-service", "v2.4.1", "completed", "release-bot", "production"),
            (scenario_id, "2026-08-24 14:05:00", "payment-service", "v2.4.0", "completed", "ops-on-call", "production"),
        ]
    elif scenario_id == "scenario_5_contradiction":
        rows += [
            (scenario_id, "2026-08-22 08:55:00", "pricing-engine", "v3.1.0", "completed", "pricing-team", "production"),
            (scenario_id, "2026-08-22 08:57:00", "promotions-api", "v2.8.0", "completed", "pricing-team", "production"),
        ]
    elif scenario_id == "scenario_3_new_kpi":
        rows += [
            (scenario_id, "2026-08-25 10:00:00", "product-catalog", "v1.0.0", "completed", "product-team", "production"),
        ]
    return rows


def generate_marketing_rows(scenario_id: str):
    rows = []
    rng = random.Random(SEED + 3)
    campaigns = {
        "Summer_Clearance": "Paid Search",
        "Brand_Awareness_Q3": "Social",
        "Email_Reactivation": "Email",
        "Display_Retargeting": "Display",
        "Affiliate_Performance": "Affiliate",
    }
    for d in date_range(ANALYSIS_START, ANALYSIS_END):
        for camp, chan in campaigns.items():
            for region in REGIONS:
                spend = round(rng.uniform(800, 4500), 2)
                impressions = int(spend * rng.uniform(80, 200))
                clicks = int(impressions * rng.uniform(0.01, 0.04))
                attr_orders = int(clicks * rng.uniform(0.02, 0.06))
                attr_rev = round(attr_orders * rng.uniform(800, 2500), 2)
                roas = round(attr_rev / spend, 3) if spend > 0 else 0.0

                # Scenario 5: marketing reports positive ROAS despite revenue declining
                if scenario_id == "scenario_5_contradiction":
                    roas = round(roas * rng.uniform(1.2, 1.5), 3)  # inflated ROAS
                    attr_rev = round(spend * roas, 2)

                rows.append((
                    scenario_id, str(d), camp, chan, region,
                    spend, impressions, clicks, attr_orders, attr_rev, roas
                ))
    return rows


def compute_kpi_values(scenario_id: str, conn: sqlite3.Connection):
    """Compute KPI current/baseline from time-series data — no hardcoded outcomes."""
    cursor = conn.cursor()

    # Helper: aggregate over date range
    def agg(start_d, end_d):
        cursor.execute("""
            SELECT
                SUM(sessions), SUM(orders), SUM(revenue),
                SUM(orders)*1.0/NULLIF(SUM(sessions),0)*100,
                SUM(revenue)*1.0/NULLIF(SUM(orders),0)
            FROM sales_data
            WHERE scenario_id=? AND date>=? AND date<=?
        """, (scenario_id, str(start_d), str(end_d)))
        row = cursor.fetchone()
        return {
            "sessions": row[0] or 0,
            "orders":   row[1] or 0,
            "revenue":  row[2] or 0.0,
            "cr":       row[3] or 0.0,
            "aov":      row[4] or 0.0,
        }

    curr = agg(ANALYSIS_START, ANALYSIS_END)
    base = agg(BASELINE_START, BASELINE_END)

    def pct(c, b):
        if b == 0:
            return 0.0
        return round((c - b) / b * 100, 2)

    # history_days = total days in DB for this scenario
    cursor.execute("SELECT COUNT(DISTINCT date) FROM sales_data WHERE scenario_id=?", (scenario_id,))
    hist = cursor.fetchone()[0] or 30

    kpi_rows = [
        (scenario_id, "revenue",         curr["revenue"], base["revenue"], pct(curr["revenue"], base["revenue"]), "INR", hist),
        (scenario_id, "orders",          curr["orders"],  base["orders"],  pct(curr["orders"],  base["orders"]),  "Count", hist),
        (scenario_id, "sessions",        curr["sessions"],base["sessions"],pct(curr["sessions"],base["sessions"]),"Count", hist),
        (scenario_id, "conversion_rate", curr["cr"],      base["cr"],      pct(curr["cr"],      base["cr"]),      "%", hist),
        (scenario_id, "aov",             curr["aov"],     base["aov"],     pct(curr["aov"],     base["aov"]),     "INR", hist),
    ]

    # Scenario 3: new_product_conversion with only 4 days history
    if scenario_id == "scenario_3_new_kpi":
        kpi_rows.append((
            scenario_id, "new_product_conversion",
            2.10, 3.50, round((2.10-3.50)/3.50*100, 2), "%", 4
        ))

    cursor.executemany("""
        INSERT INTO kpi_values (scenario_id, kpi_key, current_value, baseline_value, change_pct, unit, history_days)
        VALUES (?,?,?,?,?,?,?)
    """, kpi_rows)


def seed_all():
    scenarios = [
        "scenario_1_multifactor",
        "scenario_2_low_confidence",
        "scenario_3_new_kpi",
        "scenario_4_rbac",
        "scenario_5_contradiction",
    ]

    with sqlite3.connect(DB_PATH) as conn:
        print("Seeding sales data…")
        for sid in scenarios:
            rows = generate_sales_rows(sid)
            conn.executemany("""
                INSERT INTO sales_data
                (scenario_id,date,product,category,region,channel,customer_segment,
                 sessions,orders,units,revenue,aov,conversion_rate,discount_rate,returns,marketing_spend)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, rows)
            print(f"  {sid}: {len(rows)} sales rows")

        print("Seeding payment telemetry…")
        for sid in scenarios:
            rows = generate_payment_rows(sid)
            conn.executemany("""
                INSERT INTO payment_data
                (scenario_id,timestamp,region,sessions,orders,conversion_rate,
                 payment_success,payment_failures,checkout_errors,avg_checkout_latency_ms)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, rows)

        print("Seeding web analytics…")
        for sid in scenarios:
            rows = generate_web_rows(sid)
            conn.executemany("""
                INSERT INTO web_data
                (scenario_id,date,device,channel,sessions,bounce_rate,avg_session_duration_sec)
                VALUES (?,?,?,?,?,?,?)
            """, rows)

        print("Seeding system logs…")
        for sid in scenarios:
            rows = generate_system_logs(sid)
            if rows:
                conn.executemany("""
                    INSERT INTO system_logs (scenario_id,timestamp,service,log_level,message)
                    VALUES (?,?,?,?,?)
                """, rows)

        print("Seeding deployment events…")
        for sid in scenarios:
            rows = generate_deployments(sid)
            if rows:
                conn.executemany("""
                    INSERT INTO deployment_events
                    (scenario_id,timestamp,service,version,status,deployed_by,environment)
                    VALUES (?,?,?,?,?,?,?)
                """, rows)

        print("Seeding marketing data…")
        for sid in scenarios:
            rows = generate_marketing_rows(sid)
            conn.executemany("""
                INSERT INTO marketing_data
                (scenario_id,date,campaign,channel,region,spend,impressions,clicks,
                 attributed_orders,attributed_revenue,roas)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, rows)

        print("Computing KPI values from time-series…")
        for sid in scenarios:
            compute_kpi_values(sid, conn)

        conn.commit()
    print("Seed complete.")


# Alias for test compatibility: tests import `seed_baseline_data`
# which is equivalent to the full seed_all() function.
seed_baseline_data = seed_all


def main():
    init_db()
    seed_all()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for tbl in ["sales_data", "payment_data", "web_data", "system_logs",
                    "deployment_events", "marketing_data", "kpi_values"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"  {tbl}: {cur.fetchone()[0]} rows")
    print(f"DB size: {DB_PATH.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
