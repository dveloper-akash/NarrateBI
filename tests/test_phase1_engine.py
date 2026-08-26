"""Unit Tests for Phase 1: Database & Deterministic Engines.

Verifies:
1. KPI contract loading and mathematical formula calculations.
2. Deterministic anomaly threshold evaluation.
3. Cold-start detection for KPIs with < 14 days of history.
4. Level 1 (Revenue = Orders × AOV) & Level 2 (Orders = Sessions × CR) driver decomposition.
5. SQLite seed integrity across all 5 test scenarios.
"""

import unittest
import sqlite3
from pathlib import Path

from engine.kpi_engine import (
    load_kpi_contracts,
    calculate_change_pct,
    calculate_conversion_rate,
    calculate_revenue,
    calculate_aov,
    evaluate_kpi,
    fetch_kpis_for_scenario,
)
from engine.driver_engine import (
    analyze_revenue_drivers,
    decompose_multiplicative_pair,
)
from database.seed import init_db, seed_baseline_data, DB_PATH


class TestPhase1DeterministicEngines(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Seed clean database before testing."""
        init_db()
        seed_baseline_data()

    def test_kpi_contract_loading(self):
        """Test that all 5 connected KPIs and new_product_conversion are defined."""
        contracts = load_kpi_contracts()
        expected_keys = ["revenue", "orders", "conversion_rate", "sessions", "aov", "new_product_conversion"]
        for key in expected_keys:
            self.assertIn(key, contracts, f"Contract missing for {key}")
            self.assertTrue(contracts[key].name)
            self.assertTrue(contracts[key].formula)
            self.assertGreater(contracts[key].threshold, 0)
            self.assertGreaterEqual(contracts[key].min_history_days, 14)

    def test_kpi_math_formulas(self):
        """Test deterministic math calculations."""
        # 1. Percentage change
        self.assertEqual(calculate_change_pct(44.0, 50.0), -12.0)
        self.assertEqual(calculate_change_pct(55.0, 50.0), 10.0)
        self.assertEqual(calculate_change_pct(50.0, 50.0), 0.0)

        # 2. Conversion Rate: (Orders / Sessions) * 100
        # 5,000 / 100,000 * 100 = 5.0%
        self.assertEqual(calculate_conversion_rate(5000, 100000), 5.0)
        self.assertEqual(calculate_conversion_rate(4210, 100000), 4.21)

        # 3. Revenue: Orders * AOV
        # 5,000 * 1,000 = 5,000,000
        self.assertEqual(calculate_revenue(5000, 1000), 5000000.0)
        self.assertEqual(calculate_revenue(4210, 1050), 4420500.0)

        # 4. AOV: Revenue / Orders
        self.assertEqual(calculate_aov(5000000.0, 5000), 1000.0)
        self.assertEqual(calculate_aov(4420500.0, 4210), 1050.0)

    def test_anomaly_detection_thresholds(self):
        """Test that movements exceeding configured threshold are flagged as anomalies."""
        contracts = load_kpi_contracts()

        # Revenue threshold is 10.0%
        # -12% change -> Anomaly
        res_anomaly = evaluate_kpi("revenue", 4400000.0, 5000000.0, history_days=30, contracts=contracts)
        self.assertTrue(res_anomaly.is_anomaly)
        self.assertFalse(res_anomaly.is_cold_start)
        self.assertEqual(res_anomaly.change_pct, -12.0)

        # -5% change -> Normal (Not anomaly)
        res_normal = evaluate_kpi("revenue", 4750000.0, 5000000.0, history_days=30, contracts=contracts)
        self.assertFalse(res_normal.is_anomaly)

    def test_cold_start_guardrail(self):
        """Test that KPIs with < 14 days of history trigger cold-start and abstain from anomaly flag."""
        contracts = load_kpi_contracts()

        # 4 days history -> Cold Start
        res_cold = evaluate_kpi("new_product_conversion", 2.1, 3.5, history_days=4, contracts=contracts)
        self.assertTrue(res_cold.is_cold_start)
        self.assertFalse(res_cold.is_anomaly, "Cold start KPI should never be classified as an anomaly")
        self.assertEqual(res_cold.history_days, 4)

        # 20 days history -> Mature KPI
        res_mature = evaluate_kpi("new_product_conversion", 2.1, 3.5, history_days=20, contracts=contracts)
        self.assertFalse(res_mature.is_cold_start)
        self.assertTrue(res_mature.is_anomaly)

    def test_driver_variance_decomposition(self):
        """Test that variance decomposition calculates correct contributions summing to 100%."""
        # Scenario 1 values:
        # Base: Rev = 5000 * 1000 = 5,000,000
        # Curr: Rev = 4210 * 1050 = 4,420,500
        # Orders: 5000 -> 4210 (Δ = -790, effect = -790,000)
        # AOV: 1000 -> 1050 (Δ = +50, effect = +250,000)
        # Interaction: -790 * 50 = -39,500
        res = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-11.59,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=4210,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="AOV",
            factor_b_curr=1050,
            factor_b_base=1000,
        )

        self.assertEqual(res.primary_driver, "Orders")
        # Sum of contributions must equal 100%
        total_contrib = sum(d.contribution_pct for d in res.drivers)
        self.assertAlmostEqual(total_contrib, 100.0, places=1)
        self.assertGreater(res.primary_contribution, 70.0)

    def test_multi_tier_driver_analysis(self):
        """Test hierarchical driver analysis: Revenue -> Orders -> Conversion Rate."""
        kpis = fetch_kpis_for_scenario("scenario_1_multifactor")
        kpi_map = {k.key: k for k in kpis}

        driver_res = analyze_revenue_drivers(kpi_map)
        self.assertIsNotNone(driver_res)
        self.assertEqual(driver_res.target_kpi, "Revenue")
        self.assertEqual(driver_res.primary_driver, "Orders")

        # Check sub-driver result (Level 2)
        self.assertIsNotNone(driver_res.sub_driver_result)
        self.assertEqual(driver_res.sub_driver_result.target_kpi, "Orders")
        self.assertEqual(driver_res.sub_driver_result.primary_driver, "Conversion Rate")
        self.assertEqual(driver_res.sub_driver_result.primary_contribution, 100.0)

    def test_database_all_scenarios_seeded(self):
        """Verify that all 5 scenarios can be fetched from SQLite with valid data."""
        scenario_ids = [
            "scenario_1_multifactor",
            "scenario_2_low_confidence",
            "scenario_3_new_kpi",
            "scenario_4_rbac",
            "scenario_5_contradiction",
        ]
        for s_id in scenario_ids:
            kpis = fetch_kpis_for_scenario(s_id)
            self.assertGreaterEqual(len(kpis), 1, f"No KPIs found for scenario {s_id}")

        # Check cold-start scenario specifically
        cold_kpis = fetch_kpis_for_scenario("scenario_3_new_kpi")
        has_cold = any(k.is_cold_start for k in cold_kpis)
        self.assertTrue(has_cold, "Scenario 3 must contain at least one cold start KPI")


if __name__ == "__main__":
    unittest.main()
