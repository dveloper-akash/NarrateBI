"""Part 2 Regression Tests: Driver Correctness, Confidence Calibration, Dynamic RAG.

Critical assertions:
1. AOV ↑, Revenue ↓  →  AOV impact_direction == 'positive' (NEVER negative)
2. Conversion ↓       →  Conversion impact_direction == 'negative'
3. Ambiguous drivers  →  confidence falls, abstention triggered
4. Missing evidence   →  confidence is Low, should_abstain True
5. Contradictory evidence → contradiction_notes non-empty, confidence reduced
6. Cold start         →  score == 20, should_abstain True
7. Dynamic RAG query  →  changes when inputs change
8. Scenario 5 end-to-end: AOV + Revenue, correct primary negative driver
"""

import unittest
from typing import List

from engine.kpi_engine import evaluate_kpi, fetch_kpis_for_scenario, load_kpi_contracts, KPIResult
from engine.driver_engine import (
    decompose_multiplicative_pair,
    analyze_revenue_drivers,
    get_negative_contributors,
    get_positive_contributors,
    DriverAnalysisResult,
)
from engine.confidence import calculate_confidence, ConfidenceScore
from engine.evidence import EvidenceItem, check_contradiction, get_combined_evidence
from rag.query_builder import build_rag_query
from database.seed import init_db, seed_all, DB_PATH


def make_kpi(key: str, current: float, baseline: float, history_days: int = 30) -> KPIResult:
    """Helper to create a KPIResult directly for unit tests."""
    contracts = load_kpi_contracts()
    return evaluate_kpi(key, current, baseline, history_days=history_days, contracts=contracts)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Driver Contribution Correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestDriverImpactDirection(unittest.TestCase):
    """Verify signed impact_direction is independent of anomaly status."""

    def test_aov_up_revenue_down_aov_is_positive_contributor(self):
        """AOV increasing while Revenue falls → AOV contribution is POSITIVE.

        This is the core correctness requirement of Part 2.
        An anomalous AOV increase does NOT make AOV a negative contributor.
        """
        # Revenue = Orders × AOV
        # Orders: 5000 → 3500 (−30%)
        # AOV:    1000 → 1220 (+22%)
        # Revenue: 5_000_000 → 4_270_000 (−14.6%)
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-14.6,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=3500,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1220,
            factor_b_base=1000,
        )
        aov_driver = next(d for d in result.drivers if d.kpi_key == "aov")
        orders_driver = next(d for d in result.drivers if d.kpi_key == "orders")

        # AOV went up → its effect on Revenue is POSITIVE (partially offsets the decline)
        self.assertEqual(
            aov_driver.impact_direction, "positive",
            f"AOV (+22%) must have positive impact on Revenue, got: {aov_driver.impact_direction}"
        )
        # Orders went down → its effect on Revenue is NEGATIVE (drives the decline)
        self.assertEqual(
            orders_driver.impact_direction, "negative",
            f"Orders (−30%) must have negative impact on Revenue, got: {orders_driver.impact_direction}"
        )

    def test_both_up_both_positive(self):
        """When both factors increase, both should have positive impact direction."""
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=18.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=5500,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="AOV",
            factor_b_curr=1100,
            factor_b_base=1000,
        )
        for d in result.drivers:
            if d.kpi_key != "interaction":
                self.assertEqual(
                    d.impact_direction, "positive",
                    f"{d.name} increased, must have positive impact, got: {d.impact_direction}"
                )

    def test_both_down_both_negative(self):
        """When both factors decrease, both should have negative impact direction."""
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-20.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=4000,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="AOV",
            factor_b_curr=900,
            factor_b_base=1000,
        )
        for d in result.drivers:
            if d.kpi_key != "interaction":
                self.assertEqual(
                    d.impact_direction, "negative",
                    f"{d.name} decreased, must have negative impact, got: {d.impact_direction}"
                )

    def test_conversion_down_aov_up_correct_attribution(self):
        """Scenario 5 pattern: Conversion ↓, AOV ↑ → Orders ↓.
        When decomposing Revenue = Orders × AOV:
        - Orders (from conversion drop) should be the primary negative driver
        - AOV should be a positive contributor
        """
        # Orders: 5000 → 3600 (conversion suppression)
        # AOV: 1000 → 1220 (premium pricing)
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-12.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=3600,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1220,
            factor_b_base=1000,
        )
        aov_d = next(d for d in result.drivers if d.kpi_key == "aov")
        orders_d = next(d for d in result.drivers if d.kpi_key == "orders")

        self.assertEqual(aov_d.impact_direction, "positive",
                         "AOV must be a positive contributor to revenue")
        self.assertEqual(orders_d.impact_direction, "negative",
                         "Orders (conversion-driven) must be the negative contributor")
        self.assertGreater(orders_d.contribution_pct, aov_d.contribution_pct,
                           "Orders should explain more of the movement than AOV")

    def test_contribution_pcts_sum_to_100(self):
        """All driver contribution_pct values must sum to 100%."""
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-14.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=3500,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="AOV",
            factor_b_curr=1220,
            factor_b_base=1000,
        )
        total = sum(d.contribution_pct for d in result.drivers)
        self.assertAlmostEqual(total, 100.0, places=1,
                               msg=f"Contribution pcts must sum to 100, got {total}")

    def test_is_anomalous_independent_of_impact(self):
        """A driver can be anomalous (large own change) while having POSITIVE impact.
        is_anomalous should NOT influence impact_direction.
        """
        contracts = load_kpi_contracts()
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-8.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=4600,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1180,
            factor_b_base=1000,
            contracts=contracts,  # AOV threshold=5%, so +18% is anomalous
        )
        aov_d = next(d for d in result.drivers if d.kpi_key == "aov")
        # AOV is anomalous (18% > 5% threshold) but has positive impact
        self.assertTrue(aov_d.is_anomalous, "AOV at +18% should be flagged as anomalous")
        self.assertEqual(aov_d.impact_direction, "positive",
                         "Anomalous AOV still has POSITIVE impact on Revenue")

    def test_get_negative_contributors_helper(self):
        """get_negative_contributors returns only negative-impact drivers."""
        result = decompose_multiplicative_pair(
            target_name="Revenue",
            target_change_pct=-10.0,
            factor_a_key="orders",
            factor_a_name="Orders",
            factor_a_curr=3800,
            factor_a_base=5000,
            factor_b_key="aov",
            factor_b_name="AOV",
            factor_b_curr=1150,
            factor_b_base=1000,
        )
        negatives = get_negative_contributors(result)
        positives = get_positive_contributors(result)
        for d in negatives:
            self.assertEqual(d.impact_direction, "negative")
        for d in positives:
            self.assertEqual(d.impact_direction, "positive")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Confidence Calibration
