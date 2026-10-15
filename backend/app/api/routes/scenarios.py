"""Energy balance and what-if scenario endpoints."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.energy_balance import run_scenario
from app.db.database import get_db
from app.models.energy_observation import EnergyObservation
from app.models.demand_observation import DemandObservation
from app.models.forecast import Forecast
from app.models.scenario import Scenario
from app.schemas.analytics import ScenarioRequest, ScenarioResponse

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def _load_generation_df(db: Session, start: str, end: str):
    """Load solar generation forecasts as a DataFrame for scenario use."""
    import pandas as pd

    rows = (
        db.query(Forecast)
        .filter(
            Forecast.forecast_type == "solar_generation",
            Forecast.forecast_for >= start,
            Forecast.forecast_for <= end,
        )
        .order_by(Forecast.forecast_for)
        .all()
    )

    if not rows:
        # Fall back to actual observations
        obs_rows = (
            db.query(EnergyObservation)
            .filter(
                EnergyObservation.observed_at >= start,
                EnergyObservation.observed_at <= end,
                EnergyObservation.is_valid == True,
            )
            .order_by(EnergyObservation.observed_at)
            .all()
        )
        if not obs_rows:
            return None
        return pd.DataFrame(
            [{"observed_at": r.observed_at, "generation_kwh": r.generation_kwh} for r in obs_rows]
        )

    return pd.DataFrame(
        [
            {
                "observed_at": r.forecast_for,
                "generation_kwh": r.predicted_value,
            }
            for r in rows
        ]
    )


def _load_demand_df(db: Session, start: str, end: str):
    """Load demand observations as a DataFrame, or None if unavailable."""
    import pandas as pd

    rows = (
        db.query(DemandObservation)
        .filter(
            DemandObservation.observed_at >= start,
            DemandObservation.observed_at <= end,
            DemandObservation.is_valid == True,
        )
        .order_by(DemandObservation.observed_at)
        .all()
    )
    if not rows:
        return None
    return pd.DataFrame(
        [{"observed_at": r.observed_at, "demand_kwh": r.demand_kwh} for r in rows]
    )


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(payload: ScenarioRequest, db: Session = Depends(get_db)):
    """
    Run a what-if energy balance scenario.

    Uses stored generation forecasts (or historical observations as fallback)
    and demand data (if available) over the specified date range.

    All results are labelled as simulated outputs based on stated assumptions.
    """
    gen_df = _load_generation_df(db, payload.analysis_start, payload.analysis_end)
    if gen_df is None or len(gen_df) == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "No generation data found for the specified date range. "
                "Run ingestion and train forecasting models first."
            ),
        )

    dem_df = _load_demand_df(db, payload.analysis_start, payload.analysis_end)

    result = run_scenario(
        scenario_name=payload.name,
        generation_df=gen_df,
        demand_df=dem_df,
        generation_adjustment_pct=payload.generation_adjustment_pct,
        demand_adjustment_pct=payload.demand_adjustment_pct,
        analysis_start=payload.analysis_start,
        analysis_end=payload.analysis_end,
    )

    # Persist the scenario
    scenario = Scenario(
        name=result["scenario_name"],
        description=payload.description,
        analysis_start=payload.analysis_start,
        analysis_end=payload.analysis_end,
        assumptions=json.dumps(result["assumptions"]),
        total_generation_kwh=result["total_generation_kwh"],
        total_demand_kwh=result["total_demand_kwh"],
        net_balance_kwh=result["net_balance_kwh"],
        balance_status=result["balance_status"],
        result_series=json.dumps(result.get("interval_series") or []),
        recommendation=result["recommendation"],
    )
    db.add(scenario)
    db.flush()

    return scenario


@router.get("", response_model=List[ScenarioResponse])
def list_scenarios(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return saved scenario results, newest first."""
    return (
        db.query(Scenario)
        .order_by(Scenario.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Return a specific scenario with full interval series."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "analysis_start": scenario.analysis_start,
        "analysis_end": scenario.analysis_end,
        "assumptions": json.loads(scenario.assumptions) if scenario.assumptions else {},
        "total_generation_kwh": scenario.total_generation_kwh,
        "total_demand_kwh": scenario.total_demand_kwh,
        "net_balance_kwh": scenario.net_balance_kwh,
        "balance_status": scenario.balance_status,
        "recommendation": scenario.recommendation,
        "result_series": json.loads(scenario.result_series) if scenario.result_series else [],
        "created_at": scenario.created_at,
    }
