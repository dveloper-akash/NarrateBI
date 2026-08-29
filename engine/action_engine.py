"""Action Recommendation Engine — Deterministic, Evidence-Grounded Action Provider.

Produces structured action recommendations following the hackathon's required format:
  driver → controllable lever → action → expected impact → owner → confidence → monitoring plan

Design principles:
- 100% deterministic: actions are derived from verified DriverContribution and EvidenceItem signals.
- LLM is NOT the source of action logic. The LLM can enrich phrasing, but the structure comes here.
- Persona-aware: Executive sees strategic levers; Engineer sees technical runbooks.
- Confidence-gated: Low-confidence scenarios produce monitoring-only actions, not intervention.
- Evidence-anchored: Each action cites the evidence signals that justify it.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from engine.driver_engine import DriverAnalysisResult, DriverContribution
from engine.evidence import EvidenceItem
from engine.confidence import ConfidenceScore


# ─────────────────────────────────────────────────────────────────────────────
# Data Contract
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActionRecommendation:
    """Structured action record following the hackathon's required format."""
    rank: int                        # Priority rank (1 = highest)
    driver: str                      # Which KPI driver triggered this action
    controllable_lever: str          # Business/technical lever that can be pulled
    action: str                      # Specific action description
    expected_impact: str             # Quantified or directional impact estimate
    owner: str                       # Who is responsible (role-based)
    owner_role: str                  # 'Executive' | 'Engineer' | 'Both'
    confidence: str                  # 'High' | 'Medium' | 'Low'
    confidence_rationale: str        # Why this confidence level was assigned
    monitoring_plan: str             # How to verify the action had effect
    evidence_citations: List[str]    # Which evidence items support this action
    action_type: str                 # 'immediate' | 'short_term' | 'strategic' | 'investigate'
    urgency: str                     # 'Critical' | 'High' | 'Medium' | 'Low'


@dataclass
class ActionPlan:
    """Complete action plan for a KPI movement, returned to the UI."""
    target_kpi: str
    target_change_pct: float
    scenario_id: str
    persona: str
    actions: List[ActionRecommendation]
    abstain_reason: Optional[str] = None   # Set when confidence is too low to act
    methodology_note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_evidence_desc(items: List[EvidenceItem]) -> List[str]:
    """Returns human-readable evidence strings for citation."""
    return [f"[{e.source}] {e.description}" for e in items]


def _confidence_from_driver(driver: DriverContribution, overall: ConfidenceScore) -> str:
    """Maps driver isolation strength + overall confidence into action confidence."""
    if driver.contribution_pct >= 60 and overall.score >= 68:
        return "High"
    elif driver.contribution_pct >= 40 and overall.score >= 43:
        return "Medium"
    return "Low"


def _urgency_from_driver(driver: DriverContribution, change_pct: float) -> str:
    """Determines urgency based on driver impact magnitude."""
    magnitude = abs(driver.contribution_to_target)
    abs_change = abs(change_pct)
    if abs_change >= 20 and driver.contribution_pct >= 50:
        return "Critical"
    elif abs_change >= 10 or driver.contribution_pct >= 40:
        return "High"
    elif abs_change >= 5:
        return "Medium"
    return "Low"


# ─────────────────────────────────────────────────────────────────────────────
# Persona-Specific Action Templates
# Maps driver key → levers and actions for each persona
# ─────────────────────────────────────────────────────────────────────────────

