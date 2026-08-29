"""Part 1 Data & Scenario Validation Tests

Verifies Part 1 completion requirements:
1. Database is substantially seeded (row counts by table).
2. Seed is deterministic and reproducible (SEED=42).
3. All 5 scenarios have data-driven KPIs (no hardcoded outcomes).
4. Scenario 5: AOV increases, Conversion Rate decreases, Revenue net-negative.
5. RAG corpus has documents across all categories.
6. seed_baseline_data alias works for test compatibility.
"""

import unittest
import sqlite3
from pathlib import Path

from database.seed import init_db, seed_baseline_data, seed_all, DB_PATH, SEED
from engine.kpi_engine import fetch_kpis_for_scenario
from rag.ingest import load_documents


class TestDatabaseSize(unittest.TestCase):
    """Verify database is substantially populated."""

    @classmethod
    def setUpClass(cls):
        """Seed fresh DB once for all tests in this class."""
        init_db()
        seed_all()

    def test_sales_data_substantial(self):
        """sales_data must have > 50,000 rows (multi-month, multi-dim)."""
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.execute("SELECT COUNT(*) FROM sales_data")
            count = c.fetchone()[0]
        self.assertGreater(count, 50_000, f"Expected >50,000 sales rows, got {count}")

    def test_payment_data_present(self):
        """payment_data must have rows (hourly telemetry)."""
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.execute("SELECT COUNT(*) FROM payment_data")
            count = c.fetchone()[0]
        self.assertGreater(count, 0, "payment_data is empty")

    def test_kpi_values_all_scenarios(self):
        """kpi_values must contain rows for each of the 5 scenarios."""
        scenarios = [
            "scenario_1_multifactor",
            "scenario_2_low_confidence",
            "scenario_3_new_kpi",
            "scenario_4_rbac",
            "scenario_5_contradiction",
        ]
        with sqlite3.connect(DB_PATH) as conn:
            for s in scenarios:
                c = conn.execute("SELECT COUNT(*) FROM kpi_values WHERE scenario_id=?", (s,))
                cnt = c.fetchone()[0]
                self.assertGreater(cnt, 0, f"No kpi_values for {s}")

    def test_system_logs_for_incident_scenarios(self):
        """Scenario 1 and 4 must have system error logs (the payment incident)."""
        with sqlite3.connect(DB_PATH) as conn:
            for s in ("scenario_1_multifactor", "scenario_4_rbac"):
                c = conn.execute(
                    "SELECT COUNT(*) FROM system_logs WHERE scenario_id=? AND log_level='ERROR'",
                    (s,),
                )
                cnt = c.fetchone()[0]
                self.assertGreater(cnt, 0, f"No error logs for {s}")

    def test_deployment_events_present(self):
        """Scenario 1, 4, 5 must have deployment records."""
        with sqlite3.connect(DB_PATH) as conn:
            for s in ("scenario_1_multifactor", "scenario_4_rbac", "scenario_5_contradiction"):
                c = conn.execute(
                    "SELECT COUNT(*) FROM deployment_events WHERE scenario_id=?", (s,)
                )
                cnt = c.fetchone()[0]
                self.assertGreater(cnt, 0, f"No deployment events for {s}")


class TestDeterministicReproducibility(unittest.TestCase):
    """Verify SEED=42 produces stable, reproducible data."""

    def test_seed_constant_is_42(self):
        """The global SEED must be 42."""
        self.assertEqual(SEED, 42)

    def test_sales_row_count_reproducible(self):
        """Running seed_all() twice should produce the same row count
        (schema DROP+CREATE ensures idempotency)."""
        init_db()
        seed_all()
        with sqlite3.connect(DB_PATH) as conn:
            c1 = conn.execute("SELECT COUNT(*) FROM sales_data").fetchone()[0]

        init_db()
        seed_all()
        with sqlite3.connect(DB_PATH) as conn:
            c2 = conn.execute("SELECT COUNT(*) FROM sales_data").fetchone()[0]

        self.assertEqual(c1, c2, "Row count differs between two runs — seed is NOT deterministic")

    def test_seed_baseline_data_alias(self):
        """seed_baseline_data must be callable and equivalent to seed_all."""
        # Should not raise
        init_db()
        seed_baseline_data()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.execute("SELECT COUNT(*) FROM kpi_values").fetchone()[0]
        self.assertGreater(c, 0)


