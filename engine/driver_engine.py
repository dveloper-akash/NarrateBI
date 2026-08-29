"""Driver Engine - Deterministic driver contribution with correct impact direction.

Key correctness principles:
- Contribution magnitude (%) = how much of total movement is explained by this factor.
- Impact direction = the SIGNED direction of this factor's effect on the target KPI.
  These are separate concepts and must never be conflated.

For Revenue = Orders × AOV:
  delta_rev ≈ (delta_Orders × AOV_base) + (delta_AOV × Orders_base) + interaction

AOV increasing while Orders fall:
  - AOV effect is POSITIVE (it partially offsets the revenue decline)
  - Orders effect is NEGATIVE (it drives the revenue decline)
  - contribution_to_target for AOV > 0 regardless of whether AOV is "anomalous"

Exported fields per DriverContribution:
  - observed_change_pct  : % change of the driver itself
  - contribution_pct     : proportion of total absolute movement explained (0-100)
  - impact_direction     : 'positive' | 'negative' | 'neutral' — effect ON the target KPI
  - is_anomalous         : whether the driver's own change exceeds its threshold
  - contribution_to_target: signed raw delta impact on the target (same sign as effect)
  - raw_delta_impact     : same as contribution_to_target (kept for backward compat)
  - direction            : 'up' | 'down' | 'neutral' — direction of driver's OWN change
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from engine.kpi_engine import KPIResult


@dataclass
class DriverContribution:
    kpi_key: str
    name: str
    # Driver's own movement
    observed_change_pct: float        # % change in this driver (e.g. AOV +18%)
    is_anomalous: bool                # driver's own change exceeds its threshold
    direction: str                    # 'up' | 'down' | 'neutral' (driver's own direction)

    # Effect on the TARGET KPI
    contribution_pct: float           # magnitude share (always >= 0, sums to 100%)
    impact_direction: str             # 'positive' | 'negative' | 'neutral' ON the target
    contribution_to_target: float     # signed raw delta impact on target

    # Backward compatibility alias
    @property
    def change_pct(self) -> float:
        return self.observed_change_pct

    @property
    def raw_delta_impact(self) -> float:
        return self.contribution_to_target


@dataclass
class DriverAnalysisResult:
    target_kpi: str
    target_change_pct: float
    primary_driver: str           # driver with largest contribution
    primary_contribution: float   # its contribution_pct
    primary_impact_direction: str  # 'positive' | 'negative' | 'neutral'
    drivers: List[DriverContribution]
    decomposition_method: str = "multiplicative_first_order"
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
    contracts: Optional[Dict] = None,
) -> DriverAnalysisResult:
    """First-order multiplicative decomposition.

    For target T = A × B:
      delta_T ≈ delta_A × B_base + delta_B × A_base + delta_A × delta_B (interaction)

    effect_a = delta_a × B_base   → may be positive or negative
    effect_b = delta_b × A_base   → may be positive or negative

    contribution_pct uses |effect| to show magnitude share.
    impact_direction uses sign(effect) to show whether the factor helped or hurt T.
    """
    delta_a = factor_a_curr - factor_a_base
    delta_b = factor_b_curr - factor_b_base

    # First-order marginal effects (signed)
    effect_a = delta_a * factor_b_base        # signed: positive = helped target
    effect_b = delta_b * factor_a_base        # signed: positive = helped target
    interaction = delta_a * delta_b           # signed

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

    # Anomaly check from contracts (optional)
    threshold_a = contracts[factor_a_key].threshold if contracts and factor_a_key in contracts else 10.0
    threshold_b = contracts[factor_b_key].threshold if contracts and factor_b_key in contracts else 10.0

    def _impact_dir(effect: float) -> str:
        if effect > 0:
            return "positive"
        elif effect < 0:
            return "negative"
        return "neutral"

    drivers = [
        DriverContribution(
            kpi_key=factor_a_key,
            name=factor_a_name,
            observed_change_pct=pct_change_a,
            is_anomalous=abs(pct_change_a) >= threshold_a,
            direction="down" if pct_change_a < 0 else "up" if pct_change_a > 0 else "neutral",
            contribution_pct=contrib_a,
            impact_direction=_impact_dir(effect_a),
            contribution_to_target=round(effect_a, 2),
        ),
        DriverContribution(
            kpi_key=factor_b_key,
            name=factor_b_name,
            observed_change_pct=pct_change_b,
            is_anomalous=abs(pct_change_b) >= threshold_b,
            direction="down" if pct_change_b < 0 else "up" if pct_change_b > 0 else "neutral",
            contribution_pct=contrib_b,
            impact_direction=_impact_dir(effect_b),
            contribution_to_target=round(effect_b, 2),
        ),
    ]

    if contrib_other > 0:
        drivers.append(
            DriverContribution(
                kpi_key="interaction",
                name="Cross-Factor Interaction",
                observed_change_pct=0.0,
                is_anomalous=False,
                direction="neutral",
                contribution_pct=contrib_other,
                impact_direction=_impact_dir(interaction),
                contribution_to_target=round(interaction, 2),
            )
        )

    # Sort by contribution magnitude (largest first)
    drivers.sort(key=lambda d: d.contribution_pct, reverse=True)
    primary = drivers[0]

    return DriverAnalysisResult(
        target_kpi=target_name,
        target_change_pct=target_change_pct,
        primary_driver=primary.name,
        primary_contribution=primary.contribution_pct,
        primary_impact_direction=primary.impact_direction,
        drivers=drivers,
        decomposition_method="multiplicative_first_order",
    )


def analyze_revenue_drivers(
    kpi_map: Dict[str, KPIResult],
    contracts: Optional[Dict] = None,
) -> Optional[DriverAnalysisResult]:
    """Hierarchical revenue decomposition.

    Level 1: Revenue = Orders × AOV
    Level 2 (if Orders is significant): Orders = Sessions × Conversion Rate

    Passes contracts for per-driver anomaly threshold lookup.
    """
    rev = kpi_map.get("revenue")
    orders = kpi_map.get("orders")
    aov = kpi_map.get("aov")

    if not rev or not orders or not aov:
        return None

    # Load contracts if not passed
    if contracts is None:
        try:
            from engine.kpi_engine import load_kpi_contracts
            contracts = load_kpi_contracts()
        except Exception:
            contracts = {}

    # Level 1: Revenue = Orders × AOV
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
        contracts=contracts,
    )

    # Level 2: Decompose Orders = Sessions × Conversion Rate (if meaningful)
    sessions = kpi_map.get("sessions")
    cr = kpi_map.get("conversion_rate")
    if sessions and cr and orders.change_pct != 0:
        level_2_res = decompose_multiplicative_pair(
            target_name="Orders",
            target_change_pct=orders.change_pct,
            factor_a_key="conversion_rate",
            factor_a_name="Conversion Rate",
            # CR stored as % (e.g. 5.0), need absolute units for decomposition
            factor_a_curr=cr.current_value / 100.0,
            factor_a_base=cr.baseline_value / 100.0,
            factor_b_key="sessions",
            factor_b_name="Sessions",
            factor_b_curr=sessions.current_value,
            factor_b_base=sessions.baseline_value,
            contracts=contracts,
        )
        level_1_res.sub_driver_result = level_2_res

    return level_1_res


def get_negative_contributors(result: DriverAnalysisResult) -> List[DriverContribution]:
    """Returns drivers with negative impact on the target, sorted by magnitude."""
    return sorted(
        [d for d in result.drivers if d.impact_direction == "negative"],
        key=lambda d: d.contribution_pct,
        reverse=True,
    )


def get_positive_contributors(result: DriverAnalysisResult) -> List[DriverContribution]:
    """Returns drivers with positive impact on the target, sorted by magnitude."""
    return sorted(
        [d for d in result.drivers if d.impact_direction == "positive"],
        key=lambda d: d.contribution_pct,
        reverse=True,
    )
