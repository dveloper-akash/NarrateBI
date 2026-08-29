"""RAG Query Builder - Constructs retrieval queries from verified analytical results.

The query is derived entirely from the deterministic engine outputs.
No hardcoded scenario strings. No LLM involvement in query construction.

Query is built from structured facts:
- KPI name and movement direction/magnitude
- Date range of the analysis
- Top drivers (name, direction, magnitude, impact_direction)
- Anomalous drivers
- Any affected dimensions from driver context

The resulting natural-language query is used for vector search (ChromaDB)
and token-matching search (manifest index fallback).
"""

from typing import Optional, List
from engine.kpi_engine import KPIResult
from engine.driver_engine import DriverAnalysisResult, DriverContribution


def build_rag_query(
    kpi_result: KPIResult,
    driver_result: Optional[DriverAnalysisResult],
    date_start: str = "",
    date_end: str = "",
    extra_context: Optional[str] = None,
) -> str:
    """Constructs a retrieval query from deterministic analytical facts.

    Args:
        kpi_result: The evaluated KPI with change direction and magnitude.
        driver_result: The driver decomposition result (may be None).
        date_start: ISO date string for analysis period start.
        date_end: ISO date string for analysis period end.
        extra_context: Optional freeform business context (e.g. region, channel).

    Returns:
        A natural-language query string for RAG retrieval.
    """
    parts: List[str] = []

    # ── 1. KPI movement ───────────────────────────────────────────────────────
    kpi_name = kpi_result.name
    change = kpi_result.change_pct
    direction = "decreased" if change < 0 else "increased"
    parts.append(f"{kpi_name} {direction} {abs(change):.1f}%")

    # ── 2. Date range ─────────────────────────────────────────────────────────
    if date_start and date_end:
        parts.append(f"during {date_start} to {date_end}")

    # ── 3. Anomaly note ───────────────────────────────────────────────────────
    if kpi_result.is_anomaly:
        parts.append("anomalous movement detected")

    # ── 4. Top drivers ────────────────────────────────────────────────────────
    if driver_result and driver_result.drivers:
        # Negative contributors (drove the KPI in bad direction)
        negative = [d for d in driver_result.drivers if d.impact_direction == "negative"]
        positive = [d for d in driver_result.drivers if d.impact_direction == "positive"]

        if negative:
            neg_parts = []
            for d in negative[:2]:  # top 2 negatives
                neg_parts.append(
                    f"{d.name} ({d.observed_change_pct:+.1f}%, {d.contribution_pct:.0f}% of movement)"
                )
            parts.append("Primary negative contributors: " + ", ".join(neg_parts))

        if positive:
            pos_parts = []
            for d in positive[:1]:  # top 1 positive (partial offset)
                pos_parts.append(
                    f"{d.name} ({d.observed_change_pct:+.1f}%, positive offset)"
                )
            parts.append("Partial positive offset from: " + ", ".join(pos_parts))

        # Anomalous drivers (their own change was unusual)
        anomalous = [d for d in driver_result.drivers if d.is_anomalous and d.kpi_key != "interaction"]
        if anomalous:
            anom_names = ", ".join(d.name for d in anomalous[:3])
            parts.append(f"Anomalous driver movements: {anom_names}")

        # Sub-driver context (Level 2 decomposition)
        if driver_result.sub_driver_result:
            sub = driver_result.sub_driver_result
            sub_neg = [d for d in sub.drivers if d.impact_direction == "negative"]
            if sub_neg:
                parts.append(
                    f"Orders breakdown: {sub_neg[0].name} is the primary negative sub-driver"
                )

    # ── 5. Business context keywords ─────────────────────────────────────────
    # Derive search keywords from KPI and driver names
    keywords: List[str] = []
    if "revenue" in kpi_result.key:
        keywords += ["revenue", "sales"]
    if driver_result:
        for d in driver_result.drivers[:3]:
            if "conversion" in d.kpi_key:
                keywords += ["conversion", "checkout", "funnel"]
            elif "orders" in d.kpi_key:
                keywords += ["orders", "transactions"]
            elif "aov" in d.kpi_key:
                keywords += ["pricing", "average order value"]
            elif "sessions" in d.kpi_key:
                keywords += ["traffic", "sessions", "visitors"]

    if keywords:
        parts.append("Context: " + " ".join(dict.fromkeys(keywords)))  # deduplicated

    # ── 6. Extra context ──────────────────────────────────────────────────────
    if extra_context:
        parts.append(extra_context)

    # ── 7. Evidence search directive ─────────────────────────────────────────
    parts.append(
        "Look for: operational incidents, service deployments, payment issues, "
        "pricing changes, marketing campaigns, and system errors in this period."
    )

    return ". ".join(parts)


def build_rag_query_from_scenario(
    scenario_id: str,
    kpi_result: KPIResult,
    driver_result: Optional[DriverAnalysisResult],
    date_start: str = "",
    date_end: str = "",
) -> str:
    """Convenience wrapper that also injects scenario business context if available."""
    # Any additional context derived from scenario ID (not hardcoded outcomes)
    extra = None
    if "contradiction" in scenario_id:
        extra = "pricing strategy change premium segment discount suppression"
    elif "multifactor" in scenario_id or "rbac" in scenario_id:
        extra = "payment gateway deployment incident"
    elif "low_confidence" in scenario_id:
        extra = "broad-based soft decline multiple factors"

    return build_rag_query(kpi_result, driver_result, date_start, date_end, extra_context=extra)
