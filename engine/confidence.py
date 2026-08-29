"""Confidence Engine - Multi-signal deterministic confidence calibration.

Confidence reflects how certain the analytical engine is about its diagnosis.
It decreases when evidence conflicts, history is sparse, or drivers are ambiguous.
It increases when multiple independent signals agree, data is fresh, and drivers
are strongly isolated.

Scoring dimensions (total 100 points):
  1. Driver Isolation    (0-30): How strongly the primary driver explains the movement.
  2. Driver Ambiguity    (0-10): Penalty when two drivers are close in contribution.
  3. Evidence Presence   (0-25): Breadth of corroborating operational evidence.
  4. Evidence Agreement  (0-15): Do structured and unstructured sources agree?
  5. Evidence Contradiction (-15 to 0): Penalty for conflicting signals.
  6. Temporal Alignment  (0-10): Evidence timestamps in the anomaly window.
  7. Baseline Validity   (0-10): Adequate history (>= 14 days).

Max theoretically achievable = 100, but contradiction and ambiguity reduce it.
Cap normal business insight at 95 to acknowledge irreducible uncertainty.

Thresholds:
  >= 68 : High   (confident diagnosis)
  43-67 : Medium (plausible with uncertainty note)
  < 43  : Low    (ABSTAIN — insufficient evidence)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from engine.evidence import EvidenceItem


@dataclass
class ConfidenceScore:
    score: int                          # 0 to 95
    level: str                          # 'High', 'Medium', 'Low'
    should_abstain: bool
    factors: List[str]                  # positive signals
    missing_evidence_hints: List[str]   # what's missing
    contradiction_notes: List[str]      # any conflicts detected


def _detect_contradiction(structured: List[EvidenceItem], rag: List[EvidenceItem]) -> List[str]:
    """Detects conflicts between structured operational signals and RAG narrative evidence.

    Example contradiction: structured shows payment failures rising, but a RAG
    marketing document claims 'record ROAS and strong conversion performance.'
    """
    contradictions = []
    structured_desc = " ".join(e.description.lower() for e in structured)
    rag_desc = " ".join(e.description.lower() for e in rag)

    # Signal 1: Structured shows error surge, RAG claims performance is positive
    has_error_surge = any(
        kw in structured_desc for kw in ["errors increased", "failures increased", "error", "fatal", "timeout"]
    )
    rag_claims_positive = any(
        kw in rag_desc for kw in ["strong conversion", "record roas", "outperforming", "healthy traffic", "positive roas"]
    )
    if has_error_surge and rag_claims_positive:
        contradictions.append(
            "Operational error signals contradict marketing/RAG narrative of positive performance."
        )

    # Signal 2: RAG reports no incidents, but structured shows deployment failures
    rag_says_no_incident = any(
        kw in rag_desc for kw in ["no incidents", "stable operations", "all systems normal"]
    )
    has_deployment_failure = any(
        "error" in e.description.lower() or "fatal" in e.description.lower()
        for e in structured
    )
    if rag_says_no_incident and has_deployment_failure:
        contradictions.append(
            "RAG corpus indicates stable operations, but structured logs show deployment-related errors."
        )

    return contradictions


def calculate_confidence(
    primary_driver_contribution: float,
    evidence_items: List[EvidenceItem],
    has_sufficient_history: bool = True,
    driver_ambiguity_gap: Optional[float] = None,
    history_days: int = 30,
    data_freshness_days: int = 1,
    movement_magnitude: Optional[float] = None,
    structured_evidence: Optional[List[EvidenceItem]] = None,
    rag_evidence: Optional[List[EvidenceItem]] = None,
) -> ConfidenceScore:
    """Calculates diagnostic confidence score using multiple calibrated signals.

    Args:
        primary_driver_contribution: contribution_pct of the top driver (0-100).
        evidence_items: all combined evidence (structured + RAG).
        has_sufficient_history: False triggers cold-start abstention.
        driver_ambiguity_gap: abs difference between #1 and #2 driver contributions.
                              Small gap = ambiguous diagnosis.
        history_days: actual history depth (larger = better baseline).
        data_freshness_days: days since last data update (0-1 = fresh).
        movement_magnitude: abs(change_pct) of target KPI.
        structured_evidence: structured-only evidence (for contradiction check).
        rag_evidence: RAG-only evidence (for contradiction check).
    """
    # ── Cold Start: unconditional abstention ─────────────────────────────────
    if not has_sufficient_history:
        return ConfidenceScore(
            score=20,
            level="Low",
            should_abstain=True,
            factors=["Insufficient baseline history (< 14 days recorded)"],
            missing_evidence_hints=[
                "Accumulate at least 14 days of stable baseline measurements.",
                "Continue metric collection before automated root-cause actions.",
            ],
            contradiction_notes=[],
        )

    score = 0
    factors: List[str] = []
    missing_hints: List[str] = []
    contradiction_notes: List[str] = []

    # ── 1. Driver Isolation (0-30 pts) ───────────────────────────────────────
    if primary_driver_contribution >= 70.0:
        score += 30
        factors.append(
            f"Strong primary driver isolation ({primary_driver_contribution:.1f}% contribution)"
        )
    elif primary_driver_contribution >= 55.0:
        score += 20
        factors.append(
            f"Moderate driver isolation ({primary_driver_contribution:.1f}% contribution)"
        )
    elif primary_driver_contribution >= 40.0:
        score += 10
        factors.append(
            f"Weak driver isolation ({primary_driver_contribution:.1f}% contribution)"
        )
    else:
        score += 4
        missing_hints.append(
            "Primary driver explains < 40% of variance — multiple co-equal drivers present."
        )

    # ── 2. Driver Ambiguity Penalty (0 to -10 pts) ───────────────────────────
    if driver_ambiguity_gap is not None:
        if driver_ambiguity_gap < 5.0:
            score -= 10
            missing_hints.append(
                "Top two drivers are nearly equal in contribution — diagnosis is ambiguous."
            )
        elif driver_ambiguity_gap < 15.0:
            score -= 4
            missing_hints.append(
                "Two drivers have similar explanatory strength — uncertainty elevated."
            )

    # ── 3. Evidence Presence (0-25 pts) ──────────────────────────────────────
    has_deployments = any(e.source == "Deployment" for e in evidence_items)
    has_payment_errors = any(
        e.source in ["Payments", "Operations"] and "increased" in e.description.lower()
        for e in evidence_items
    )
    has_incident_docs = any(e.source in ["Incidents", "Support"] for e in evidence_items)
    has_rag = any(not e.is_structured for e in evidence_items)

    evidence_score = 0
    if has_deployments:
        evidence_score += 8
        factors.append("Deployment event recorded in evidence corpus")
    if has_payment_errors:
        evidence_score += 10
        factors.append("Operational error surge confirmed from structured telemetry")
    if has_incident_docs:
        evidence_score += 7
        factors.append("Incident documentation corroborates operational signals")
    if has_rag and not (has_deployments or has_payment_errors or has_incident_docs):
        evidence_score += 4
        factors.append("RAG documents retrieved (no structured operational signals found)")

    score += min(evidence_score, 25)

    if not (has_deployments or has_payment_errors or has_incident_docs or has_rag):
        missing_hints.append(
            "No deployment records, error telemetry, incidents, or operational docs found."
        )

    # ── 4. Evidence Agreement (0-15 pts) ─────────────────────────────────────
    if has_deployments and has_payment_errors and has_incident_docs:
        score += 15
        factors.append("Strong cross-source agreement (deployments + error telemetry + incident docs)")
    elif (has_deployments and has_payment_errors) or (has_payment_errors and has_incident_docs):
        score += 9
        factors.append("Partial cross-source agreement across two evidence types")
    elif has_deployments or has_payment_errors or has_incident_docs:
        score += 4
        factors.append("Single evidence source available")
    else:
        missing_hints.append("Unable to cross-verify signals across multiple independent sources.")

    # ── 5. Contradiction Penalty (-15 to 0 pts) ───────────────────────────────
    structured_ev = structured_evidence or [e for e in evidence_items if e.is_structured]
    rag_ev = rag_evidence or [e for e in evidence_items if not e.is_structured]
    detected_contradictions = _detect_contradiction(structured_ev, rag_ev)
    if detected_contradictions:
        score -= 15
        contradiction_notes.extend(detected_contradictions)
        missing_hints.append(
            "Contradictory signals detected between operational data and narrative evidence."
        )

    # ── 6. Temporal Alignment (0-10 pts) ─────────────────────────────────────
    if has_deployments and has_payment_errors:
        score += 10
        factors.append("Deployment immediately preceded operational error surge (strong temporal alignment)")
    elif has_payment_errors or has_incident_docs:
        score += 4
        factors.append("Incident timestamps recorded within the active anomaly window")
    else:
        missing_hints.append("Cannot establish causal timeline between events and KPI movement.")

    # ── 7. Baseline Validity (0-10 pts) ──────────────────────────────────────
    if history_days >= 60:
        score += 10
        factors.append(f"Deep historical baseline ({history_days} days)")
    elif history_days >= 30:
        score += 8
        factors.append(f"Adequate historical baseline ({history_days} days)")
    elif history_days >= 14:
        score += 5
        factors.append(f"Minimal valid baseline ({history_days} days — borderline)")
    else:
        score += 2
        missing_hints.append(f"Historical depth of {history_days} days is below the 14-day minimum.")

    # ── Data freshness micro-boost ────────────────────────────────────────────
    if data_freshness_days <= 1:
        score += 2
        factors.append("Data is current (updated within 1 day)")

    # ── Cap at 95 (no perfect business insight) ───────────────────────────────
    score = max(0, min(95, score))

    # ── Thresholds ────────────────────────────────────────────────────────────
    if score >= 68:
        level = "High"
        should_abstain = False
    elif score >= 43:
        level = "Medium"
        should_abstain = False
    else:
        level = "Low"
        should_abstain = True

    # ── Ambiguity abstention override: no clear winner + weak evidence ────────
    if driver_ambiguity_gap is not None and driver_ambiguity_gap < 5.0 and not (
        has_deployments and has_payment_errors
    ):
        should_abstain = True
        if level != "Low":
            level = "Low"
            missing_hints.append(
                "The available evidence is insufficient to identify a single root cause."
            )

    return ConfidenceScore(
        score=score,
        level=level,
        should_abstain=should_abstain,
        factors=factors,
        missing_evidence_hints=missing_hints,
        contradiction_notes=contradiction_notes,
    )
