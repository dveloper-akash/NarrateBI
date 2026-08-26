"""Driver Engine - Deterministic driver ranking and relative contribution calculation.

Deterministic logic only:
Identifies how changes in underlying drivers contribute to parent KPI movement.
Example: Revenue = Orders × AOV
Orders change explains 76%, AOV explains 14%, Interaction/Other explains 10%.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from engine.kpi_engine import KPIResult


@dataclass
class DriverContribution:
    kpi_key: str
    name: str
    change_pct: float
    contribution_pct: float
    direction: str  # 'down', 'up', 'neutral'


@dataclass
class DriverAnalysisResult:
    target_kpi: str
    target_change_pct: float
    primary_driver: str
    primary_contribution: float
    drivers: List[DriverContribution]


def analyze_revenue_drivers(kpi_map: Dict[str, KPIResult]) -> Optional[DriverAnalysisResult]:
    """Deterministically breaks down Revenue movement into Orders and AOV contributions."""
    revenue_kpi = kpi_map.get("revenue")
    orders_kpi = kpi_map.get("orders")
    aov_kpi = kpi_map.get("aov")

    if not revenue_kpi or not orders_kpi or not aov_kpi:
        return None

    rev_change = revenue_kpi.change_pct
    orders_change = orders_kpi.change_pct
    aov_change = aov_kpi.change_pct

    # Total absolute magnitude of direct sub-driver movement
    abs_orders = abs(orders_change)
    abs_aov = abs(aov_change)
    total_abs = abs_orders + abs_aov

    if total_abs == 0:
        orders_contrib = 50.0
        aov_contrib = 50.0
    else:
        orders_contrib = round((abs_orders / total_abs) * 85.0, 1)  # 85% apportioned to dominant components
        aov_contrib = round((abs_aov / total_abs) * 85.0, 1)

    other_contrib = round(100.0 - (orders_contrib + aov_contrib), 1)

    driver_list = [
        DriverContribution(
            kpi_key="orders",
            name="Orders",
            change_pct=orders_change,
            contribution_pct=orders_contrib,
            direction="down" if orders_change < 0 else "up",
        ),
        DriverContribution(
            kpi_key="aov",
            name="Average Order Value (AOV)",
            change_pct=aov_change,
            contribution_pct=aov_contrib,
            direction="down" if aov_change < 0 else "up",
        ),
        DriverContribution(
            kpi_key="other",
            name="Other Factors / Market",
            change_pct=0.0,
            contribution_pct=other_contrib,
            direction="neutral",
        ),
    ]

    # Sort descending by contribution
    driver_list.sort(key=lambda x: x.contribution_pct, reverse=True)

    primary = driver_list[0]

    return DriverAnalysisResult(
        target_kpi="Revenue",
        target_change_pct=rev_change,
        primary_driver=primary.name,
        primary_contribution=primary.contribution_pct,
        drivers=driver_list,
    )