# ─────────────────────────────────────────────────────────────────────────────

class TestConfidenceCalibration(unittest.TestCase):

    def _full_evidence(self) -> List[EvidenceItem]:
        return [
            EvidenceItem("Deployment", "2026-08-24 13:00", "payment-service v2.4.1 deployed", "High", True,
                         evidence_type="deployment", affected_entity="payment-service"),
            EvidenceItem("Payments", "2026-08-24 14:00", "Checkout errors increased 140%", "High", True,
                         evidence_type="error_surge", affected_entity="checkout-service"),
            EvidenceItem("Incidents", "2026-08-24 14:15", "INC-84920: Gateway Timeout Storm", "High", False,
                         evidence_type="rag_doc", affected_entity="gateway-proxy"),
        ]

    def test_high_confidence_strong_driver_full_evidence(self):
        """Strong driver + full corroborating evidence → High confidence."""
        score = calculate_confidence(
            primary_driver_contribution=78.0,
            evidence_items=self._full_evidence(),
            has_sufficient_history=True,
            driver_ambiguity_gap=40.0,
            history_days=60,
        )
        self.assertEqual(score.level, "High")
        self.assertFalse(score.should_abstain)
        self.assertGreaterEqual(score.score, 68)

    def test_confidence_capped_at_95(self):
        """Confidence must never reach 100 for normal business insights."""
        score = calculate_confidence(
            primary_driver_contribution=99.0,
            evidence_items=self._full_evidence(),
            has_sufficient_history=True,
            driver_ambiguity_gap=80.0,
            history_days=180,
            data_freshness_days=0,
        )
        self.assertLessEqual(score.score, 95,
                              "Normal business confidence must be capped at 95")

    def test_low_confidence_no_evidence(self):
        """No evidence → Low confidence → should_abstain."""
        score = calculate_confidence(
            primary_driver_contribution=50.0,
            evidence_items=[],
            has_sufficient_history=True,
        )
        self.assertEqual(score.level, "Low")
        self.assertTrue(score.should_abstain)
        self.assertLess(score.score, 43)

    def test_cold_start_abstention(self):
        """Cold start always abstains at score=20."""
        score = calculate_confidence(
            primary_driver_contribution=99.0,
            evidence_items=self._full_evidence(),
            has_sufficient_history=False,
        )
        self.assertEqual(score.score, 20)
        self.assertTrue(score.should_abstain)
        self.assertEqual(score.level, "Low")

    def test_ambiguous_drivers_reduce_confidence(self):
        """Drivers nearly equal in contribution → confidence reduced (ambiguity gap < 5)."""
        score_ambiguous = calculate_confidence(
            primary_driver_contribution=38.0,
            evidence_items=[],
            has_sufficient_history=True,
            driver_ambiguity_gap=2.0,  # very close
        )
        score_clear = calculate_confidence(
            primary_driver_contribution=75.0,
            evidence_items=self._full_evidence(),
            has_sufficient_history=True,
            driver_ambiguity_gap=45.0,
        )
        self.assertLess(score_ambiguous.score, score_clear.score,
                        "Ambiguous drivers must yield lower confidence")
        self.assertTrue(score_ambiguous.should_abstain,
                        "Ambiguous drivers with no evidence should trigger abstention")

    def test_contradiction_reduces_confidence(self):
        """Contradictory evidence reduces confidence and surfaces contradiction_notes."""
        evidence_with_contradiction = self._full_evidence() + [
            EvidenceItem("Marketing", "2026-08-24", "Record ROAS and strong conversion performance",
                         "Medium", False, evidence_type="rag_doc", affected_entity="campaigns"),
        ]
        score_no_conflict = calculate_confidence(
            primary_driver_contribution=76.0,
            evidence_items=self._full_evidence(),
            has_sufficient_history=True,
            driver_ambiguity_gap=40.0,
            structured_evidence=[e for e in self._full_evidence() if e.is_structured],
            rag_evidence=[e for e in self._full_evidence() if not e.is_structured],
        )
        score_with_conflict = calculate_confidence(
            primary_driver_contribution=76.0,
            evidence_items=evidence_with_contradiction,
            has_sufficient_history=True,
            driver_ambiguity_gap=40.0,
            structured_evidence=[e for e in self._full_evidence() if e.is_structured],
            rag_evidence=[e for e in evidence_with_contradiction if not e.is_structured],
        )
        self.assertLess(score_with_conflict.score, score_no_conflict.score,
                        "Contradictory evidence must reduce confidence score")
        self.assertGreater(len(score_with_conflict.contradiction_notes), 0,
                           "Contradictions must be surfaced in contradiction_notes")

    def test_abstention_message_present(self):
        """Low-confidence abstention must provide useful missing evidence hints."""
        score = calculate_confidence(
            primary_driver_contribution=30.0,
            evidence_items=[],
            has_sufficient_history=True,
            driver_ambiguity_gap=2.0,
        )
        self.assertTrue(score.should_abstain)
        self.assertGreater(len(score.missing_evidence_hints), 0)

    def test_deep_history_boosts_confidence(self):
        """More history days should produce higher confidence than minimal history."""
        evidence = [
            EvidenceItem("Deployment", "2026-08-24", "service v2 deployed", "High", True,
                         evidence_type="deployment", affected_entity="svc"),
        ]
        score_minimal = calculate_confidence(
            primary_driver_contribution=70.0,
            evidence_items=evidence,
            has_sufficient_history=True,
            driver_ambiguity_gap=30.0,
            history_days=15,
        )
        score_deep = calculate_confidence(
            primary_driver_contribution=70.0,
            evidence_items=evidence,
            has_sufficient_history=True,
            driver_ambiguity_gap=30.0,
            history_days=90,
        )
        self.assertGreaterEqual(score_deep.score, score_minimal.score,
                                "Deeper history should produce >= confidence")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Evidence Contradiction Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceContradiction(unittest.TestCase):

    def test_contradiction_flag_set_on_conflicting_rag_item(self):
        """RAG item claiming 'strong conversion' contradicts structured error surge."""
        structured = [
            EvidenceItem("Payments", "2026-08-24", "Checkout errors increased 140%", "High", True,
                         evidence_type="error_surge", affected_entity="checkout"),
        ]
        rag = [
            EvidenceItem("Marketing", "2026-08-24", "Record ROAS and strong conversion performance",
                         "Medium", False, evidence_type="rag_doc", affected_entity="campaigns"),
        ]
        flagged = check_contradiction(structured, rag)
        self.assertTrue(flagged[0].contradiction_flag,
                        "Marketing claim of strong conversion contradicts checkout error surge")

    def test_non_contradictory_rag_not_flagged(self):
        """RAG item about an incident should NOT be flagged as contradiction."""
        structured = [
            EvidenceItem("Payments", "2026-08-24", "Checkout errors increased 140%", "High", True,
                         evidence_type="error_surge", affected_entity="checkout"),
        ]
        rag = [
            EvidenceItem("Incidents", "2026-08-24", "INC-8492: payment gateway timeout storm",
                         "High", False, evidence_type="rag_doc", affected_entity="gateway"),
        ]
        flagged = check_contradiction(structured, rag)
        self.assertFalse(flagged[0].contradiction_flag,
                         "Incident doc about errors should not be flagged as contradiction")

    def test_no_errors_no_contradiction(self):
        """Without structured errors, no contradictions should be detected."""
        structured = [
            EvidenceItem("Deployment", "2026-08-22", "pricing-engine v3.1 deployed", "High", True,
                         evidence_type="deployment", affected_entity="pricing-engine"),
        ]
        rag = [
            EvidenceItem("Marketing", "2026-08-22", "Record ROAS and strong conversion",
                         "Medium", False, evidence_type="rag_doc", affected_entity="campaigns"),
        ]
        flagged = check_contradiction(structured, rag)
        self.assertFalse(flagged[0].contradiction_flag,
                         "No error signals in structured → no contradiction possible")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dynamic RAG Query Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestDynamicRAGQuery(unittest.TestCase):

    def _make_revenue_kpi(self, change: float) -> KPIResult:
        return make_kpi("revenue", 4300000, 5000000 * (1 + change / 100) if change != 0 else 5000000)

    def test_query_contains_kpi_movement(self):
        """Query must encode KPI name and direction."""
        kpi = make_kpi("revenue", 4300000, 5000000)
        query = build_rag_query(kpi, None)
        self.assertIn("Revenue", query)
        self.assertIn("decreased", query.lower())

    def test_query_contains_negative_driver(self):
        """Query must include the primary negative contributor."""
        kpi = make_kpi("revenue", 4300000, 5000000)
        # AOV up, Orders down → Orders is negative
        driver_result = decompose_multiplicative_pair(
            target_name="Revenue", target_change_pct=-14.0,
            factor_a_key="orders", factor_a_name="Orders",
            factor_a_curr=3600, factor_a_base=5000,
            factor_b_key="aov", factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1220, factor_b_base=1000,
        )
        query = build_rag_query(kpi, driver_result, "2026-08-22", "2026-08-28")
        self.assertIn("Orders", query,
                      "Query must mention primary negative contributor (Orders)")
        self.assertIn("2026-08-22", query, "Query must include date range")

    def test_different_drivers_produce_different_queries(self):
        """Changing driver inputs must change the query (not hardcoded)."""
        kpi = make_kpi("revenue", 4300000, 5000000)

        driver_orders_negative = decompose_multiplicative_pair(
            target_name="Revenue", target_change_pct=-14.0,
            factor_a_key="orders", factor_a_name="Orders",
            factor_a_curr=3600, factor_a_base=5000,
            factor_b_key="aov", factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1220, factor_b_base=1000,
        )

        driver_aov_negative = decompose_multiplicative_pair(
            target_name="Revenue", target_change_pct=-14.0,
            factor_a_key="orders", factor_a_name="Orders",
            factor_a_curr=5000, factor_a_base=5000,  # orders flat
            factor_b_key="aov", factor_b_name="Average Order Value (AOV)",
            factor_b_curr=860, factor_b_base=1000,   # AOV dropped
        )

        query_1 = build_rag_query(kpi, driver_orders_negative)
        query_2 = build_rag_query(kpi, driver_aov_negative)
        self.assertNotEqual(query_1, query_2,
                            "Different driver inputs must produce different RAG queries")

    def test_query_includes_positive_offset_note(self):
        """When AOV ↑ (positive contribution), query should note the partial offset."""
        kpi = make_kpi("revenue", 4300000, 5000000)
        driver_result = decompose_multiplicative_pair(
            target_name="Revenue", target_change_pct=-14.0,
            factor_a_key="orders", factor_a_name="Orders",
            factor_a_curr=3600, factor_a_base=5000,
            factor_b_key="aov", factor_b_name="Average Order Value (AOV)",
            factor_b_curr=1220, factor_b_base=1000,
        )
        query = build_rag_query(kpi, driver_result)
        # Should mention positive offset (AOV)
        self.assertIn("positive", query.lower(),
                      "Query should note positive offset driver (AOV) when it increases")

    def test_query_without_driver_still_valid(self):
        """Query builder must work even with no driver result."""
        kpi = make_kpi("revenue", 4300000, 5000000)
        query = build_rag_query(kpi, None, "2026-08-22", "2026-08-28")
        self.assertIn("Revenue", query)
        self.assertIsInstance(query, str)
        self.assertGreater(len(query), 20)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scenario 5 End-to-End: AOV ↑, Conversion ↓, Revenue ↓
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario5EndToEnd(unittest.TestCase):
    """Full pipeline test: data → KPIs → drivers → verify correct attribution."""

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_all()

    def test_scenario_5_aov_is_positive_contributor_to_revenue(self):
        """AOV up + Revenue down → AOV must have positive impact on revenue."""
        kpis = fetch_kpis_for_scenario("scenario_5_contradiction")
        kpi_map = {k.key: k for k in kpis}

        self.assertIn("revenue", kpi_map)
        self.assertIn("aov", kpi_map)
        self.assertLess(kpi_map["revenue"].change_pct, 0, "Revenue must be negative")
        self.assertGreater(kpi_map["aov"].change_pct, 0, "AOV must be positive")

        driver_result = analyze_revenue_drivers(kpi_map)
        self.assertIsNotNone(driver_result)

        aov_driver = next(
            (d for d in driver_result.drivers if d.kpi_key == "aov"), None
        )
        self.assertIsNotNone(aov_driver, "AOV driver must be present in decomposition")
        self.assertEqual(
            aov_driver.impact_direction, "positive",
            f"Scenario 5: AOV must have POSITIVE impact direction, got '{aov_driver.impact_direction}'. "
            f"AOV change: {aov_driver.observed_change_pct:+.1f}%, "
            f"contribution_to_target: {aov_driver.contribution_to_target:.0f}"
        )

    def test_scenario_5_orders_is_primary_negative_driver(self):
        """Orders (driven by conversion drop) must be primary negative contributor."""
        kpis = fetch_kpis_for_scenario("scenario_5_contradiction")
        kpi_map = {k.key: k for k in kpis}

        driver_result = analyze_revenue_drivers(kpi_map)
        negatives = get_negative_contributors(driver_result)

        self.assertGreater(len(negatives), 0, "At least one negative contributor required")
        self.assertEqual(negatives[0].kpi_key, "orders",
                         "Orders should be the primary negative driver when conversion drops")

    def test_scenario_5_conversion_is_negative_sub_driver(self):
        """In Level 2 decomposition, Conversion Rate must be the negative sub-driver."""
        kpis = fetch_kpis_for_scenario("scenario_5_contradiction")
        kpi_map = {k.key: k for k in kpis}

        driver_result = analyze_revenue_drivers(kpi_map)
        self.assertIsNotNone(driver_result.sub_driver_result)

        sub = driver_result.sub_driver_result
        cr_driver = next(
            (d for d in sub.drivers if d.kpi_key == "conversion_rate"), None
        )
        self.assertIsNotNone(cr_driver, "Conversion rate must appear in Level 2 decomposition")
        self.assertEqual(
            cr_driver.impact_direction, "negative",
            f"Conversion Rate must be a NEGATIVE sub-driver, got '{cr_driver.impact_direction}'"
        )

    def test_scenario_5_rag_query_mentions_conversion_not_aov_as_culprit(self):
        """RAG query derived from Scenario 5 should cite conversion/orders (not AOV) as culprit."""
        kpis = fetch_kpis_for_scenario("scenario_5_contradiction")
        kpi_map = {k.key: k for k in kpis}

        revenue_kpi = kpi_map["revenue"]
        driver_result = analyze_revenue_drivers(kpi_map)

        query = build_rag_query(revenue_kpi, driver_result, "2026-08-22", "2026-08-28")

        # The query must mention the conversion/orders problem
        self.assertTrue(
            "conversion" in query.lower() or "orders" in query.lower() or "checkout" in query.lower(),
            f"Query should reference conversion/orders as the culprit. Got: {query}"
        )
        # The query must NOT frame AOV as a negative problem
        # (AOV appears as "positive offset" not as a culprit)
        query_lower = query.lower()
        # Check it's not saying "aov" as primary negative contributor
        if "average order value" in query_lower:
            # AOV should only appear in "positive offset" context
            aov_idx = query_lower.find("average order value")
            before_aov = query_lower[max(0, aov_idx - 50):aov_idx]
            self.assertIn("positive", before_aov + query_lower[aov_idx:aov_idx + 100],
                          "AOV in query should be framed as positive offset, not culprit")


if __name__ == "__main__":
    unittest.main()
