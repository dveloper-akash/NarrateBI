"""Evidence Engine - Structured metrics + RAG evidence with full traceability.

Combines:
1. Structured signals from SQLite (payment errors, deployment changelogs, system logs).
2. Unstructured RAG documents from ChromaDB / manifest index.

Each EvidenceItem carries enough metadata to understand:
- source       : which system produced this signal
- timestamp    : when the event occurred
- description  : human-readable summary
- relevance    : 'High' | 'Medium' | 'Low'
- is_structured: True = SQLite signal, False = RAG/doc retrieval
- evidence_type: 'error_surge' | 'deployment' | 'log' | 'rag_doc' | 'marketing' | 'other'
- affected_entity: service/component/dimension affected
- contradiction_flag: True if this item conflicts with other sources
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "narratebi.db"


@dataclass
class EvidenceItem:
    source: str          # 'Payments', 'Operations', 'Deployment', 'Support', 'Incidents', 'Marketing'
    timestamp: str       # ISO or descriptive timestamp
    description: str     # human-readable summary of the signal
    relevance: str       # 'High' | 'Medium' | 'Low'
    is_structured: bool  # True = from SQLite; False = from RAG/docs

    # Traceability fields (optional, default to sensible values)
    evidence_type: str = "other"        # 'error_surge' | 'deployment' | 'log' | 'rag_doc' | 'marketing'
    affected_entity: str = "unknown"    # service or component name
    contradiction_flag: bool = False    # True if this conflicts with other signals


def fetch_structured_evidence(scenario_id: str, db_file: Optional[Path] = None) -> List[EvidenceItem]:
    """Extracts structured transactional, deployment, and log signals from SQLite."""
    evidence: List[EvidenceItem] = []
    target_db = db_file or DB_PATH

    if not target_db.exists():
        return evidence

    with sqlite3.connect(target_db) as conn:
        cursor = conn.cursor()

        # 1. Payment & checkout error surges
        cursor.execute(
            """
            SELECT timestamp, sessions, orders, payment_failures, checkout_errors
            FROM payment_data
            WHERE scenario_id = ?
            ORDER BY timestamp ASC
            """,
            (scenario_id,),
        )
        rows = cursor.fetchall()
        if len(rows) >= 2:
            initial_err = rows[0][4]
            max_err_row = max(rows, key=lambda r: r[4])
            peak_err = max_err_row[4]
            peak_timestamp = max_err_row[0]

            if initial_err > 0 and peak_err > initial_err:
                increase_pct = round(((peak_err - initial_err) / initial_err) * 100)
                evidence.append(
                    EvidenceItem(
                        source="Payments",
                        timestamp=peak_timestamp,
                        description=f"Checkout errors increased {increase_pct}% (from {initial_err} to {peak_err}/hr)",
                        relevance="High",
                        is_structured=True,
                        evidence_type="error_surge",
                        affected_entity="checkout-service",
                    )
                )

            initial_fail = rows[0][3]
            max_fail_row = max(rows, key=lambda r: r[3])
            peak_fail = max_fail_row[3]
            if initial_fail > 0 and peak_fail > initial_fail:
                fail_pct = round(((peak_fail - initial_fail) / initial_fail) * 100)
                evidence.append(
                    EvidenceItem(
                        source="Payments",
                        timestamp=max_fail_row[0],
                        description=f"Payment failures increased {fail_pct}% (from {initial_fail} to {peak_fail}/hr)",
                        relevance="High",
                        is_structured=True,
                        evidence_type="error_surge",
                        affected_entity="payment-service",
                    )
                )

        # 2. Deployment events
        cursor.execute(
            """
            SELECT timestamp, service, version, status, deployed_by
            FROM deployment_events
            WHERE scenario_id = ?
            ORDER BY timestamp DESC
            """,
            (scenario_id,),
        )
        deployments = cursor.fetchall()
        for dep in deployments:
            evidence.append(
                EvidenceItem(
                    source="Deployment",
                    timestamp=dep[0],
                    description=f"{dep[1]} version {dep[2]} deployment {dep[3]} at {dep[0]} (by {dep[4]})",
                    relevance="High",
                    is_structured=True,
                    evidence_type="deployment",
                    affected_entity=dep[1],
                )
            )

        # 3. System error/fatal logs
        cursor.execute(
            """
            SELECT timestamp, service, log_level, message
            FROM system_logs
            WHERE scenario_id = ? AND log_level IN ('ERROR', 'FATAL')
            ORDER BY timestamp ASC
            LIMIT 3
            """,
            (scenario_id,),
        )
        error_logs = cursor.fetchall()
        for log in error_logs:
            evidence.append(
                EvidenceItem(
                    source="Operations",
                    timestamp=log[0],
                    description=f"[{log[1]}] {log[3]}",
                    relevance="High",
                    is_structured=True,
                    evidence_type="log",
                    affected_entity=log[1],
                )
            )

    return evidence


def check_contradiction(
    structured: List[EvidenceItem],
    rag_items: List[EvidenceItem],
) -> List[EvidenceItem]:
    """Flags evidence items that contradict the dominant structured signal.

    Returns the rag_items list with contradiction_flag set where applicable.
    Does NOT silently discard contradictory evidence — surfaces it.
    """
    structured_desc = " ".join(e.description.lower() for e in structured)
    has_errors = any(kw in structured_desc for kw in ["errors increased", "failures increased", "error", "fatal"])

    flagged = []
    for item in rag_items:
        desc_lower = item.description.lower()
        is_contradiction = (
            has_errors
            and any(kw in desc_lower for kw in [
                "strong conversion", "record roas", "outperforming", "healthy traffic",
                "positive roas", "all systems normal", "no incidents",
            ])
        )
        if is_contradiction:
            flagged.append(
                EvidenceItem(
                    source=item.source,
                    timestamp=item.timestamp,
                    description=item.description,
                    relevance=item.relevance,
                    is_structured=item.is_structured,
                    evidence_type=item.evidence_type,
                    affected_entity=item.affected_entity,
                    contradiction_flag=True,
                )
            )
        else:
            flagged.append(item)
    return flagged


def get_combined_evidence(
    scenario_id: str,
    rag_evidence: Optional[List[EvidenceItem]] = None,
    db_file: Optional[Path] = None,
) -> List[EvidenceItem]:
    """Combines structured SQLite signals with RAG operational evidence.

    Applies contradiction flagging and returns items sorted:
    structured first (chronological), then RAG items.
    Contradictory items are included but flagged — never silently discarded.
    """
    structured = fetch_structured_evidence(scenario_id, db_file=db_file)
    unstructured = rag_evidence or []

    # Contradiction check: flag RAG items that conflict with structured signals
    unstructured_checked = check_contradiction(structured, unstructured)

    combined = structured + unstructured_checked
    return combined