_EXECUTIVE_ACTIONS: Dict[str, Dict[str, Any]] = {
    "orders": {
        "negative": {
            "lever": "Demand Stimulation / Conversion Recovery",
            "action": "Authorize a targeted 3-7 day demand recovery campaign: activate email re-engagement for abandoned carts, enable time-limited promotional pricing on top 5 SKUs, and brief sales leadership on volume recovery targets.",
            "impact": "Expected to recover 40-60% of lost order volume within 5-7 business days based on historical campaign benchmarks.",
            "owner": "Chief Commercial Officer / VP Sales",
            "monitoring_plan": "Track daily order count vs. prior 7-day moving average. Escalate if recovery < 20% within 48 hours of campaign launch.",
            "action_type": "immediate",
        },
        "positive": {
            "lever": "Volume Scale-Up / Capacity Planning",
            "action": "Review fulfilment capacity and supply chain readiness to sustain elevated order volumes. Confirm warehouse, logistics, and customer service headcount are scaled to match demand.",
            "impact": "Prevents service degradation and prevents lost revenue from fulfilment failures during high-demand periods.",
            "owner": "Chief Operations Officer / Head of Supply Chain",
            "monitoring_plan": "Monitor order-to-shipment SLA, fulfilment error rate, and customer satisfaction scores daily.",
            "action_type": "short_term",
        },
    },
    "conversion_rate": {
        "negative": {
            "lever": "Checkout Funnel Optimization / UX Recovery",
            "action": "Immediately audit checkout funnel drop-off rates by step. Commission emergency UX review of payment flow. Evaluate A/B test of simplified one-click checkout. If a recent release is correlated, authorise a product rollback decision with Engineering within 4 hours.",
            "impact": "A 5% improvement in checkout completion restores approximately {driver_contrib:.0f}% of lost revenue based on current order volume.",
            "owner": "Chief Product Officer / VP Digital Commerce",
            "monitoring_plan": "Monitor hourly checkout funnel completion rate and payment success rate. Trigger P1 incident if conversion drops further >2% in next 6 hours.",
            "action_type": "immediate",
        },
        "positive": {
            "lever": "Conversion Experience Scaling",
            "action": "Identify which UX, pricing, or campaign changes drove the conversion improvement. Document winning experiment results and plan rollout to additional audience segments or markets.",
            "impact": "Sustaining or growing the conversion gain will compound revenue impact over the next 30-60 days.",
            "owner": "Chief Product Officer / Head of Growth",
            "monitoring_plan": "Track conversion rate weekly and A/B test continuation of winning experiments.",
            "action_type": "short_term",
        },
    },
    "aov": {
        "negative": {
            "lever": "Pricing & Basket Value Recovery",
            "action": "Review recent pricing changes, discount mechanics, and promotional rules. Assess whether current promotional depth is eroding basket value. Brief Revenue Management on sustainable pricing guardrails.",
            "impact": "A 1% improvement in AOV directly lifts revenue proportionally to current order volume.",
            "owner": "Chief Revenue Officer / VP Pricing",
            "monitoring_plan": "Track AOV daily by product category and channel. Set alert threshold at AOV < 95% of 30-day baseline.",
            "action_type": "short_term",
        },
        "positive": {
            "lever": "Premium Mix Expansion",
            "action": "Analyse product mix shift driving AOV uplift. Consider expanding premium product placement, bundling strategies, or upsell prompts across the purchase funnel.",
            "impact": "Sustained AOV improvement of this magnitude compounds revenue growth without requiring volume gains.",
            "owner": "Chief Commercial Officer / VP Merchandising",
            "monitoring_plan": "Monitor AOV weekly alongside category mix, average units per transaction, and bundle attach rate.",
            "action_type": "strategic",
        },
    },
    "sessions": {
        "negative": {
            "lever": "Traffic Acquisition Recovery",
            "action": "Review paid media spend, organic search ranking changes, and any infrastructure issues affecting page load speed. Coordinate with Marketing to activate emergency media reallocation if traffic decline is channel-specific.",
            "impact": "Recovering session volume restores the top-of-funnel capacity required to hit revenue targets.",
            "owner": "Chief Marketing Officer / Head of Performance Marketing",
            "monitoring_plan": "Monitor daily sessions by channel (organic, paid, direct, email). Flag declines > 10% vs. 7-day average.",
            "action_type": "immediate",
        },
        "positive": {
            "lever": "Traffic Monetisation Optimisation",
            "action": "Ensure landing page conversion rate is optimised to capture elevated traffic. Confirm inventory availability and pricing competitiveness on high-traffic pages.",
            "impact": "Increased sessions with stable conversion rate directly lifts order volume and revenue.",
            "owner": "Chief Marketing Officer / VP Digital",
            "monitoring_plan": "Track sessions-to-orders conversion ratio daily to confirm traffic quality is maintained.",
            "action_type": "short_term",
        },
    },
}

