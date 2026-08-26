"""Evidence Engine - Merges structured metrics and unstructured operational evidence.

Combines:
1. Structured signals from SQLite (e.g. checkout errors +42%, payment failures +25%)
2. Unstructured documents from ChromaDB / RAG (deployments, incident reports, logs)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "narratebi.db"


@dataclass
class EvidenceItem:
    source: str  # 'Payments', 'Operations', 'Deployment', 'Support'
    timestamp: str
    description: str
    relevance: str  # 'High', 'Medium', 'Low'
    is_structured: bool


def fetch_structured_evidence(scenario_id: str) -> List[EvidenceItem]:
    """Extracts structured transactional and telemetry evidence from SQLite."""
    evidence = []
    if not DB_PATH.exists():
        return evidence

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Check payment / checkout error increases
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
            prev, curr = rows[-2], rows[-1]
            prev_err, curr_err = prev[4], curr[4]
            if prev_err > 0 and curr_err > prev_err:
                increase_pct = round(((curr_err - prev_err) / prev_err) * 100)
                evidence.append(
                    EvidenceItem(
                        source="Payments",
                        timestamp=curr[0],
                        description=f"Checkout errors increased {increase_pct}% (from {prev_err} to {curr_err})",
                        relevance="High",
                        is_structured=True,
                    )
                )

            prev_fail, curr_fail = prev[3], curr[3]
            if prev_fail > 0 and curr_fail > prev_fail:
                fail_pct = round(((curr_fail - prev_fail) / prev_fail) * 100)
                evidence.append(
                    EvidenceItem(
                        source="Payments",
                        timestamp=curr[0],
                        description=f"Payment failures increased {fail_pct}%",
                        relevance="High",
                        is_structured=True,
                    )
                )

        # Check deployments
        cursor.execute(
            """
            SELECT timestamp, service, version, status
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
                    description=f"{dep[1]} version {dep[2]} deployment {dep[3]}",
                    relevance="High",
                    is_structured=True,
                )
            )

    return evidence


def get_combined_evidence(scenario_id: str, rag_evidence: Optional[List[EvidenceItem]] = None) -> List[EvidenceItem]:
    """Combines structured SQLite signals with RAG operational evidence."""
    structured = fetch_structured_evidence(scenario_id)
    unstructured = rag_evidence or []
    return structured + unstructured
