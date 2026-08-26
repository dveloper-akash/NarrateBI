"""Unit Tests for Phase 2: Evidence & RAG Layer.

Verifies:
1. Document ingestion and metadata parsing across all 4 categories.
2. Contextual evidence retrieval from manifest / ChromaDB.
3. Structured signal extraction from SQLite tables.
4. Deterministic 4-factor confidence scoring.
5. Strict abstention triggers (< 45% or cold start).
"""

import unittest
from pathlib import Path

from rag.ingest import ingest_documents, load_documents, extract_metadata_from_content
from rag.retrieve import retrieve_evidence
from engine.evidence import fetch_structured_evidence, get_combined_evidence, EvidenceItem
from engine.confidence import calculate_confidence, ConfidenceScore
from database.seed import init_db, seed_baseline_data


class TestPhase2RagAndConfidence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Prepare database and document index before testing."""
        init_db()
        seed_baseline_data()
        ingest_documents()

    def test_document_ingestion_and_metadata(self):
        """Test that operational documents are discovered and parsed with rich metadata."""
        docs = load_documents()
        self.assertGreaterEqual(len(docs), 4, "Should find at least 4 operational markdown documents")

        categories = {d["category"] for d in docs}
        expected_cats = {"deployments", "incidents", "logs", "support"}
        for cat in expected_cats:
            self.assertIn(cat, categories, f"Category {cat} not found in docs")

        # Test metadata extraction
        sample_content = """# Deployment Record: payment-service v2.4.1
- **Service**: `payment-service`
- **Version**: `v2.4.1`
- **Timestamp**: `2026-08-26 14:00:00 UTC`
"""
        meta = extract_metadata_from_content(sample_content)
        self.assertEqual(meta.get("service"), "payment-service")
        self.assertEqual(meta.get("version"), "v2.4.1")

    def test_rag_evidence_retrieval(self):
        """Test retrieval of documents based on query context."""
        query = "payment gateway timeout errors and checkout failure"
        results = retrieve_evidence(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        self.assertIsInstance(results[0], EvidenceItem)
        self.assertFalse(results[0].is_structured)

        # Category filter test
        deploy_res = retrieve_evidence("payment", top_k=2, category="deployments")
        if deploy_res:
            self.assertEqual(deploy_res[0].source.lower(), "deployments")

    def test_structured_evidence_extraction(self):
        """Test extraction of structured transaction surges and deployment logs from SQLite."""
        evidence = fetch_structured_evidence("scenario_1_multifactor")
        self.assertGreaterEqual(len(evidence), 2, "Scenario 1 should have structured error spikes and deployments")

        sources = [e.source for e in evidence]
        self.assertIn("Payments", sources)
        self.assertIn("Deployment", sources)

        # Check for checkout error surge description
        err_item = next(e for e in evidence if e.source == "Payments")
        self.assertIn("increased", err_item.description.lower())

    def test_confidence_scoring_high_confidence(self):
        """Test high confidence score when primary driver is strong and operational evidence is present."""
        evidence = [
            EvidenceItem("Deployment", "14:00", "payment-service v2.4.1 deployment", "High", True),
            EvidenceItem("Payments", "15:00", "Checkout errors increased 42%", "High", True),
            EvidenceItem("Incidents", "14:15", "INC-84920: Gateway Timeout Storm", "High", False),
        ]
        score = calculate_confidence(
            primary_driver_contribution=76.0,
            evidence_items=evidence,
            has_sufficient_history=True,
        )
        self.assertEqual(score.level, "High")
        self.assertFalse(score.should_abstain)
        self.assertGreaterEqual(score.score, 70)
        self.assertGreater(len(score.factors), 2)

    def test_confidence_scoring_low_confidence_abstention(self):
        """Test that missing operational evidence forces low score and should_abstain = True."""
        # Empty evidence items
        score = calculate_confidence(
            primary_driver_contribution=50.0,
            evidence_items=[],
            has_sufficient_history=True,
        )
        self.assertEqual(score.level, "Low")
        self.assertTrue(score.should_abstain)
        self.assertLess(score.score, 45)
        self.assertGreaterEqual(len(score.missing_evidence_hints), 1)

    def test_confidence_scoring_cold_start_abstention(self):
        """Test that cold-start KPI (< 14 days) unconditionally triggers abstention."""
        score = calculate_confidence(
            primary_driver_contribution=85.0,
            evidence_items=[],
            has_sufficient_history=False,
        )
        self.assertEqual(score.level, "Low")
        self.assertTrue(score.should_abstain)
        self.assertEqual(score.score, 20)
        self.assertIn("Insufficient baseline history", score.factors[0])


if __name__ == "__main__":
    unittest.main()