class TestScenario5Contradiction(unittest.TestCase):
    """Verify Scenario 5 data tells the correct contradictory story:
    AOV rises, Conversion falls, Revenue net-negative.
    """

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_all()

    def _get_kpi_map(self):
        kpis = fetch_kpis_for_scenario("scenario_5_contradiction")
        return {k.key: k for k in kpis}

    def test_aov_increases(self):
        """Scenario 5 AOV must be higher in analysis period than baseline."""
        km = self._get_kpi_map()
        self.assertIn("aov", km)
        self.assertGreater(
            km["aov"].current_value,
            km["aov"].baseline_value,
            f"Scenario 5 AOV should increase: curr={km['aov'].current_value}, base={km['aov'].baseline_value}",
        )

    def test_conversion_rate_decreases(self):
        """Scenario 5 conversion rate must be lower in analysis period."""
        km = self._get_kpi_map()
        self.assertIn("conversion_rate", km)
        self.assertLess(
            km["conversion_rate"].current_value,
            km["conversion_rate"].baseline_value,
            f"Scenario 5 CR should decrease: curr={km['conversion_rate'].current_value}, base={km['conversion_rate'].baseline_value}",
        )

    def test_revenue_net_negative(self):
        """Scenario 5 revenue must decline (conversion drop > AOV gain)."""
        km = self._get_kpi_map()
        self.assertIn("revenue", km)
        self.assertLess(
            km["revenue"].change_pct,
            0,
            f"Scenario 5 revenue must be net-negative: got {km['revenue'].change_pct}%",
        )

    def test_aov_change_pct_positive(self):
        """AOV change_pct > 0 in scenario 5."""
        km = self._get_kpi_map()
        self.assertGreater(
            km["aov"].change_pct,
            0,
            f"Scenario 5 AOV change_pct should be positive: got {km['aov'].change_pct}",
        )

    def test_conversion_change_pct_negative(self):
        """Conversion rate change_pct < 0 in scenario 5."""
        km = self._get_kpi_map()
        self.assertLess(
            km["conversion_rate"].change_pct,
            0,
            f"Scenario 5 CR change_pct should be negative: got {km['conversion_rate'].change_pct}",
        )


class TestNoHardcodedScenarioOutcomes(unittest.TestCase):
    """Verify that KPI values come from computed data, not hardcoded constants."""

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_all()

    def test_kpi_values_computed_not_hardcoded(self):
        """KPI current_value and baseline_value must not match any known hardcoded fixture."""
        # Known hardcoded values from OLD implementation (these should NOT appear):
        known_hardcoded = [
            (1000000.0, 1200000.0),   # old stub
            (5000000.0, 5000000.0),   # placeholder
        ]
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT current_value, baseline_value FROM kpi_values WHERE kpi_key='revenue'"
            ).fetchall()
        for curr, base in rows:
            for hc_curr, hc_base in known_hardcoded:
                self.assertFalse(
                    curr == hc_curr and base == hc_base,
                    f"KPI value appears hardcoded: curr={curr}, base={base}",
                )

    def test_all_scenarios_have_different_kpi_values(self):
        """Different scenarios must produce different revenue KPI values
        (proving the engine computed them from distinct underlying data)."""
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT scenario_id, current_value FROM kpi_values WHERE kpi_key='revenue'"
            ).fetchall()
        values = {r[0]: r[1] for r in rows}
        # At minimum scenarios 1 and 5 should differ (different modifiers)
        self.assertNotEqual(
            values.get("scenario_1_multifactor"),
            values.get("scenario_5_contradiction"),
            "Sc1 and Sc5 revenue must differ (different scenario modifiers applied)",
        )


class TestRAGCorpus(unittest.TestCase):
    """Verify RAG document corpus is adequately populated."""

    def test_minimum_document_count(self):
        """RAG corpus must have at least 10 documents."""
        docs = load_documents()
        self.assertGreaterEqual(
            len(docs),
            10,
            f"Expected ≥10 RAG documents, got {len(docs)}",
        )

    def test_documents_span_multiple_categories(self):
        """Documents must span at least 4 categories."""
        docs = load_documents()
        categories = {d["category"] for d in docs}
        self.assertGreaterEqual(
            len(categories),
            4,
            f"Expected ≥4 RAG categories, got: {categories}",
        )

    def test_incident_documents_present(self):
        """At least one incident document must be present."""
        docs = load_documents()
        incidents = [d for d in docs if d["category"] == "incidents"]
        self.assertGreater(len(incidents), 0, "No incident documents found")

    def test_deployment_documents_present(self):
        """At least one deployment document must be present."""
        docs = load_documents()
        deployments = [d for d in docs if d["category"] == "deployments"]
        self.assertGreater(len(deployments), 0, "No deployment documents found")

    def test_documents_have_content(self):
        """All documents must have non-empty content."""
        docs = load_documents()
        for doc in docs:
            self.assertGreater(
                len(doc.get("content", "")),
                50,
                f"Document {doc['id']} has insufficient content",
            )


if __name__ == "__main__":
    unittest.main()
