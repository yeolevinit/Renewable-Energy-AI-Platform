"""ML training trigger endpoint."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


class TrainRequest(BaseModel):
    source_id: int
    target_col: str = "generation_kwh"
    include_weather: bool = True
    train_ratio: float = 0.70
    val_ratio: float = 0.15


@router.post("/train/solar")
def train_solar_models(payload: TrainRequest, db: Session = Depends(get_db)):
    """
    Trigger training of all solar generation forecasting models.

    Loads processed energy (and optionally weather) data from the database,
    engineers features, and trains linear regression, random forest, and XGBoost.
    Stores model artifacts and evaluation metrics.
    """
    import pandas as pd
    from sqlalchemy import text

    from app.analytics.anomaly_detector import (
        detect_residual_anomalies,
        detect_statistical_anomalies,
        save_alerts,
    )
    from app.ml.forecaster import train_solar_forecast_models
    from app.models.energy_observation import EnergyObservation
    from app.models.weather_observation import WeatherObservation

    # Load energy observations
    energy_rows = (
        db.query(EnergyObservation)
        .filter(
            EnergyObservation.source_id == payload.source_id,
            EnergyObservation.is_valid == True,
        )
        .order_by(EnergyObservation.observed_at)
        .all()
    )

    if len(energy_rows) < 100:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data: {len(energy_rows)} rows found. Need at least 100.",
        )

    df = pd.DataFrame(
        [
            {
                "observed_at": r.observed_at,
                "generation_kwh": r.generation_kwh,
                "ghi": r.ghi,
                "dni": r.dni,
                "dhi": r.dhi,
                "temperature_c": r.temperature_c,
            }
            for r in energy_rows
        ]
    )

    # Merge weather if available
    if payload.include_weather:
        weather_rows = (
            db.query(WeatherObservation)
            .filter(WeatherObservation.source_id == payload.source_id)
            .order_by(WeatherObservation.observed_at)
            .all()
        )
        if weather_rows:
            wdf = pd.DataFrame(
                [
                    {
                        "observed_at": r.observed_at,
                        "temperature_c": r.temperature_c,
                        "cloud_cover_pct": r.cloud_cover_pct,
                        "shortwave_radiation_wm2": r.shortwave_radiation_wm2,
                        "direct_radiation_wm2": r.direct_radiation_wm2,
                        "diffuse_radiation_wm2": r.diffuse_radiation_wm2,
                        "precipitation_mm": r.precipitation_mm,
                        "relative_humidity_pct": r.relative_humidity_pct,
                    }
                    for r in weather_rows
                ]
            )
            # Merge on nearest hour
            df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
            wdf["observed_at"] = pd.to_datetime(wdf["observed_at"], utc=True)
            df = pd.merge_asof(
                df.sort_values("observed_at"),
                wdf.sort_values("observed_at"),
                on="observed_at",
                tolerance=pd.Timedelta("1h"),
                suffixes=("", "_w"),
            )

    # Train all models
    results = train_solar_forecast_models(
        df=df,
        target_col=payload.target_col,
        include_weather=payload.include_weather,
        train_ratio=payload.train_ratio,
        val_ratio=payload.val_ratio,
    )

    # Run statistical anomaly detection on training data
    alerts = detect_statistical_anomalies(
        df=df,
        value_col=payload.target_col,
        series_type="solar_generation",
        source_id=payload.source_id,
    )
    saved_alerts = save_alerts(alerts)

    return {
        "status": "completed",
        "rows_used": len(df),
        "model_results": {
            k: v for k, v in results.items()
            if k not in ("feature_columns",)
        },
        "feature_count": len(results.get("feature_columns", [])),
        "split_dates": results.get("split_dates"),
        "anomalies_detected": saved_alerts,
        "note": (
            "All metrics are from the chronological held-out test set. "
            "Illustrative results only until experiment runs are verified."
        ),
    }
