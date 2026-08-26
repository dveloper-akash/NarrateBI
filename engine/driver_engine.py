"""Driver Engine - Deterministic driver ranking and relative contribution calculation.

Mathematical driver decomposition:
- Level 1: Revenue = Orders × AOV
    ΔRevenue ≈ (ΔOrders × AOV_base) + (ΔAOV × Orders_base) + (ΔOrders × ΔAOV)
- Level 2: Orders = Sessions × Conversion Rate
    ΔOrders ≈ (ΔSessions × CR_base) + (ΔCR × Sessions_base) + (ΔSessions × ΔCR)

Contribution percentages are computed deterministically from direct factor variance
and strictly sum to 100%.
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
    raw_delta_impact: float


@dataclass
class DriverAnalysisResult:
    target_kpi: str
    target_change_pct: float
    primary_driver: str
    primary_contribution: float
    drivers: List[DriverContribution]
    sub_driver_result: Optional["DriverAnalysisResult"] = None


def decompose_multiplicative_pair(
    target_name: str,
    target_change_pct: float,
    factor_a_key: str,
    factor_a_name: str,
    factor_a_curr: float,
    factor_a_base: float,
    factor_b_key: str,
    factor_b_name: str,
    factor_b_curr: float,
    factor_b_base: float,
) -> DriverAnalysisResult:
    """Decomposes target movement into factor A and factor B contributions."""
    delta_a = factor_a_curr - factor_a_base
    delta_b = factor_b_curr - factor_b_base

    # First-order marginal effects
    effect_a = delta_a * factor_b_base
    effect_b = delta_b * factor_a_base
    interaction = delta_a * delta_b

    abs_a = abs(effect_a)
    abs_b = abs(effect_b)
    abs_interaction = abs(interaction)
    total_abs = abs_a + abs_b + abs_interaction

    if total_abs == 0:
        contrib_a = 50.0
        contrib_b = 50.0
        contrib_other = 0.0
    else:
        contrib_a = round((abs_a / total_abs) * 100.0, 1)
        contrib_b = round((abs_b / total_abs) * 100.0, 1)
        contrib_other = round(100.0 - (contrib_a + contrib_b), 1)

    pct_change_a = round((delta_a / factor_a_base) * 100.0, 2) if factor_a_base != 0 else 0.0
    pct_change_b = round((delta_b / factor_b_base) * 100.0, 2) if factor_b_base != 0 else 0.0

    drivers = [
        DriverContribution(
            kpi_key=factor_a_key,
            name=factor_a_name,
            change_pct=pct_change_a,
            contribution_pct=contrib_a,
            direction="down" if pct_change_a < 0 else "up" if pct_change_a > 0 else "neutral",
            raw_delta_impact=round(effect_a, 2),
        ),
        DriverContribution(
            kpi_key=factor_b_key,
            name=factor_b_name,
            change_pct=pct_change_b,
            contribution_pct=contrib_b,
            direction="down" if pct_change_b < 0 else "up" if pct_change_b > 0 else "neutral",
            raw_delta_impact=round(effect_b, 2),
        ),
    ]

    if contrib_other > 0:
        drivers.append(
            DriverContribution(
                kpi_key="interaction",
                name="Cross-Factor Interaction",
                change_pct=0.0,
                contribution_pct=contrib_other,
                direction="neutral",
                raw_delta_impact=round(interaction, 2),
            )
        )

    # Sort descending by contribution percentage
    drivers.sort(key=lambda d: d.contribution_pct, reverse=True)
    primary = drivers[0]

    return DriverAnalysisResult(
        target_kpi=target_name,
        target_change_pct=target_change_pct,
        primary_driver=primary.name,
        primary_contribution=primary.contribution_pct,
        drivers=drivers,
    )


def analyze_revenue_drivers(kpi_map: Dict[str, KPIResult]) -> Optional[DriverAnalysisResult]:
    """Deterministically breaks down Revenue into Level 1 (Orders vs AOV) and Level 2 (Sessions vs CR)."""
    rev = kpi_map.get("revenue")
    orders = kpi_map.get("orders")
    aov = kpi_map.get("aov")

    if not rev or not orders or not aov:
        return None

    # Level 1: Revenue = Orders * AOV
    level_1_res = decompose_multiplicative_pair(
        target_name="Revenue",
        target_change_pct=rev.change_pct,
        factor_a_key="orders",
        factor_a_name="Orders",
        factor_a_curr=orders.current_value,
        factor_a_base=orders.baseline_value,
        factor_b_key="aov",
        factor_b_name="Average Order Value (AOV)",
        factor_b_curr=aov.current_value,
        factor_b_base=aov.baseline_value,
    )

    # Level 2: If Orders is a dominant driver, decompose Orders = Sessions * Conversion Rate
    sessions = kpi_map.get("sessions")
    cr = kpi_map.get("conversion_rate")
    if sessions and cr and orders.change_pct != 0:
        # Conversion rate stored as percentage (e.g. 5.0), convert to decimal (0.05)
        level_2_res = decompose_multiplicative_pair(
            target_name="Orders",
            target_change_pct=orders.change_pct,
            factor_a_key="conversion_rate",
            factor_a_name="Conversion Rate",
            factor_a_curr=cr.current_value / 100.0,
            factor_a_base=cr.baseline_value / 100.0,
            factor_b_key="sessions",
            factor_b_name="Sessions",
            factor_b_curr=sessions.current_value,
            factor_b_base=sessions.baseline_value,
        )
        level_1_res.sub_driver_result = level_2_res

    return level_1_res
