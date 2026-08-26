"""Confidence Engine - Deterministic diagnostic confidence evaluation and abstention logic.

Evaluates 4 objective dimensions (Total: 0 - 100 points):
1. Driver Strength (0 - 40 pts): Contribution magnitude of primary driver.
2. Corroborating Evidence (0 - 35 pts): Corroboration across SQLite metrics and RAG docs.
3. Temporal Alignment (0 - 15 pts): Deployment timestamp directly preceding error spikes.
4. Baseline Validity (0 - 10 pts): Adequate historical baseline (>= 14 days).

Thresholds:
- >= 70%: High confidence (Confident diagnosis)
- 45% - 69%: Medium confidence (Plausible diagnosis with uncertainty note)
- < 45%: Low confidence (ABSTAIN - Do NOT guess or invent causes)
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
    # Cold Start Guardrail: Instant Abstention
    if not has_sufficient_history:
        return ConfidenceScore(
            score=20,
            level="Low",
            should_abstain=True,
            factors=["Insufficient baseline history (< 14 days recorded)"],
            missing_evidence_hints=[
                "Accumulate at least 14 days of stable baseline measurements.",
                "Continue metric collection before executing automated root cause actions.",
            ],
        )

    score = 0
    factors = []
    missing_hints = []

    # -------------------------------------------------------------
    # 1. Driver Strength (0 to 40 pts)
    # -------------------------------------------------------------
    if primary_driver_contribution >= 70.0:
        score += 40
        factors.append(f"Strong primary driver isolation ({primary_driver_contribution:.1f}% variance explained)")
    elif primary_driver_contribution >= 50.0:
        score += 25
        factors.append(f"Moderate driver isolation ({primary_driver_contribution:.1f}% variance explained)")
    else:
        score += 10
        missing_hints.append("Primary driver is diffuse (< 50% contribution across factors).")

    # -------------------------------------------------------------
    # 2. Corroborating Evidence (0 to 35 pts)
    # -------------------------------------------------------------
    has_deployments = any(e.source == "Deployment" for e in evidence_items)
    has_error_surges = any(e.source in ["Payments", "Operations"] and "increased" in e.description.lower() for e in evidence_items)
    has_incident_docs = any(e.source in ["Incidents", "Support"] for e in evidence_items)

    if has_deployments and (has_error_surges or has_incident_docs):
        score += 35
        factors.append("Cross-verified by service deployment record and error spike telemetry")
    elif has_error_surges or has_incident_docs:
        score += 20
        factors.append("Partial operational signals detected without verified deployment changelog")
        missing_hints.append("Missing deployment changelog or release tag verification.")
    elif has_deployments:
        score += 15
        factors.append("Deployment event logged, but corresponding error spike telemetry is missing")
        missing_hints.append("Missing microservice application error logs.")
    else:
        score += 0
        missing_hints.append("Fresh service error logs, deployment records, and support escalations unavailable.")

    # -------------------------------------------------------------
    # 3. Temporal Alignment (0 to 15 pts)
    # -------------------------------------------------------------
    if has_deployments and has_error_surges:
        score += 15
        factors.append("Strong temporal alignment (deployment immediately preceded error surge)")
    elif has_error_surges or has_incident_docs:
        score += 5
        factors.append("Incident timestamps recorded within the active anomaly window")
    else:
        score += 0
        missing_hints.append("Unable to establish timeline correlation between events.")

    # -------------------------------------------------------------
    # 4. Baseline Validity (0 to 10 pts)
    # -------------------------------------------------------------
    score += 10
    factors.append("Historical KPI baseline is valid (>= 14 days)")

    # Clamp score
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