_ENGINEER_ACTIONS: Dict[str, Dict[str, Any]] = {
    "orders": {
        "negative": {
            "lever": "Order Processing Pipeline Reliability",
            "action": "1. Query order_service error logs for 5xx rate vs. baseline (threshold: >1%). "
                      "2. Check database connection pool saturation on order-db replica. "
                      "3. Verify payment-service queue depth and consumer lag (>500ms p99 = incident). "
                      "4. Run order reconciliation job to detect silent drop-offs between cart and confirmation.",
            "impact": "Restoring order pipeline reliability is expected to recover >80% of lost order count within 1 service deployment cycle.",
            "owner": "SRE Lead / Backend Engineering",
            "monitoring_plan": "Alert on: order_service 5xx rate > 0.5%, p95 checkout latency > 2s, payment-service error rate > 2%. Review within 1 hour of each deploy.",
            "action_type": "immediate",
        },
        "positive": {
            "lever": "Capacity Validation",
            "action": "Validate autoscaling policies on order-service and payment-service to ensure elevated throughput is sustained without latency degradation. Review DB replica read distribution.",
            "impact": "Proactive capacity validation prevents service degradation during sustained order volume spikes.",
            "owner": "SRE / Platform Engineering",
            "monitoring_plan": "Monitor p99 order processing latency and DB CPU utilisation. Set alert if p99 > 1.8s.",
            "action_type": "short_term",
        },
    },
    "conversion_rate": {
        "negative": {
            "lever": "Checkout Service Rollback / Hotfix",
            "action": "1. Cross-reference deployment changelog with conversion rate drop timestamp. "
                      "2. If correlated (within 2hr window), initiate emergency rollback via CI/CD pipeline. "
                      "3. Capture checkout funnel step-level error rates from payment_data table. "
                      "4. Check SSL certificate validity, 3DS auth redirect timeouts, and payment gateway health endpoint. "
                      "5. Enable feature flag kill-switch for any new checkout flow variant.",
            "impact": "A confirmed rollback to last known-good build typically restores conversion baseline within 15-30 minutes.",
            "owner": "On-call SRE / Checkout Engineering Lead",
            "monitoring_plan": "Real-time monitor: checkout_errors/hr (alert > 150/hr), payment_failure_rate (alert > 3%), conversion_rate p5m (alert < -5% vs. 30min rolling avg).",
            "action_type": "immediate",
        },
        "positive": {
            "lever": "Performance Baseline Lock-In",
            "action": "Capture the winning configuration (feature flags, AB variant IDs, CDN cache rules) as a named release artifact. Run load test to confirm performance holds at 2x current session volume before promoting to stable.",
            "impact": "Prevents regression of conversion gains in future deployments.",
            "owner": "Platform Engineering / QA Lead",
            "monitoring_plan": "Pin conversion rate regression tests in CI pipeline. Fail build if staging conversion rate drops >3% vs. baseline.",
            "action_type": "short_term",
        },
    },
    "aov": {
        "negative": {
            "lever": "Pricing Engine / Discount Rule Audit",
            "action": "1. Check pricing_service config for recent rule changes (discount stacking, coupon logic). "
                      "2. Validate that promotional price overrides are scoped to intended SKU segments. "
                      "3. Review cart-service item composition logs to detect unexpected product substitutions or bundle failures. "
                      "4. Confirm currency conversion rates if multi-currency is enabled.",
            "impact": "Pricing engine misconfiguration corrections typically restore AOV within 1 deployment cycle.",
            "owner": "Backend Engineering / Pricing Service Team",
            "monitoring_plan": "Alert on: AOV moving average dropping >5% in 4hr window, cart item count anomalies, discount application rate >20%.",
            "action_type": "investigate",
        },
        "positive": {
            "lever": "Recommendation Engine Performance Validation",
            "action": "Verify that upsell/cross-sell recommendation service is functioning correctly and is not creating ghost-orders. Confirm that higher AOV reflects genuine customer intent and not data pipeline double-counting.",
            "impact": "Validates that AOV gain is real, preventing false dashboard metrics from misguiding business decisions.",
            "owner": "Data Engineering / Recommendations Team",
            "monitoring_plan": "Audit order item counts, AOV distribution, and recommendation click-through rates for anomalies.",
            "action_type": "investigate",
        },
    },
    "sessions": {
        "negative": {
            "lever": "Traffic Infrastructure & CDN Audit",
            "action": "1. Check CDN edge cache hit rates and origin pull latency spikes. "
                      "2. Review web_analytics ingestion pipeline for sampling configuration changes (common source of phantom session drop). "
                      "3. Inspect DNS TTL propagation after any recent infrastructure changes. "
                      "4. Validate bot-filtering rules have not over-aggressively excluded legitimate traffic.",
            "impact": "Infrastructure fixes resolve measurement or delivery issues affecting session counts within 1-2 hours.",
            "owner": "Platform Engineering / Infrastructure SRE",
            "monitoring_plan": "Monitor CDN cache hit rate, origin error rate, and session count from multiple analytics sources in parallel to detect discrepancies.",
            "action_type": "investigate",
        },
        "positive": {
            "lever": "Infrastructure Capacity Readiness",
            "action": "Confirm autoscaling policies on frontend servers and CDN bandwidth limits are configured to handle sustained traffic volume. Review database read replica scaling.",
            "impact": "Prevents revenue loss from infrastructure bottlenecks during traffic spikes.",
            "owner": "Platform Engineering / Infrastructure SRE",
            "monitoring_plan": "Monitor p99 page load time, CDN bandwidth utilisation, and web server CPU every 15 minutes during elevated traffic.",
            "action_type": "short_term",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Low-Confidence / Investigation Actions
# ─────────────────────────────────────────────────────────────────────────────

_INVESTIGATE_ACTIONS = {
    "executive": ActionRecommendation(
        rank=1,
        driver="Multiple Co-Equal Drivers",
        controllable_lever="Evidence Collection",
        action="Request a 24-hour diagnostic report from Engineering and Analytics teams. Do not take operational action on this KPI until root cause is isolated — premature interventions risk compounding the problem.",
        expected_impact="Accurate root-cause identification prevents wasted spend on the wrong lever and reduces time-to-recovery.",
        owner="Chief Analytics Officer / Head of Business Intelligence",
        owner_role="Executive",
        confidence="Low",
        confidence_rationale="Diagnostic confidence is below 43% — insufficient evidence to single out a primary driver.",
        monitoring_plan="Continue monitoring hourly KPI snapshots. Brief leadership if KPI delta widens further before root cause is confirmed.",
        evidence_citations=["Insufficient operational evidence to confirm a single root cause."],
        action_type="investigate",
        urgency="High",
    ),
    "engineer": ActionRecommendation(
        rank=1,
        driver="Ambiguous Driver — Investigation Required",
        controllable_lever="Structured Diagnostic Runbook",
        action="Execute diagnostic runbook: (1) Compare error rates across all dependent microservices for the anomaly window. "
               "(2) Pull deployment changelog for the past 72 hours. "
               "(3) Query payment_data and system_logs tables for correlated spikes. "
               "(4) Check data pipeline freshness — stale data may create false anomalies. "
               "(5) Report findings to BI team within 4 hours.",
        expected_impact="Structured investigation will isolate root cause within 4 hours, enabling targeted remediation.",
        owner="On-call SRE / Data Engineering Lead",
        owner_role="Engineer",
        confidence="Low",
        confidence_rationale="Driver ambiguity gap < 5% — multiple co-equal contributors cannot be distinguished without additional operational signals.",
        monitoring_plan="Set up real-time alerts on all dependent KPIs (conversion_rate, orders, sessions, aov) until root cause confirmed.",
        evidence_citations=["Multiple drivers show similar contribution — no single primary cause identified."],
        action_type="investigate",
        urgency="High",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Deployment-Specific Actions (Evidence-Triggered)
# ─────────────────────────────────────────────────────────────────────────────

def _build_deployment_action(persona: str, evidence: List[EvidenceItem]) -> Optional[ActionRecommendation]:
    """Generates a deployment-triggered action when deployment evidence is present."""
    dep_items = [e for e in evidence if e.evidence_type == "deployment"]
    error_items = [e for e in evidence if e.evidence_type == "error_surge"]
    if not dep_items:
        return None

    citations = _extract_evidence_desc(dep_items + error_items[:2])
    services = list({e.affected_entity for e in dep_items})
    service_str = ", ".join(services[:3])

    if persona == "engineer":
        return ActionRecommendation(
            rank=1,  # Will be re-ranked after merging
            driver="Deployment Event",
            controllable_lever="Deployment Rollback / Hotfix Pipeline",
            action=(
                f"DEPLOYMENT ALERT: {service_str} deployment detected in the anomaly window. "
                "Immediate steps: (1) Compare KPI timeline vs. deploy timestamp. "
                "(2) If correlated within 2 hours: initiate rollback via CI/CD pipeline. "
                "(3) If rollback is risky: deploy forward with hotfix and feature-flag disable. "
                "(4) Escalate to on-call lead if payment error rate > 3% or checkout errors > 200/hr. "
                "(5) Capture incident in post-mortem template within 24 hours."
            ),
            expected_impact="Rollback to last stable build typically restores KPI baseline within 15-45 minutes.",
            owner="On-call SRE / Release Engineering",
            owner_role="Engineer",
            confidence="High",
            confidence_rationale="Deployment event timestamp correlates with KPI decline window — strong causal signal.",
            monitoring_plan=(
                "Monitor: payment_failure_rate (<1%), checkout_errors/hr (<100), p99 checkout latency (<1.5s), "
                "conversion_rate vs. 30-min rolling average. Alert engineering if metrics don't recover within 30 min of rollback."
            ),
            evidence_citations=citations,
            action_type="immediate",
            urgency="Critical",
        )
    else:
        return ActionRecommendation(
            rank=1,
            driver="Deployment Event",
            controllable_lever="Release Management Decision",
            action=(
                f"A {service_str} service deployment coincided with the KPI decline. "
                "Authorise Engineering to evaluate rollback vs. forward-fix. "
                "Invoke Change Advisory Board (CAB) process if rollback affects more than 3 services. "
                "Set 2-hour recovery SLA for Engineering team."
            ),
            expected_impact="Deployment rollback typically restores revenue run-rate within 1-2 hours, minimising financial exposure.",
            owner="VP Engineering / Director of SRE",
            owner_role="Executive",
            confidence="High",
            confidence_rationale="Deployment event is temporally correlated with KPI anomaly.",
            monitoring_plan="Review hourly revenue and order volume vs. pre-deployment baseline. Escalate if no recovery in 2 hours.",
            evidence_citations=citations,
            action_type="immediate",
            urgency="Critical",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main Action Generation Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_action_plan(
    target_kpi_key: str,
    target_kpi_name: str,
    target_change_pct: float,
    driver_result: Optional[DriverAnalysisResult],
    evidence: List[EvidenceItem],
    confidence_result: ConfidenceScore,
    persona: str = "executive",
    scenario_id: str = "",
) -> ActionPlan:
    """Generates a structured, evidence-grounded action plan.

    Args:
        target_kpi_key:   Key of the primary KPI being analysed (e.g. 'revenue').
        target_kpi_name:  Display name (e.g. 'Revenue').
        target_change_pct: Percentage change of target KPI.
        driver_result:    Output of the driver decomposition engine.
        evidence:         All combined evidence items (structured + RAG).
        confidence_result: Output of the confidence scoring engine.
        persona:          'executive' | 'engineer'.
        scenario_id:      Scenario ID for context.

    Returns:
        ActionPlan with ranked, structured recommendations.
    """
    persona_key = persona.lower()
    actions: List[ActionRecommendation] = []

    # ── Case 1: Abstention — insufficient confidence ───────────────────────
    if confidence_result.should_abstain:
        abstain_action = _INVESTIGATE_ACTIONS.get(persona_key, _INVESTIGATE_ACTIONS["executive"])
        return ActionPlan(
            target_kpi=target_kpi_name,
            target_change_pct=target_change_pct,
            scenario_id=scenario_id,
            persona=persona,
            actions=[abstain_action],
            abstain_reason=confidence_result.missing_evidence_hints[0] if confidence_result.missing_evidence_hints else "Insufficient evidence.",
            methodology_note="Actions withheld pending higher-confidence diagnosis. Deterministic engine requires ≥43% confidence to recommend intervention.",
        )

    # ── Case 2: Deployment Evidence → Highest Priority Action ─────────────
    dep_action = _build_deployment_action(persona_key, evidence)
    if dep_action:
        actions.append(dep_action)

    # ── Case 3: Driver-Based Actions ───────────────────────────────────────
    template_map = _EXECUTIVE_ACTIONS if persona_key == "executive" else _ENGINEER_ACTIONS

    if driver_result:
        # Sort drivers by contribution magnitude, process top 3
        sorted_drivers = sorted(driver_result.drivers, key=lambda d: d.contribution_pct, reverse=True)

        for driver in sorted_drivers[:3]:
            if driver.kpi_key == "interaction":
                continue  # Cross-factor interaction — not directly actionable

            driver_templates = template_map.get(driver.kpi_key)
            if not driver_templates:
                continue

            direction_key = driver.impact_direction  # 'positive' | 'negative'
            template = driver_templates.get(direction_key)
            if not template:
                continue

            # Evidence citations relevant to this driver
            driver_evidence = [
                e for e in evidence
                if driver.kpi_key in e.description.lower()
                or driver.name.lower() in e.description.lower()
                or e.evidence_type == "error_surge"
            ]
            citations = _extract_evidence_desc(driver_evidence[:3]) or [
                f"Driver {driver.name} accounts for {driver.contribution_pct:.0f}% of revenue movement (deterministic decomposition)."
            ]

            # Dynamic impact string — substitute driver contribution %
            action_str = template["action"]
            impact_str = template["impact"]
            if "{driver_contrib:.0f}" in impact_str:
                impact_str = impact_str.format(driver_contrib=driver.contribution_pct)

            action_rec = ActionRecommendation(
                rank=len(actions) + 1,
                driver=driver.name,
                controllable_lever=template["lever"],
                action=action_str,
                expected_impact=impact_str,
                owner=template["owner"],
                owner_role=persona.title(),
                confidence=_confidence_from_driver(driver, confidence_result),
                confidence_rationale=(
                    f"{driver.name} explains {driver.contribution_pct:.0f}% of KPI movement "
                    f"(impact direction: {driver.impact_direction}). "
                    f"Overall diagnostic confidence: {confidence_result.score}% ({confidence_result.level})."
                ),
                monitoring_plan=template["monitoring_plan"],
                evidence_citations=citations,
                action_type=template["action_type"],
                urgency=_urgency_from_driver(driver, target_change_pct),
            )
            actions.append(action_rec)

        # Sub-driver actions (Level 2 decomposition)
        if driver_result.sub_driver_result:
            sub = driver_result.sub_driver_result
            sub_negatives = [d for d in sub.drivers if d.impact_direction == "negative" and d.kpi_key != "interaction"]
            for sub_driver in sub_negatives[:1]:
                sub_templates = template_map.get(sub_driver.kpi_key)
                if sub_templates:
                    sub_template = sub_templates.get("negative", {})
                    if sub_template:
                        sub_citations = _extract_evidence_desc(
                            [e for e in evidence if sub_driver.kpi_key in e.description.lower()][:2]
                        ) or [f"Sub-driver {sub_driver.name} identified via Level-2 Orders decomposition ({sub_driver.contribution_pct:.0f}% of Orders movement)."]

                        actions.append(ActionRecommendation(
                            rank=len(actions) + 1,
                            driver=f"{sub_driver.name} [Orders Sub-Driver]",
                            controllable_lever=sub_template.get("lever", "Sub-Driver Remediation"),
                            action=sub_template.get("action", "Investigate sub-driver root cause."),
                            expected_impact=sub_template.get("impact", "Partial recovery of Orders volume."),
                            owner=sub_template.get("owner", "Engineering / Analytics"),
                            owner_role=persona.title(),
                            confidence=_confidence_from_driver(sub_driver, confidence_result),
                            confidence_rationale=f"Level-2 decomposition: {sub_driver.name} explains {sub_driver.contribution_pct:.0f}% of Orders movement.",
                            monitoring_plan=sub_template.get("monitoring_plan", "Monitor Orders recovery rate."),
                            evidence_citations=sub_citations,
                            action_type=sub_template.get("action_type", "investigate"),
                            urgency=_urgency_from_driver(sub_driver, target_change_pct),
                        ))

    # ── Fallback if no driver actions generated ────────────────────────────
    if not actions:
        actions.append(ActionRecommendation(
            rank=1,
            driver="Unknown",
            controllable_lever="Diagnostic Data Collection",
            action="Collect additional operational telemetry (error logs, deployment records, user journey data) before recommending targeted interventions.",
            expected_impact="Enables accurate root-cause isolation within 24 hours.",
            owner="Analytics Engineering" if persona_key == "engineer" else "Chief Analytics Officer",
            owner_role=persona.title(),
            confidence="Low",
            confidence_rationale="No isolatable driver found with sufficient confidence to warrant intervention.",
            monitoring_plan="Monitor all KPI tiers hourly and alert on further degradation.",
            evidence_citations=["No corroborating evidence identified."],
            action_type="investigate",
            urgency="Medium",
        ))

    # ── Re-rank: Immediate > Critical urgency first ────────────────────────
    urgency_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    type_order = {"immediate": 0, "investigate": 1, "short_term": 2, "strategic": 3}
    actions.sort(key=lambda a: (type_order.get(a.action_type, 9), urgency_order.get(a.urgency, 9)))
    for i, action in enumerate(actions):
        action.rank = i + 1

    # ── Deduplicate by driver key ──────────────────────────────────────────
    seen_drivers = set()
    deduped = []
    for action in actions:
        if action.driver not in seen_drivers:
            seen_drivers.add(action.driver)
            deduped.append(action)

    return ActionPlan(
        target_kpi=target_kpi_name,
        target_change_pct=target_change_pct,
        scenario_id=scenario_id,
        persona=persona,
        actions=deduped[:4],  # Return top 4 prioritised actions
        methodology_note=(
            "Actions derived deterministically from: (1) DriverContribution magnitudes and impact directions, "
            "(2) Evidence signal types (deployment, error_surge, log), "
            "(3) Persona role mapping. LLM may enrich phrasing; all structure is deterministic."
        ),
    )
