"""Pipeline ingestion and run-history endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.pipeline_run import PipelineRun
from app.pipeline.ingestion_service import (
    ingest_open_meteo,
    ingest_solar_csv,
    ingest_weather_csv,
)
from app.schemas.pipeline import (
    IngestCSVRequest,
    IngestOpenMeteoRequest,
    PipelineRunResponse,
    PipelineRunResult,
)

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("/runs", response_model=List[PipelineRunResponse])
def list_pipeline_runs(
    source_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return recent pipeline run history, newest first."""
    q = db.query(PipelineRun)
    if source_id is not None:
        q = q.filter(PipelineRun.source_id == source_id)
    return q.order_by(PipelineRun.created_at.desc()).limit(limit).all()


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


@router.post("/ingest/solar-csv", response_model=PipelineRunResult)
def ingest_solar(payload: IngestCSVRequest):
    """
    Ingest a solar generation CSV file.

    The file must be accessible at the given path on the server.
    Returns a pipeline run summary including quality score and any issues.
    """
    try:
        result = ingest_solar_csv(
            file_path=payload.file_path,
            source_id=payload.source_id,
            timestamp_col=payload.timestamp_col,
            generation_col=payload.generation_col,
            ghi_col=payload.ghi_col,
            dni_col=payload.dni_col,
            dhi_col=payload.dhi_col,
            temperature_col=payload.temperature_col,
            site_id=payload.site_id,
            unit=payload.unit,
            expected_interval=payload.expected_interval,
        )
        return PipelineRunResult(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {payload.file_path}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest/weather-csv", response_model=PipelineRunResult)
def ingest_weather(
    file_path: str,
    source_id: int,
    timestamp_col: str = "timestamp",
    location_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
):
    """Ingest a weather CSV file."""
    try:
        result = ingest_weather_csv(
            file_path=file_path,
            source_id=source_id,
            timestamp_col=timestamp_col,
            location_id=location_id,
            latitude=latitude,
            longitude=longitude,
        )
        return PipelineRunResult(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest/open-meteo", response_model=PipelineRunResult)
def ingest_meteo(payload: IngestOpenMeteoRequest):
    """
    Fetch and ingest historical weather data from the Open-Meteo archive API.

    No API key required. Dates must be ISO format: YYYY-MM-DD.
    Coverage: typically available from 1940 to recent days.
    """
    try:
        result = ingest_open_meteo(
            source_id=payload.source_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            start_date=payload.start_date,
            end_date=payload.end_date,
            location_id=payload.location_id,
        )
        return PipelineRunResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
