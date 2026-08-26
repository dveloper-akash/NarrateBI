"""NarrateBI - Main Streamlit Application

A clean, modern B2B SaaS Analytics prototype for AI-powered KPI root-cause diagnostics.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import sqlite3
import streamlit as st
from typing import Dict, List, Any

# Engine imports
from engine.kpi_engine import load_kpi_contracts, fetch_kpis_for_scenario, KPIResult
from engine.driver_engine import analyze_revenue_drivers
from engine.evidence import get_combined_evidence, EvidenceItem
from engine.confidence import calculate_confidence, ConfidenceScore
from rag.retrieve import retrieve_evidence
from ai.narrative import generate_narrative

# Page Configuration
st.set_page_config(
    page_title="NarrateBI | Diagnostic Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Enterprise Minimal Custom Styling
st.markdown(
    """
    <style>
    /* Base SaaS Styling */
    .stApp {
        background-color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #0F172A;
    }
    
    /* Top Navbar */
    .header-bar {
        background: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
        padding: 16px 24px;
        margin-bottom: 24px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* KPI Card */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: border-color 0.2s;
    }
    .kpi-card:hover {
        border-color: #CBD5E1;
    }
    .kpi-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-val {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A;
        margin: 4px 0;
    }
    .badge-neg {
        background: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-pos {
        background: #DCFCE7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-neutral {
        background: #F1F5F9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    
    /* Section Panels */
    .panel-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    .panel-header {
        font-size: 15px;
        font-weight: 700;
        color: #1E293B;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }
    
    /* Source Tags */
    .source-tag {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        margin-right: 6px;
    }
    .source-tag-payments { background: #E0E7FF; color: #3730A3; }
    .source-tag-deployment { background: #FEF3C7; color: #92400E; }
    .source-tag-incidents { background: #FCE7F3; color: #9D174D; }
    .source-tag-support { background: #CFFAFE; color: #155E75; }
    .source-tag-operations { background: #F1F5F9; color: #334155; }
    
    /* Telemetry Footer */
    .telemetry-bar {
        background: #F8FAFC;
        border-top: 1px solid #E2E8F0;
        padding: 12px 16px;
        font-size: 12px;
        color: #64748B;
        display: flex;
        justify-content: space-between;
        margin-top: 30px;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def record_feedback(scenario_id: str, kpi_key: str, rating: str, persona: str):
    """Saves user rating to SQLite feedback table."""
    db_path = PROJECT_ROOT / "database" / "narratebi.db"
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feedback (scenario_id, kpi_key, rating, persona)
                    VALUES (?, ?, ?, ?)
                    """,
                    (scenario_id, kpi_key, rating, persona),
                )
                conn.commit()
            st.toast("Thank you for your feedback!", icon="✅")
        except Exception:
            pass


def load_scenarios() -> Dict[str, Any]:
    """Loads all test scenarios from scenarios/ directory."""
    scenarios = {
        "scenario_1_multifactor": "Multi-factor Diagnosis (Payment Service Incident)",
        "scenario_2_low_confidence": "Low Confidence / Missing Evidence (Abstention)",
        "scenario_3_new_kpi": "New KPI / Limited Baseline (Cold Start)",
        "scenario_4_rbac": "Role-Based Access (RBAC) Demonstration",
        "scenario_5_contradiction": "Contradictory Signals Analysis",
    }
    return scenarios


def main():
    # 1. Top Navigation Bar & Controls
    col_nav1, col_nav2, col_nav3 = st.columns([3, 2, 2])

    with col_nav1:
        st.markdown("### 📊 NarrateBI")
        st.caption("Deterministic Diagnostic Intelligence & AI Narratives")

    with col_nav2:
        persona = st.selectbox(
            "Active Persona / View",
            options=["Executive", "Engineer"],
            index=0,
            help="Switch between business leadership narrative and technical infrastructure telemetry.",
        )

    scenarios = load_scenarios()
    with col_nav3:
        scenario_key = st.selectbox(
            "Demo Scenario",
            options=list(scenarios.keys()),
            format_func=lambda x: scenarios[x],
            index=0,
            help="Feeds different baseline conditions through the same deterministic pipeline.",
        )

    st.divider()

    # 2. Pipeline Execution
    kpis = fetch_kpis_for_scenario(scenario_key)
    if not kpis:
        # Fallback evaluation for preview if database not yet seeded
        contracts = load_kpi_contracts()
        kpis = [
            fetch_fallback_kpi("revenue", 4420000.0, 5000000.0, contracts),
            fetch_fallback_kpi("orders", 4210.0, 5000.0, contracts),
            fetch_fallback_kpi("conversion_rate", 4.21, 5.0, contracts),
            fetch_fallback_kpi("sessions", 100000.0, 100000.0, contracts),
            fetch_fallback_kpi("aov", 1050.0, 1000.0, contracts),
        ]

    kpi_map = {k.key: k for k in kpis}

    # 3. KPI Header Row
    st.markdown("##### 📈 Monitored KPI Health")
    kpi_cols = st.columns(len(kpis))

    for idx, kpi in enumerate(kpis):
        with kpi_cols[idx]:
            # Format value
            if kpi.unit == "INR":
                val_str = f"₹{kpi.current_value / 100000:.1f}L"
            elif kpi.unit == "%":
                val_str = f"{kpi.current_value:.2f}%"
            else:
                val_str = f"{int(kpi.current_value):,}"

            # Delta format
            if kpi.is_cold_start:
                delta_html = '<span class="badge-neutral">Cold Start (< 14d)</span>'
            elif kpi.change_pct < 0:
                delta_html = f'<span class="badge-neg">↓ {abs(kpi.change_pct)}%</span>'
            elif kpi.change_pct > 0:
                delta_html = f'<span class="badge-pos">↑ {kpi.change_pct}%</span>'
            else:
                delta_html = '<span class="badge-neutral">0.0% (Stable)</span>'

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">{kpi.name}</div>
                    <div class="kpi-val">{val_str}</div>
                    <div>{delta_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.popover("ℹ️ Definition"):
                st.markdown(f"**{kpi.name}**")
                st.markdown(f"- **Definition:** {kpi.metadata.definition}")
                st.markdown(f"- **Formula:** `{kpi.metadata.formula}`")
                st.markdown(f"- **Source:** {kpi.metadata.source}")
                st.markdown(f"- **Refresh:** {kpi.metadata.refresh}")
                st.markdown(f"- **Lineage:** `{kpi.metadata.lineage}`")
                st.markdown(f"- **Anomaly Threshold:** ±{kpi.metadata.threshold}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Cold Start Check
    cold_start_kpi = next((k for k in kpis if k.is_cold_start), None)
    if cold_start_kpi:
        st.warning(
            f"⚠️ **COLD START / NEW KPI DETECTED**: `{cold_start_kpi.name}` has only {cold_start_kpi.history_days} days of historical baseline. NarrateBI deterministically abstains from generating anomaly diagnoses until at least 14 days of data are recorded.",
            icon="⏳",
        )

    # 5. Deterministic Driver Analysis
    driver_res = analyze_revenue_drivers(kpi_map)
    primary_driver_name = driver_res.primary_driver if driver_res else "Conversion Rate"
    primary_driver_contrib = driver_res.primary_contribution if driver_res else 76.0

    # 6. Evidence Retrieval (RAG & SQLite)
    query_context = "payment gateway timeout errors and checkout failure deployment"
    unstructured_evidence = retrieve_evidence(query_context) if scenario_key != "scenario_2_low_confidence" else []
    combined_evidence = get_combined_evidence(scenario_key, unstructured_evidence)

    # 7. Deterministic Confidence Scoring
    has_sufficient_history = not bool(cold_start_kpi)
    if scenario_key == "scenario_2_low_confidence":
        # Force low operational evidence to trigger abstention
        confidence_result = calculate_confidence(primary_driver_contribution=50.0, evidence_items=[], has_sufficient_history=True)
    else:
        confidence_result = calculate_confidence(
            primary_driver_contribution=primary_driver_contrib,
            evidence_items=combined_evidence,
            has_sufficient_history=has_sufficient_history,
        )

    # 8. AI Narrative Generation
    evidence_desc = [e.description for e in combined_evidence]
    target_kpi = kpi_map.get("revenue", kpis[0])

    narrative = generate_narrative(
        kpi_name=target_kpi.name,
        change_pct=target_kpi.change_pct,
        primary_driver=primary_driver_name,
        driver_contribution=primary_driver_contrib,
        confidence_score=confidence_result.score,
        confidence_level=confidence_result.level,
        evidence_descriptions=evidence_desc,
        persona=persona.lower(),
        should_abstain=confidence_result.should_abstain,
    )

    # 9. Main Grid: Insight vs. Evidence & Confidence
    col_left, col_right = st.columns([7, 5])

    with col_left:
        # Main Insight Card
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-header">🎯 Diagnostic Narrative ({persona} View)</div>
                <h4 style="margin-top:0; color:#0F172A;">{narrative.get('summary', 'Diagnosis Summary')}</h4>
                <p style="color:#334155; font-size:14px;">
                    {narrative.get('reason', narrative.get('technical_diagnosis', ''))}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Driver Contribution Panel
        st.markdown('<div class="panel-card"><div class="panel-header">⚖️ Deterministic Driver Breakdown</div>', unsafe_allow_html=True)
        if driver_res:
            for d in driver_res.drivers:
                c1, c2, c3 = st.columns([4, 6, 2])
                with c1:
                    st.write(f"**{d.name}**")
                with c2:
                    st.progress(min(1.0, max(0.0, d.contribution_pct / 100.0)))
                with c3:
                    st.write(f"**{d.contribution_pct}%**")
        st.markdown("</div>", unsafe_allow_html=True)

        # Recommendation Card
        rec_text = narrative.get("recommendation", narrative.get("technical_recommendation", "Continue monitoring system metrics."))
        st.markdown(
            f"""
            <div class="panel-card" style="border-left: 4px solid #2563EB;">
                <div class="panel-header" style="color:#2563EB;">💡 Recommended Action</div>
                <div style="font-size:14px; font-weight:500; color:#1E293B;">{rec_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        # Confidence Score Card
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">🛡️ Diagnostic Confidence</div>', unsafe_allow_html=True)

        conf_color = "#16A34A" if confidence_result.score >= 70 else "#D97706" if confidence_result.score >= 45 else "#DC2626"
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:26px; font-weight:800; color:{conf_color};">{confidence_result.score}%</span>
                <span style="font-size:13px; font-weight:700; color:{conf_color}; text-transform:uppercase;">{confidence_result.level} Confidence</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(confidence_result.score / 100.0)

        if confidence_result.should_abstain:
            st.error("⚠️ **System Abstaining**: Confidence is below the 45% threshold. NarrateBI avoids hallucinations by requesting missing operational data instead of guessing.", icon="🛑")
            if confidence_result.missing_evidence_hints:
                st.markdown("**Required Evidence:**")
                for hint in confidence_result.missing_evidence_hints:
                    st.markdown(f"- {hint}")
        else:
            st.markdown("**Confidence Factors:**")
            for factor in confidence_result.factors:
                st.markdown(f"✓ {factor}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Supporting Evidence Panel
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">📑 Corroborating Evidence</div>', unsafe_allow_html=True)

        if not combined_evidence:
            st.info("No operational evidence items linked to this scenario.")
        else:
            for item in combined_evidence:
                source_class = f"source-tag-{item.source.lower()}"
                st.markdown(
                    f"""
                    <div style="padding: 8px 0; border-bottom: 1px solid #F1F5F9; font-size:13px;">
                        <span class="source-tag {source_class}">{item.source}</span>
                        <span style="color:#334155;">{item.description}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # 10. Architecture Transparency & Feedback
    st.divider()
    col_arch, col_feed = st.columns([8, 4])

    with col_arch:
        st.caption("⚙️ **Architecture Transparency**")
        st.markdown(
            """
            - **Deterministic Engine:** KPI Delta Calculation • Anomaly Thresholds • Parent-Child Driver Contribution • Confidence Scoring
            - **RAG Context Layer:** ChromaDB Semantic Document Index (Incidents, Deployments, Server Logs)
            - **LLM Reasoning Layer:** Grounded Persona Explanations & Action Formulation (`gemini-2.5-flash` / Grounded Fallback)
            """
        )

    with col_feed:
        st.caption("Was this diagnosis useful?")
        cf1, cf2 = st.columns(2)
        with cf1:
            if st.button("👍 Helpful", use_container_width=True):
                record_feedback(scenario_key, target_kpi.key, "up", persona)
        with cf2:
            if st.button("👎 Inaccurate", use_container_width=True):
                record_feedback(scenario_key, target_kpi.key, "down", persona)

    # 11. Telemetry Bar
    telemetry = narrative.get("telemetry", {})
    st.markdown(
        f"""
        <div class="telemetry-bar">
            <span>⚡ Execution Latency: <b>{telemetry.get('latency_ms', 820)} ms</b></span>
            <span>🪙 Token Count: <b>{telemetry.get('tokens', 320)}</b></span>
            <span>💵 Est. AI Cost: <b>${telemetry.get('estimated_cost_usd', 0.0002):.5f}</b></span>
            <span>🔒 Mode: <b>{telemetry.get('mode', 'grounded')}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_fallback_kpi(key: str, curr: float, base: float, contracts: Dict[str, Any]) -> KPIResult:
    """Fallback helper when database is empty."""
    from engine.kpi_engine import evaluate_kpi
    return evaluate_kpi(key, curr, base, history_days=30, contracts=contracts)


if __name__ == "__main__":
    main()
