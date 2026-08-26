"""NarrateBI - Main Streamlit Application

A clean, high-contrast B2B SaaS Analytics prototype for AI-powered KPI root-cause diagnostics.
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
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# High-Contrast Enterprise Styling (Theme-Adaptive)
st.markdown(
    """
    <style>
    /* Base SaaS Styling */
    .stApp {
        background-color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Header */
    .brand-title {
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-subtitle {
        color: #475569;
        font-size: 13px;
        font-weight: 500;
        margin-top: 2px;
    }

    /* KPI Cards */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .kpi-card:hover {
        border-color: #3B82F6;
        transform: translateY(-1px);
    }
    .kpi-title {
        font-size: 12px;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .kpi-val {
        font-size: 24px;
        font-weight: 800;
        color: #0F172A;
        margin: 4px 0 8px 0;
    }
    .badge-neg {
        background: #FEE2E2;
        color: #DC2626;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-pos {
        background: #DCFCE7;
        color: #16A34A;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-neutral {
        background: #F1F5F9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    
    /* Panels */
    .panel-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    .panel-header {
        font-size: 14px;
        font-weight: 700;
        color: #2563EB;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 8px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* RBAC Tag */
    .rbac-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }

    /* Colorful Evidence Badges */
    .source-tag {
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: 700;
        margin-right: 8px;
        display: inline-block;
    }
    .source-tag-payments { background: #EEF2FF; color: #4F46E5; border: 1px solid #C7D2FE; }
    .source-tag-deployment { background: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }
    .source-tag-incidents { background: #FCE7F3; color: #DB2777; border: 1px solid #FBCFE8; }
    .source-tag-support { background: #E0F2FE; color: #0284C7; border: 1px solid #BAE6FD; }
    .source-tag-operations { background: #F3E8FF; color: #9333EA; border: 1px solid #E9D5FF; }

    /* Telemetry Footer */
    .telemetry-bar {
        background: #1E293B;
        color: #F8FAFC;
        border-radius: 8px;
        padding: 12px 18px;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        margin-top: 24px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .telemetry-item {
        color: #94A3B8;
    }
    .telemetry-item b {
        color: #38BDF8;
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
            st.toast("Feedback recorded successfully!", icon="✅")
        except Exception:
            pass


def get_recent_feedback() -> List[Dict[str, Any]]:
    """Fetches recent feedback submissions from SQLite."""
    db_path = PROJECT_ROOT / "database" / "narratebi.db"
    items = []
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT scenario_id, kpi_key, rating, persona, created_at
                    FROM feedback
                    ORDER BY id DESC LIMIT 5
                    """
                )
                for r in cursor.fetchall():
                    items.append({
                        "scenario": r[0],
                        "kpi": r[1],
                        "rating": "👍 Helpful" if r[2] == "up" else "👎 Inaccurate",
                        "persona": r[3],
                        "timestamp": r[4],
                    })
        except Exception:
            pass
    return items


def load_scenarios() -> Dict[str, Any]:
    """Loads all test scenarios."""
    return {
        "scenario_1_multifactor": "Multi-factor Diagnosis (Payment Service Incident)",
        "scenario_2_low_confidence": "Low Confidence / Missing Evidence (Abstention)",
        "scenario_3_new_kpi": "New KPI / Limited Baseline (Cold Start)",
        "scenario_4_rbac": "Role-Based Access (RBAC) Demonstration",
        "scenario_5_contradiction": "Contradictory Signals Analysis",
    }


def filter_evidence_by_rbac(evidence: List[EvidenceItem], persona: str) -> List[EvidenceItem]:
    """Filters evidence items according to role access policies."""
    if persona.lower() == "engineer":
        return evidence
    # Executive persona: Filter out raw internal server debug logs
    return [e for e in evidence if not (e.source == "Operations" and "[" in e.description)]


def main():
    # 1. Top Navbar
    col_nav1, col_nav2, col_nav3 = st.columns([3, 2, 2])

    with col_nav1:
        st.markdown('<div class="brand-title">⚡ NarrateBI</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-subtitle">Diagnostic Root-Cause Engine & AI Narratives</div>', unsafe_allow_html=True)

    with col_nav2:
        persona = st.selectbox(
            "Active Persona / Role",
            options=["Executive", "Engineer"],
            index=0,
            help="Switch between Executive (business impact) and Engineer (technical telemetry).",
        )

    scenarios = load_scenarios()
    with col_nav3:
        scenario_key = st.selectbox(
            "Demo Scenario",
            options=list(scenarios.keys()),
            format_func=lambda x: scenarios[x],
            index=0,
            help="Selects underlying operational and KPI scenario datasets.",
        )

    st.divider()

    # 2. Pipeline Execution: Fetch KPIs
    kpis = fetch_kpis_for_scenario(scenario_key)
    if not kpis:
        st.error("No KPI records found. Please run `python database/seed.py`.", icon="🚨")
        return

    kpi_map = {k.key: k for k in kpis}

    # 3. KPI Header Row
    st.markdown("##### 📈 Monitored Business KPIs")
    kpi_cols = st.columns(len(kpis))

    for idx, kpi in enumerate(kpis):
        with kpi_cols[idx]:
            if kpi.unit == "INR":
                val_str = f"₹{kpi.current_value / 100000:.1f}L"
            elif kpi.unit == "%":
                val_str = f"{kpi.current_value:.2f}%"
            else:
                val_str = f"{int(kpi.current_value):,}"

            if kpi.is_cold_start:
                delta_html = '<span class="badge-neutral">Cold Start (< 14d)</span>'
            elif kpi.change_pct < 0:
                delta_html = f'<span class="badge-neg">↓ {abs(kpi.change_pct):.1f}%</span>'
            elif kpi.change_pct > 0:
                delta_html = f'<span class="badge-pos">↑ {kpi.change_pct:.1f}%</span>'
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

            with st.popover("📘 Definition & Lineage"):
                st.markdown(f"**{kpi.name}**")
                st.markdown(f"- **Definition:** {kpi.metadata.definition}")
                st.markdown(f"- **Formula:** `{kpi.metadata.formula}`")
                st.markdown(f"- **Source:** `{kpi.metadata.source}`")
                st.markdown(f"- **Refresh Rate:** `{kpi.metadata.refresh}`")
                st.markdown(f"- **Lineage:** `{kpi.metadata.lineage}`")
                st.markdown(f"- **Anomaly Threshold:** `±{kpi.metadata.threshold}%`")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Cold Start Banner
    cold_start_kpi = next((k for k in kpis if k.is_cold_start), None)
    if cold_start_kpi:
        st.warning(
            f"⚠️ **COLD START / NEW KPI DETECTED**: `{cold_start_kpi.name}` has only {cold_start_kpi.history_days} days of historical baseline. NarrateBI deterministically abstains from generating anomaly diagnoses until at least 14 days of data are recorded.",
            icon="⏳",
        )

    # 5. Deterministic Driver Decomposition
    driver_res = analyze_revenue_drivers(kpi_map)
    primary_driver_name = driver_res.primary_driver if driver_res else "Conversion Rate"
    primary_driver_contrib = driver_res.primary_contribution if driver_res else 76.0

    # 6. Evidence Retrieval (RAG & SQLite)
    query_context = "payment gateway timeout errors and checkout failure deployment"
    unstructured_evidence = retrieve_evidence(query_context) if scenario_key != "scenario_2_low_confidence" else []
    combined_evidence = get_combined_evidence(scenario_key, unstructured_evidence)
    filtered_evidence = filter_evidence_by_rbac(combined_evidence, persona)

    # 7. Deterministic Confidence Scoring
    has_sufficient_history = not bool(cold_start_kpi)
    if scenario_key == "scenario_2_low_confidence":
        confidence_result = calculate_confidence(primary_driver_contribution=50.0, evidence_items=[], has_sufficient_history=True)
    else:
        confidence_result = calculate_confidence(
            primary_driver_contribution=primary_driver_contrib,
            evidence_items=combined_evidence,
            has_sufficient_history=has_sufficient_history,
        )

    # 8. Persona AI Narrative Generation
    evidence_desc = [e.description for e in filtered_evidence]
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

    # 9. Main Grid
    col_left, col_right = st.columns([7, 5])

    with col_left:
        # Diagnostic Narrative Card
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-header">
                    <span>🎯 Diagnostic Narrative</span>
                    <span class="rbac-badge">{persona} View</span>
                </div>
                <h4 style="margin-top:0; color:#0F172A;">{narrative.get('summary', 'Diagnostic Summary')}</h4>
                <p style="color:#334155; font-size:14px; line-height:1.5;">
                    {narrative.get('reason', narrative.get('technical_diagnosis', ''))}
                </p>
                {f'<div style="font-size:13px; color:#64748B; margin-top:8px;"><b>Business Impact:</b> {narrative.get("business_impact")}</div>' if narrative.get("business_impact") and persona == 'Executive' else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Deterministic Driver Breakdown
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

            # Show Sub-driver Level 2 if present
            sub_res = getattr(driver_res, "sub_driver_result", None)
            if sub_res:
                st.caption(f"↳ **Sub-Factor Decomposition for {sub_res.target_kpi}:**")
                for sd in sub_res.drivers:
                    sc1, sc2, sc3 = st.columns([4, 6, 2])
                    with sc1:
                        st.write(f"&nbsp;&nbsp;• {sd.name}")
                    with sc2:
                        st.progress(min(1.0, max(0.0, sd.contribution_pct / 100.0)))
                    with sc3:
                        st.write(f"{sd.contribution_pct}%")
        st.markdown("</div>", unsafe_allow_html=True)

        # Recommendation Card
        rec_text = narrative.get("recommendation", narrative.get("technical_recommendation", "Continue monitoring system metrics."))
        st.markdown(
            f"""
            <div class="panel-card" style="border-left: 5px solid #2563EB;">
                <div class="panel-header" style="color:#2563EB;">💡 Recommended Action</div>
                <div style="font-size:14px; font-weight:600; color:#1E293B; line-height:1.4;">{rec_text}</div>
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
                <span style="font-size:28px; font-weight:800; color:{conf_color};">{confidence_result.score}%</span>
                <span style="font-size:13px; font-weight:700; color:{conf_color}; text-transform:uppercase;">{confidence_result.level} Confidence</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(confidence_result.score / 100.0)

        if confidence_result.should_abstain:
            st.error("⚠️ **System Abstaining**: Diagnostic confidence is below the 45% threshold. NarrateBI avoids hallucinations by requiring missing operational logs instead of guessing.", icon="🛑")
            if confidence_result.missing_evidence_hints:
                st.markdown("**Required Evidence for Confirmation:**")
                for hint in confidence_result.missing_evidence_hints:
                    st.markdown(f"- {hint}")
        else:
            st.markdown("**Corroborating Confidence Factors:**")
            for factor in confidence_result.factors:
                st.markdown(f"✓ {factor}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Supporting Evidence Panel
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="panel-header">
                <span>📑 Corroborating Evidence</span>
                <span class="rbac-badge">{len(filtered_evidence)} items</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not filtered_evidence:
            st.info("No operational evidence items linked to this scenario.")
        else:
            for item in filtered_evidence:
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
            - **Deterministic Math Layer:** KPI Δ% • Anomaly Thresholds • Hierarchical Driver Variance • Confidence Scoring
            - **RAG Context Layer:** ChromaDB Document Retrieval (Incidents, Deployments, Server Logs)
            - **Generative AI Layer:** Persona Explanation Grounding (`gemini-2.5-flash` / Grounded Fallback)
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

        recent_fb = get_recent_feedback()
        if recent_fb:
            with st.expander("📜 Recent Submissions"):
                for fb in recent_fb:
                    st.caption(f"{fb['rating']} ({fb['persona']}) - {fb['scenario']}")

    # 11. Telemetry Bar
    telemetry = narrative.get("telemetry", {})
    st.markdown(
        f"""
        <div class="telemetry-bar">
            <span class="telemetry-item">⚡ Latency: <b>{telemetry.get('latency_ms', 820)} ms</b></span>
            <span class="telemetry-item">🪙 Tokens: <b>{telemetry.get('tokens', 320)}</b></span>
            <span class="telemetry-item">💵 Est. AI Cost: <b>${telemetry.get('estimated_cost_usd', 0.0002):.5f}</b></span>
            <span class="telemetry-item">🔒 Mode: <b>{telemetry.get('mode', 'grounded')}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
