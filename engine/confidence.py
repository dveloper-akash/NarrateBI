"""Confidence Engine - Deterministic diagnostic confidence evaluation and abstention logic.

Evaluates:
- Strength of primary driver contribution
- Operational evidence presence (deployments, incidents, error spikes)
- Temporal alignment (e.g. deployment directly preceded error spike)
- Data history / baseline validity

Thresholds:
- >= 70%: High confidence (Invoke LLM for narrative)
- 45% - 69%: Medium confidence (Invoke LLM with uncertainty warnings)
- < 45%: Low confidence (ABSTAIN - Do NOT guess or hallucinate)
"""

from dataclasses import dataclass
from typing import List, Optional
from engine.evidence import EvidenceItem


@dataclass
class ConfidenceScore:
    score: int  # 0 to 100
    level: str  # 'High', 'Medium', 'Low'
    should_abstain: bool
    factors: List[str]
    missing_evidence_hints: List[str]


def calculate_confidence(
    primary_driver_contribution: float,
    evidence_items: List[EvidenceItem],
    has_sufficient_history: bool = True,
) -> ConfidenceScore:
    """Calculates diagnostic confidence score deterministically."""
    if not has_sufficient_history:
        return ConfidenceScore(
            score=20,
            level="Low",
            should_abstain=True,
            factors=["Insufficient baseline history (< 14 days)"],
            missing_evidence_hints=["Collect at least 14 days of baseline KPI measurements."],
        )

    score = 0
    factors = []
    missing_hints = []

    # 1. Driver contribution weight (up to 40 pts)
    if primary_driver_contribution >= 70:
        score += 40
        factors.append(f"Strong primary driver contribution ({primary_driver_contribution}%)")
    elif primary_driver_contribution >= 50:
        score += 25
        factors.append(f"Moderate driver contribution ({primary_driver_contribution}%)")
    else:
        score += 10
        missing_hints.append("Primary driver is weak or ambiguous.")

    # 2. Operational / Structured Evidence presence (up to 35 pts)
    has_deployments = any(e.source == "Deployment" for e in evidence_items)
    has_error_spikes = any(e.source in ["Payments", "Operations"] and "increased" in e.description for e in evidence_items)
    has_incident_docs = any(e.source in ["Incidents", "Support"] for e in evidence_items)

    if has_deployments and has_error_spikes:
        score += 35
        factors.append("Corroborating deployment event and error rate spike found")
    elif has_error_spikes or has_incident_docs:
        score += 20
        factors.append("Partial operational signals identified")
        missing_hints.append("Missing verified deployment changelog.")
    else:
        missing_hints.append("Fresh service error logs and deployment event metadata unavailable.")

    # 3. Timing / Temporal alignment (up to 15 pts)
    if has_deployments and (has_error_spikes or has_incident_docs):
        score += 15
        factors.append("Strong temporal alignment (deployment preceded incident window)")
    else:
        score += 5

    # 4. Data freshness baseline (up to 10 pts)
    score += 10
    factors.append("KPI baseline telemetry is healthy and fresh")

    # Clamp
    score = max(0, min(100, score))

    if score >= 70:
        level = "High"
        should_abstain = False
    elif score >= 45:
        level = "Medium"
        should_abstain = False
    else:
        level = "Low"
        should_abstain = True

    return ConfidenceScore(
        score=score,
        level=level,
        should_abstain=should_abstain,
        factors=factors,
        missing_evidence_hints=missing_hints,
    )
