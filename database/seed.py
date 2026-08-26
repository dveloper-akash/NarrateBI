"""NarrateBI Database Seeder

Initializes SQLite database and populates baseline and scenario data.
Can be executed safely multiple times.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent / "narratebi.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db():
    """Initializes the database schema from schema.sql."""
    print(f"Initializing database at: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    print("Schema initialized successfully.")


def seed_baseline_data():
    """Seeds baseline and comprehensive test scenario datasets."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # -------------------------------------------------------------
        # 1. KPI VALUES (All 5 Scenarios)
        # -------------------------------------------------------------
        # Columns: (scenario_id, kpi_key, current_value, baseline_value, change_pct, unit, history_days)
        kpi_records = [
            # SCENARIO 1: AOV Drop Test (Orders = 5,000, AOV = ₹700, Rev = ₹35L)
            # Sessions = 100,000 (0%), CR = 5.0% (0%), Orders = 5,000 (0%), AOV = ₹700 (-30.0%), Revenue = ₹35.0L (-30.0%)
            ("scenario_1_multifactor", "revenue", 3500000.0, 5000000.0, -30.00, "INR", 30),
            ("scenario_1_multifactor", "orders", 5000.0, 5000.0, 0.00, "Count", 30),
            ("scenario_1_multifactor", "conversion_rate", 5.00, 5.0, 0.00, "%", 30),
            ("scenario_1_multifactor", "sessions", 100000.0, 100000.0, 0.00, "Count", 30),
            ("scenario_1_multifactor", "aov", 700.0, 1000.0, -30.00, "INR", 30),

            # SCENARIO 2: Low confidence / Missing operational evidence
            # Revenue = ₹44.0L (-12.0%), Orders = 4,400 (-12.0%), CR = 4.4% (-12.0%), Sessions = 100k, AOV = ₹1,000
            ("scenario_2_low_confidence", "revenue", 4400000.0, 5000000.0, -12.00, "INR", 30),
            ("scenario_2_low_confidence", "orders", 4400.0, 5000.0, -12.00, "Count", 30),
            ("scenario_2_low_confidence", "conversion_rate", 4.40, 5.0, -12.00, "%", 30),
            ("scenario_2_low_confidence", "sessions", 100000.0, 100000.0, 0.00, "Count", 30),
            ("scenario_2_low_confidence", "aov", 1000.0, 1000.0, 0.00, "INR", 30),

            # SCENARIO 3: Cold Start / New KPI (< 14 days history)
            ("scenario_3_new_kpi", "new_product_conversion", 2.10, 3.50, -40.00, "%", 4),
            ("scenario_3_new_kpi", "revenue", 4950000.0, 5000000.0, -1.00, "INR", 30),
            ("scenario_3_new_kpi", "orders", 4950.0, 5000.0, -1.00, "Count", 30),
            ("scenario_3_new_kpi", "conversion_rate", 4.95, 5.00, -1.00, "%", 30),
            ("scenario_3_new_kpi", "sessions", 100000.0, 100000.0, 0.00, "Count", 30),
            ("scenario_3_new_kpi", "aov", 1000.0, 1000.0, 0.00, "INR", 30),

            # SCENARIO 4: Role-Based Access (RBAC) Demonstration
            ("scenario_4_rbac", "revenue", 4420500.0, 5000000.0, -11.59, "INR", 30),
            ("scenario_4_rbac", "orders", 4210.0, 5000.0, -15.80, "Count", 30),
            ("scenario_4_rbac", "conversion_rate", 4.21, 5.0, -15.80, "%", 30),
            ("scenario_4_rbac", "sessions", 100000.0, 100000.0, 0.00, "Count", 30),
            ("scenario_4_rbac", "aov", 1050.0, 1000.0, 5.00, "INR", 30),

            # SCENARIO 5: Contradictory Evidence (Traffic down -25%, but AOV up +30%)
            # Revenue = ₹48.75L (-2.5%), Orders = 3,750 (-25.0%), Sessions = 75,000 (-25.0%), CR = 5.0% (0.0%), AOV = ₹1,300 (+30.0%)
            ("scenario_5_contradiction", "revenue", 4875000.0, 5000000.0, -2.50, "INR", 30),
            ("scenario_5_contradiction", "orders", 3750.0, 5000.0, -25.00, "Count", 30),
            ("scenario_5_contradiction", "conversion_rate", 5.00, 5.00, 0.00, "%", 30),
            ("scenario_5_contradiction", "sessions", 75000.0, 100000.0, -25.00, "Count", 30),
            ("scenario_5_contradiction", "aov", 1300.0, 1000.0, 30.00, "INR", 30),
        ]

        cursor.executemany(
            """
            INSERT INTO kpi_values 
            (scenario_id, kpi_key, current_value, baseline_value, change_pct, unit, history_days)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            kpi_records,
        )

        # -------------------------------------------------------------
        # 2. SOURCE 1: ERP / SALES DATA (Hourly granularity)
        # -------------------------------------------------------------
        base_time = datetime(2026, 8, 26, 12, 0, 0)
        sales_records = []
        for i in range(6):
            t = (base_time + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
            # Baseline hours
            if i < 2:
                orders, aov = 833, 1000.0
            else:
                # Post 14:00 drop
                orders, aov = 701, 1050.0
            rev = orders * aov
            sales_records.append(("scenario_1_multifactor", t, orders, rev, aov, rev * 0.6))
            sales_records.append(("scenario_4_rbac", t, orders, rev, aov, rev * 0.6))

        cursor.executemany(
            """
            INSERT INTO sales_data (scenario_id, timestamp, orders, revenue, aov, cogs)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            sales_records,
        )

        # -------------------------------------------------------------
        # 3. SOURCE 2: PAYMENT & WEB DATA
        # -------------------------------------------------------------
        payment_records = [
            ("scenario_1_multifactor", "2026-08-26 13:00:00", 25000, 1250, 5.0, 1250, 15, 10),
            ("scenario_1_multifactor", "2026-08-26 14:00:00", 25000, 1250, 5.0, 1240, 20, 15),
            ("scenario_1_multifactor", "2026-08-26 15:00:00", 25000, 850, 3.4, 850, 240, 380),
            ("scenario_1_multifactor", "2026-08-26 16:00:00", 25000, 860, 3.44, 860, 235, 375),
            # Scenario 4 (RBAC)
            ("scenario_4_rbac", "2026-08-26 14:00:00", 25000, 1250, 5.0, 1240, 20, 15),
            ("scenario_4_rbac", "2026-08-26 15:00:00", 25000, 850, 3.4, 850, 240, 380),
        ]
        cursor.executemany(
            """
            INSERT INTO payment_data 
            (scenario_id, timestamp, sessions, orders, conversion_rate, payment_success, payment_failures, checkout_errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payment_records,
        )

        # -------------------------------------------------------------
        # 4. SOURCE 3: DEPLOYMENT EVENTS
        # -------------------------------------------------------------
        deployments = [
            ("scenario_1_multifactor", "2026-08-26 14:00:00", "payment-service", "v2.4.1", "completed", "release-bot"),
            ("scenario_4_rbac", "2026-08-26 14:00:00", "payment-service", "v2.4.1", "completed", "release-bot"),
            ("scenario_5_contradiction", "2026-08-26 10:00:00", "marketing-attribution", "v1.8.0", "completed", "mktg-ops"),
        ]
        cursor.executemany(
            """
            INSERT INTO deployment_events (scenario_id, timestamp, service, version, status, deployed_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            deployments,
        )

        # -------------------------------------------------------------
        # 5. SOURCE 3: SYSTEM LOGS
        # -------------------------------------------------------------
        logs = [
            ("scenario_1_multifactor", "2026-08-26 14:15:00", "payment-service", "ERROR", "Gateway timeout: HTTP 504 on /v2/charge endpoint"),
            ("scenario_1_multifactor", "2026-08-26 14:16:00", "payment-service", "ERROR", "Connection pool exhausted (active: 50, queued: 120)"),
            ("scenario_1_multifactor", "2026-08-26 14:20:00", "checkout-web", "WARN", "User session checkout aborted: payment unhandled error"),
            ("scenario_4_rbac", "2026-08-26 14:15:00", "payment-service", "ERROR", "Gateway timeout: HTTP 504 on /v2/charge endpoint"),
        ]
        cursor.executemany(
            """
            INSERT INTO system_logs (scenario_id, timestamp, service, log_level, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            logs,
        )

        conn.commit()
    print("Baseline and scenario seed data inserted successfully.")


def main():
    init_db()
    seed_baseline_data()
    print("Database preparation complete.")


if __name__ == "__main__":
    main()
