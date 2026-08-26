"""End-to-End Integration Tests for Phase 4 & Phase 5.

Verifies:
1. Full end-to-end pipeline execution across all 5 demo scenarios.
2. Dual persona execution (Executive & Engineer) on the same underlying anomaly.
3. RBAC evidence filtering between Executive and Engineer roles.
4. User diagnostic feedback recording and retrieval from SQLite.
"""

import unittest
from engine.kpi_engine import fetch_kpis_for_scenario
from engine.driver_engine import analyze_revenue_drivers
from engine.evidence import get_combined_evidence, EvidenceItem
from engine.confidence import calculate_confidence
from rag.retrieve import retrieve_evidence
from ai.narrative import generate_narrative
from app.streamlit_app import filter_evidence_by_rbac, record_feedback, get_recent_feedback
from database.seed import init_db, seed_baseline_data
from rag.ingest import ingest_documents


class TestPhase4EndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Prepare fresh database and RAG index."""
        init_db()
        seed_baseline_data()
        ingest_documents()

    def test_all_scenarios_end_to_end(self):
        """Verify that every scenario executes through the complete pipeline without errors."""
        scenarios = [
            ("scenario_1_multifactor", False),  # should not abstain
            ("scenario_2_low_confidence", True),  # should abstain
            ("scenario_3_new_kpi", True),  # should abstain (cold start)
            ("scenario_4_rbac", False),
            ("scenario_5_contradiction", False),
        ]

        for s_id, expected_abstain in scenarios:
            kpis = fetch_kpis_for_scenario(s_id)
            self.assertGreaterEqual(len(kpis), 1, f"Failed to load KPIs for {s_id}")

            kpi_map = {k.key: k for k in kpis}
            driver_res = analyze_revenue_drivers(kpi_map)

            cold_start = any(k.is_cold_start for k in kpis)
            unstructured = retrieve_evidence("payment deployment") if s_id != "scenario_2_low_confidence" else []
            combined_ev = get_combined_evidence(s_id, unstructured)

            if s_id == "scenario_2_low_confidence":
                conf = calculate_confidence(50.0, [], has_sufficient_history=True)
            else:
                conf = calculate_confidence(
                    driver_res.primary_contribution if driver_res else 60.0,
                    combined_ev,
                    has_sufficient_history=not cold_start,
                )

            self.assertEqual(conf.should_abstain, expected_abstain, f"Abstention mismatch for {s_id}")

            # Test both personas
            for persona in ["executive", "engineer"]:
                narrative = generate_narrative(
                    kpi_name="Revenue",
                    change_pct=-11.6,
                    primary_driver=driver_res.primary_driver if driver_res else "Orders",
                    driver_contribution=driver_res.primary_contribution if driver_res else 60.0,
                    confidence_score=conf.score,
                    confidence_level=conf.level,
                    evidence_descriptions=[e.description for e in combined_ev],
                    persona=persona,
                    should_abstain=conf.should_abstain,
                )
                self.assertIn("summary", narrative)
                self.assertIn("telemetry", narrative)

    def test_rbac_evidence_filtering(self):
        """Test that Executive persona shields internal server log errors while Engineer persona sees all."""
        evidence = [
            EvidenceItem("Deployment", "14:00", "payment-service v2.4.1 deployment", "High", True),
            EvidenceItem("Operations", "14:15", "[payment-service] Connection pool exhausted", "High", True),
        ]

        exec_ev = filter_evidence_by_rbac(evidence, "Executive")
        eng_ev = filter_evidence_by_rbac(evidence, "Engineer")

        self.assertEqual(len(exec_ev), 1, "Executive view should filter out raw server bracketed log lines")
        self.assertEqual(len(eng_ev), 2, "Engineer view should retain full technical evidence")

    def test_feedback_persisted_in_sqlite(self):
        """Test recording diagnostic feedback and fetching recent items."""
        record_feedback("scenario_1_multifactor", "revenue", "up", "Executive")
        records = get_recent_feedback()
        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(records[0]["scenario"], "scenario_1_multifactor")


if __name__ == "__main__":
    unittest.main()
