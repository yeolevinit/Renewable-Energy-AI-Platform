"""
Energy balance and what-if scenario analysis.

IMPORTANT: Generation-demand comparisons are only performed when
generation and demand series share compatible:
  - Time intervals and resolution
  - Units (all values must be in kWh over the same interval)
  - Geographic/system boundaries (explicitly assumed by the user)

This module is advisory only. It does not operate real equipment
and cannot guarantee energy savings or confirm physical shortages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EnergyBalanceResult:
    """Result of an energy balance calculation over a time window."""
    total_generation_kwh: float
    total_demand_kwh: float
    net_balance_kwh: float          # generation - demand (positive = surplus)
    balance_status: str             # "surplus" | "deficit" | "balanced" | "generation_only"
    surplus_periods: int            # count of intervals where gen > demand
    deficit_periods: int            # count of intervals where demand > gen
    assumptions: Dict = field(default_factory=dict)
    recommendation: str = ""
    interval_series: Optional[pd.DataFrame] = None  # per-interval breakdown


def calculate_energy_balance(
    generation_df: pd.DataFrame,
    demand_df: Optional[pd.DataFrame],
    generation_col: str = "generation_kwh",
    demand_col: str = "demand_kwh",
    timestamp_col: str = "observed_at",
    generation_adjustment_pct: float = 0.0,
    demand_adjustment_pct: float = 0.0,
    unit: str = "kWh",
) -> EnergyBalanceResult:
    """
    Calculate the energy balance between generation and demand.

    If demand_df is None, returns a generation-only summary.

    generation_adjustment_pct: % change applied to all generation values
        (e.g., -20 to simulate a 20% generation reduction).
    demand_adjustment_pct: % change applied to all demand values.

    All values must already be in the same unit (kWh recommended).
    Time alignment is done by inner-joining on the timestamp column.
    """
    assumptions = {
        "generation_adjustment_pct": generation_adjustment_pct,
        "demand_adjustment_pct": demand_adjustment_pct,
        "unit": unit,
        "note": (
            "This is a simulated analysis using model forecasts or historical data. "
            "Compatibility of geographic scope and system boundaries is assumed by the user."
        ),
    }

    # Apply generation adjustment
    gen = generation_df[[timestamp_col, generation_col]].copy()
    gen[generation_col] = gen[generation_col] * (1 + generation_adjustment_pct / 100)
    gen[generation_col] = gen[generation_col].clip(lower=0)

    if demand_df is None:
        total_gen = float(gen[generation_col].sum())
        return EnergyBalanceResult(
            total_generation_kwh=total_gen,
            total_demand_kwh=0.0,
            net_balance_kwh=total_gen,
            balance_status="generation_only",
            surplus_periods=0,
            deficit_periods=0,
            assumptions=assumptions,
            recommendation=(
                "Demand data is not available for this analysis. "
                "Showing generation summary only."
            ),
        )

    # Apply demand adjustment
    dem = demand_df[[timestamp_col, demand_col]].copy()
    dem[demand_col] = dem[demand_col] * (1 + demand_adjustment_pct / 100)
    dem[demand_col] = dem[demand_col].clip(lower=0)

    # Align on timestamp (inner join)
    merged = pd.merge(
        gen.rename(columns={generation_col: "gen_kwh"}),
        dem.rename(columns={demand_col: "dem_kwh"}),
        on=timestamp_col,
        how="inner",
    )

    if len(merged) == 0:
        logger.warning("energy_balance_no_overlap")
        return EnergyBalanceResult(
            total_generation_kwh=0.0,
            total_demand_kwh=0.0,
            net_balance_kwh=0.0,
            balance_status="generation_only",
            surplus_periods=0,
            deficit_periods=0,
            assumptions=assumptions,
            recommendation=(
                "Generation and demand series have no overlapping timestamps. "
                "Ensure both datasets cover the same time period."
            ),
        )

    merged["net_kwh"] = merged["gen_kwh"] - merged["dem_kwh"]
    total_gen = float(merged["gen_kwh"].sum())
    total_dem = float(merged["dem_kwh"].sum())
    net = float(merged["net_kwh"].sum())
    surplus_periods = int((merged["net_kwh"] > 0).sum())
    deficit_periods = int((merged["net_kwh"] < 0).sum())

    if abs(net) < 0.01 * max(total_gen, total_dem, 1):
        status = "balanced"
    elif net > 0:
        status = "surplus"
    else:
        status = "deficit"

    recommendation = _build_recommendation(net, total_gen, total_dem, status)

    logger.info(
        "energy_balance_calculated",
        total_gen=total_gen,
        total_dem=total_dem,
        net=net,
        status=status,
        n_periods=len(merged),
    )

    return EnergyBalanceResult(
        total_generation_kwh=total_gen,
        total_demand_kwh=total_dem,
        net_balance_kwh=net,
        balance_status=status,
        surplus_periods=surplus_periods,
        deficit_periods=deficit_periods,
        assumptions=assumptions,
        recommendation=recommendation,
        interval_series=merged,
    )


def _build_recommendation(
    net: float,
    total_gen: float,
    total_dem: float,
    status: str,
) -> str:
    """Generate a transparent, appropriately caveated recommendation."""
    pct = abs(net) / max(total_dem, 1) * 100

    if status == "surplus":
        return (
            f"Predicted generation exceeds predicted demand by {net:.0f} kWh "
            f"({pct:.1f}% of demand). Consider exploring storage or other use for "
            "potential surplus periods under these assumptions."
        )
    elif status == "deficit":
        deficit = -net
        return (
            f"Predicted demand exceeds predicted renewable generation by {deficit:.0f} kWh "
            f"({pct:.1f}% of demand). Review alternative supply options, storage availability, "
            "or feasible demand-shifting under these system assumptions."
        )
    else:
        return (
            "Predicted generation and demand are approximately balanced "
            "under these assumptions."
        )


# ─── What-if scenario simulation ─────────────────────────────────────────────

def run_scenario(
    scenario_name: str,
    generation_df: pd.DataFrame,
    demand_df: Optional[pd.DataFrame],
    generation_adjustment_pct: float = 0.0,
    demand_adjustment_pct: float = 0.0,
    timestamp_col: str = "observed_at",
    analysis_start: Optional[str] = None,
    analysis_end: Optional[str] = None,
) -> Dict:
    """
    Run a what-if scenario and return a result dict suitable for API response
    or database storage.

    Clearly marks all outputs as simulated assumptions, not observations.
    """
    # Apply date window if specified
    if analysis_start:
        generation_df = generation_df[
            generation_df[timestamp_col] >= pd.Timestamp(analysis_start, tz="UTC")
        ]
        if demand_df is not None:
            demand_df = demand_df[
                demand_df[timestamp_col] >= pd.Timestamp(analysis_start, tz="UTC")
            ]

    if analysis_end:
        generation_df = generation_df[
            generation_df[timestamp_col] <= pd.Timestamp(analysis_end, tz="UTC")
        ]
        if demand_df is not None:
            demand_df = demand_df[
                demand_df[timestamp_col] <= pd.Timestamp(analysis_end, tz="UTC")
            ]

    result = calculate_energy_balance(
        generation_df=generation_df,
        demand_df=demand_df,
        generation_adjustment_pct=generation_adjustment_pct,
        demand_adjustment_pct=demand_adjustment_pct,
    )

    # Build interval series JSON (limit to 500 rows for API response size)
    interval_json = None
    if result.interval_series is not None:
        series = result.interval_series.copy()
        series[timestamp_col] = series[timestamp_col].astype(str)
        if len(series) > 500:
            # Downsample to daily for large ranges
            series = series.set_index(timestamp_col).resample("D").sum().reset_index()
        interval_json = series.to_dict(orient="records")

    return {
        "scenario_name": scenario_name,
        "is_simulated": True,
        "analysis_start": str(analysis_start or ""),
        "analysis_end": str(analysis_end or ""),
        "assumptions": result.assumptions,
        "total_generation_kwh": round(result.total_generation_kwh, 2),
        "total_demand_kwh": round(result.total_demand_kwh, 2),
        "net_balance_kwh": round(result.net_balance_kwh, 2),
        "balance_status": result.balance_status,
        "surplus_periods": result.surplus_periods,
        "deficit_periods": result.deficit_periods,
        "recommendation": result.recommendation,
        "interval_series": interval_json,
    }
