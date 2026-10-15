"""Historical generation and weather analytics endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.energy_observation import EnergyObservation
from app.models.weather_observation import WeatherObservation
from app.schemas.analytics import GenerationPoint

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/generation", response_model=List[GenerationPoint])
def get_generation_series(
    source_id: Optional[int] = Query(None),
    site_id: Optional[str] = Query(None),
    start: Optional[str] = Query(None, description="ISO date string, e.g. 2022-01-01"),
    end: Optional[str] = Query(None, description="ISO date string, e.g. 2022-12-31"),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Return historical solar generation observations."""
    q = db.query(EnergyObservation).filter(EnergyObservation.is_valid == True)

    if source_id is not None:
        q = q.filter(EnergyObservation.source_id == source_id)
    if site_id is not None:
        q = q.filter(EnergyObservation.site_id == site_id)
    if start:
        q = q.filter(EnergyObservation.observed_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(EnergyObservation.observed_at <= datetime.fromisoformat(end))

    return (
        q.order_by(EnergyObservation.observed_at)
        .limit(limit)
        .all()
    )


@router.get("/generation/summary")
def get_generation_summary(
    source_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return aggregate statistics for generation data."""
    q = db.query(EnergyObservation).filter(EnergyObservation.is_valid == True)
    if source_id:
        q = q.filter(EnergyObservation.source_id == source_id)

    agg = db.query(
        func.count(EnergyObservation.id).label("total_rows"),
        func.min(EnergyObservation.observed_at).label("earliest"),
        func.max(EnergyObservation.observed_at).label("latest"),
        func.avg(EnergyObservation.generation_kwh).label("mean_kwh"),
        func.sum(EnergyObservation.generation_kwh).label("total_kwh"),
        func.max(EnergyObservation.generation_kwh).label("max_kwh"),
    )
    if source_id:
        agg = agg.filter(EnergyObservation.source_id == source_id)

    row = agg.first()
    return {
        "total_rows": row.total_rows or 0,
        "earliest": str(row.earliest) if row.earliest else None,
        "latest": str(row.latest) if row.latest else None,
        "mean_generation_kwh": round(float(row.mean_kwh), 4) if row.mean_kwh else None,
        "total_generation_kwh": round(float(row.total_kwh), 2) if row.total_kwh else None,
        "max_generation_kwh": round(float(row.max_kwh), 4) if row.max_kwh else None,
    }


@router.get("/weather")
def get_weather_series(
    source_id: Optional[int] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Return historical weather observations."""
    q = db.query(WeatherObservation).filter(WeatherObservation.is_valid == True)

    if source_id:
        q = q.filter(WeatherObservation.source_id == source_id)
    if start:
        q = q.filter(WeatherObservation.observed_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(WeatherObservation.observed_at <= datetime.fromisoformat(end))

    rows = q.order_by(WeatherObservation.observed_at).limit(limit).all()
    return [
        {
            "observed_at": r.observed_at,
            "temperature_c": r.temperature_c,
            "cloud_cover_pct": r.cloud_cover_pct,
            "shortwave_radiation_wm2": r.shortwave_radiation_wm2,
            "precipitation_mm": r.precipitation_mm,
            "wind_speed_ms": r.wind_speed_ms,
            "relative_humidity_pct": r.relative_humidity_pct,
        }
        for r in rows
    ]


@router.get("/weather/summary")
def get_weather_summary(
    source_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return aggregate weather statistics."""
    q = db.query(WeatherObservation)
    if source_id:
        q = q.filter(WeatherObservation.source_id == source_id)

    agg = db.query(
        func.count(WeatherObservation.id).label("total_rows"),
        func.min(WeatherObservation.observed_at).label("earliest"),
        func.max(WeatherObservation.observed_at).label("latest"),
        func.avg(WeatherObservation.temperature_c).label("mean_temp"),
        func.avg(WeatherObservation.cloud_cover_pct).label("mean_cloud"),
        func.avg(WeatherObservation.shortwave_radiation_wm2).label("mean_radiation"),
    )
    if source_id:
        agg = agg.filter(WeatherObservation.source_id == source_id)

    row = agg.first()
    return {
        "total_rows": row.total_rows or 0,
        "earliest": str(row.earliest) if row.earliest else None,
        "latest": str(row.latest) if row.latest else None,
        "mean_temperature_c": round(float(row.mean_temp), 2) if row.mean_temp else None,
        "mean_cloud_cover_pct": round(float(row.mean_cloud), 2) if row.mean_cloud else None,
        "mean_shortwave_radiation_wm2": round(float(row.mean_radiation), 2) if row.mean_radiation else None,
    }
