"""Evidence Engine - Merges structured metrics and unstructured operational evidence.

Combines:
1. Structured signals from SQLite (checkout error surge %, payment failure surge %, deployment changelogs, error logs)
2. Unstructured documents from RAG / ChromaDB (incidents, release notes, support digests)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "narratebi.db"


@dataclass
class EvidenceItem:
    source: str  # 'Payments', 'Operations', 'Deployment', 'Support', 'Incidents'
    timestamp: str
    description: str
    relevance: str  # 'High', 'Medium', 'Low'
    is_structured: bool


def fetch_structured_evidence(scenario_id: str, db_file: Optional[Path] = None) -> List[EvidenceItem]:
    """Extracts structured transactional, deployment, and log signals from SQLite."""
    evidence: List[EvidenceItem] = []
    target_db = db_file or DB_PATH

    if not target_db.exists():
        return evidence

    with sqlite3.connect(target_db) as conn:
        cursor = conn.cursor()

        # 1. Check payment & checkout error surges (compare baseline min vs incident peak)
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
                    )
                )

        # 2. Check deployment events
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
                )
            )

        # 3. Check system error logs
        cursor.execute(
            """
            SELECT timestamp, service, log_level, message
            FROM system_logs
            WHERE scenario_id = ? AND log_level IN ('ERROR', 'FATAL')
            ORDER BY timestamp ASC
            LIMIT 2
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
                )
            )

    return evidence


def get_combined_evidence(
    scenario_id: str,
    rag_evidence: Optional[List[EvidenceItem]] = None,
    db_file: Optional[Path] = None,
) -> List[EvidenceItem]:
    """Combines structured SQLite signals with RAG operational evidence in chronological order."""
    structured = fetch_structured_evidence(scenario_id, db_file=db_file)
    unstructured = rag_evidence or []
    
    combined = structured + unstructured
    return combined
