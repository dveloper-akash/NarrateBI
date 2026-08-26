"""KPI Engine - Deterministic KPI calculations, anomaly detection, and contract loading.

Deterministic math only:
- Percentage change: ((current - baseline) / baseline) * 100
- Formula relationships:
    * Conversion Rate = (Orders / Sessions) * 100
    * Revenue = Orders * AOV
    * AOV = Revenue / Orders
- Anomaly threshold comparison from config/kpi_contracts.yaml
- Cold-start history verification (< 14 days)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import sqlite3

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "kpi_contracts.yaml"
DB_PATH = Path(__file__).resolve().parent.parent / "database" / "narratebi.db"


@dataclass
class KPIMetadata:
    key: str
    name: str
    definition: str
    formula: str
    source: str
    refresh: str
    unit: str
    threshold: float
    min_history_days: int
    lineage: str
    access: List[str]


@dataclass
class KPIResult:
    key: str
    name: str
    current_value: float
    baseline_value: float
    change_pct: float
    unit: str
    is_anomaly: bool
    is_cold_start: bool
    history_days: int
    metadata: KPIMetadata


def load_kpi_contracts(config_file: Optional[Path] = None) -> Dict[str, KPIMetadata]:
    """Loads KPI metadata contracts from YAML configuration."""
    target_path = config_file or CONFIG_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"KPI contract config not found at {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    contracts = {}
    for key, spec in data.get("kpis", {}).items():
        contracts[key] = KPIMetadata(
            key=key,
            name=spec.get("name", key),
            definition=spec.get("definition", ""),
            formula=spec.get("formula", ""),
            source=spec.get("source", "Unknown"),
            refresh=spec.get("refresh", "Daily"),
            unit=spec.get("unit", ""),
            threshold=float(spec.get("threshold", 10.0)),
            min_history_days=int(spec.get("min_history_days", 14)),
            lineage=spec.get("lineage", ""),
            access=spec.get("access", ["executive", "engineer"]),
        )
    return contracts


def calculate_change_pct(current: float, baseline: float) -> float:
    """Calculates deterministic percentage change between current and baseline."""
    if baseline == 0:
        return 0.0
    return round(((current - baseline) / baseline) * 100.0, 2)


def calculate_conversion_rate(orders: float, sessions: float) -> float:
    """Deterministic Conversion Rate formula: (Orders / Sessions) * 100."""
    if sessions <= 0:
        return 0.0
    return round((orders / sessions) * 100.0, 2)


def calculate_revenue(orders: float, aov: float) -> float:
    """Deterministic Revenue formula: Orders * AOV."""
    return round(orders * aov, 2)


def calculate_aov(revenue: float, orders: float) -> float:
    """Deterministic AOV formula: Revenue / Orders."""
    if orders <= 0:
        return 0.0
    return round(revenue / orders, 2)


def evaluate_kpi(
    key: str,
    current: float,
    baseline: float,
    history_days: int = 30,
    contracts: Optional[Dict[str, KPIMetadata]] = None,
) -> KPIResult:
    """Evaluates a single KPI for anomaly threshold breaches and cold-start state."""
    if contracts is None:
        contracts = load_kpi_contracts()

    meta = contracts.get(
        key,
        KPIMetadata(
            key=key,
            name=key.replace("_", " ").title(),
            definition="",
            formula="",
            source="Custom",
            refresh="Daily",
            unit="",
            threshold=10.0,
            min_history_days=14,
            lineage="",
            access=["executive", "engineer"],
        ),
    )

    change_pct = calculate_change_pct(current, baseline)
    is_cold_start = history_days < meta.min_history_days
    is_anomaly = (not is_cold_start) and (abs(change_pct) >= meta.threshold)

    return KPIResult(
        key=key,
        name=meta.name,
        current_value=current,
        baseline_value=baseline,
        change_pct=change_pct,
        unit=meta.unit,
        is_anomaly=is_anomaly,
        is_cold_start=is_cold_start,
        history_days=history_days,
        metadata=meta,
    )


def fetch_kpis_for_scenario(scenario_id: str, db_file: Optional[Path] = None) -> List[KPIResult]:
    """Fetches and evaluates all KPIs for a given scenario from the SQLite database."""
    contracts = load_kpi_contracts()
    results = []
    target_db = db_file or DB_PATH

    if not target_db.exists():
        return results

    with sqlite3.connect(target_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT kpi_key, current_value, baseline_value, history_days
            FROM kpi_values
            WHERE scenario_id = ?
            ORDER BY id ASC
            """,
            (scenario_id,),
        )
        rows = cursor.fetchall()

    for kpi_key, current, baseline, history_days in rows:
        result = evaluate_kpi(
            key=kpi_key,
            current=current,
            baseline=baseline,
            history_days=history_days,
            contracts=contracts,
        )
        results.append(result)

    return results
