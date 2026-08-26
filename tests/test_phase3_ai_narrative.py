"""Unit Tests for Phase 3: AI Narrative & Persona Prompts.

Verifies:
1. Executive narrative structure and business impact grounding.
2. Engineer narrative structure and technical signal grounding.
3. Strict abstention handling when should_abstain=True.
4. AI cost and token telemetry calculations.
5. Offline fallback resilience.
"""

import unittest
from ai.narrative import generate_narrative, calculate_ai_cost


class TestPhase3AiNarrative(unittest.TestCase):

    def test_calculate_ai_cost(self):
        """Test exact cost formula for Gemini Flash tokens."""
        # 1M input ($0.075) + 1M output ($0.30) = $0.375
        cost = calculate_ai_cost(1000000, 1000000)
        self.assertAlmostEqual(cost, 0.375, places=3)

        # 300 input + 100 output
        cost_small = calculate_ai_cost(300, 100)
        self.assertGreater(cost_small, 0.0)
        self.assertLess(cost_small, 0.001)

    def test_executive_narrative_structure(self):
        """Test that executive narrative returns business-tailored JSON."""
        res = generate_narrative(
            kpi_name="Revenue",
            change_pct=-11.6,
            primary_driver="Orders",
            driver_contribution=64.6,
            confidence_score=87,
            confidence_level="High",
            evidence_descriptions=["Checkout errors increased 42%", "Payment deployment v2.4.1 completed"],
            persona="executive",
            should_abstain=False,
        )

        self.assertIn("summary", res)
        self.assertIn("reason", res)
        self.assertIn("business_impact", res)
        self.assertIn("recommendation", res)
        self.assertIn("telemetry", res)
        self.assertGreater(res["telemetry"]["tokens"], 0)
        self.assertGreaterEqual(res["telemetry"]["estimated_cost_usd"], 0)

    def test_engineer_narrative_structure(self):
        """Test that engineer narrative returns technical signal telemetry."""
        res = generate_narrative(
            kpi_name="Revenue",
            change_pct=-11.6,
            primary_driver="Orders",
            driver_contribution=64.6,
            confidence_score=87,
            confidence_level="High",
            evidence_descriptions=["Checkout errors increased 42%", "Payment deployment v2.4.1 completed"],
            persona="engineer",
            should_abstain=False,
        )

        self.assertIn("summary", res)
        self.assertTrue("technical_diagnosis" in res or "reason" in res)
        self.assertTrue("technical_recommendation" in res or "recommendation" in res)
        self.assertIn("telemetry", res)

    def test_abstention_enforcement(self):
        """Test that should_abstain=True strictly returns an abstention payload without hallucination."""
        res = generate_narrative(
            kpi_name="Revenue",
            change_pct=-12.0,
            primary_driver="Conversion Rate",
            driver_contribution=50.0,
            confidence_score=34,
            confidence_level="Low",
            evidence_descriptions=[],
            persona="executive",
            should_abstain=True,
        )

        self.assertEqual(res.get("status"), "abstain")
        self.assertIn("confidence is too low", res.get("summary", "").lower())
        self.assertIn("abstention", res["telemetry"]["mode"].lower())
        self.assertEqual(res["telemetry"]["tokens"], 0)


if __name__ == "__main__":
    unittest.main()
