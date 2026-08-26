"""NarrateBI Database Seeder

Initializes SQLite database and populates baseline and scenario data.
Can be executed safely multiple times.
"""

import os
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
    """Seeds baseline and initial scenario datasets."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 1. Seed KPI Values (Default / Multi-factor scenario)
        kpi_records = [
            # scenario_id, kpi_key, current_value, baseline_value, change_pct, unit, history_days
            ("scenario_1_multifactor", "revenue", 4420000.0, 5000000.0, -11.6, "INR", 30),
            ("scenario_1_multifactor", "orders", 4210.0, 5000.0, -15.8, "Count", 30),
            ("scenario_1_multifactor", "conversion_rate", 4.21, 5.0, -15.8, "%", 30),
            ("scenario_1_multifactor", "sessions", 100000.0, 100000.0, 0.0, "Count", 30),
            ("scenario_1_multifactor", "aov", 1050.0, 1000.0, 5.0, "INR", 30),

            # Low confidence scenario (missing deployment evidence)
            ("scenario_2_low_confidence", "revenue", 4400000.0, 5000000.0, -12.0, "INR", 30),
            ("scenario_2_low_confidence", "orders", 4400.0, 5000.0, -12.0, "Count", 30),
            ("scenario_2_low_confidence", "conversion_rate", 4.4, 5.0, -12.0, "%", 30),
            ("scenario_2_low_confidence", "sessions", 100000.0, 100000.0, 0.0, "Count", 30),
            ("scenario_2_low_confidence", "aov", 1000.0, 1000.0, 0.0, "INR", 30),

            # New KPI / Cold start scenario (history_days = 4)
            ("scenario_3_new_kpi", "new_product_conversion", 2.1, 3.5, -40.0, "%", 4),
            ("scenario_3_new_kpi", "revenue", 4950000.0, 5000000.0, -1.0, "INR", 30),
        ]

        cursor.executemany(
            """
            INSERT INTO kpi_values 
            (scenario_id, kpi_key, current_value, baseline_value, change_pct, unit, history_days)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            kpi_records,
        )

        # 2. Seed Deployment Events (Scenario 1)
        deployments = [
            ("scenario_1_multifactor", "2026-08-26 14:00:00", "payment-service", "v2.4.1", "completed", "devops-team"),
        ]
        cursor.executemany(
            """
            INSERT INTO deployment_events (scenario_id, timestamp, service, version, status, deployed_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            deployments,
        )

        # 3. Seed System Logs (Scenario 1)
        logs = [
            ("scenario_1_multifactor", "2026-08-26 14:15:00", "payment-service", "ERROR", "Gateway timeout: HTTP 504 on /v2/charge endpoint"),
            ("scenario_1_multifactor", "2026-08-26 14:16:00", "payment-service", "ERROR", "Connection pool exhausted (max 50)"),
            ("scenario_1_multifactor", "2026-08-26 14:20:00", "checkout-web", "WARN", "User session checkout aborted: payment unhandled error"),
        ]
        cursor.executemany(
            """
            INSERT INTO system_logs (scenario_id, timestamp, service, log_level, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            logs,
        )

        # 4. Seed Payment Data (Scenario 1)
        payment_records = [
            ("scenario_1_multifactor", "2026-08-26 14:00:00", 25000, 1250, 5.0, 1250, 20, 15),
            ("scenario_1_multifactor", "2026-08-26 15:00:00", 25000, 850, 3.4, 850, 240, 380),
        ]
        cursor.executemany(
            """
            INSERT INTO payment_data 
            (scenario_id, timestamp, sessions, orders, conversion_rate, payment_success, payment_failures, checkout_errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payment_records,
        )

        conn.commit()
    print("Baseline seed data inserted successfully.")


def main():
    init_db()
    seed_baseline_data()
    print("Database preparation complete.")


if __name__ == "__main__":
    main()
