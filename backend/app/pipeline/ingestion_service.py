"""
Ingestion service — orchestrates reading → validating → transforming → loading.

Supports ingestion of:
  - CSV files (solar generation, weather, demand)
  - Open-Meteo historical weather API
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import db_session
from app.models.pipeline_run import PipelineRun
from app.models.data_quality_report import DataQualityReport
from app.pipeline.loaders import load_solar_generation, load_weather, load_demand
from app.pipeline.quality_engine import build_quality_report
from app.pipeline.transformers import (
    transform_demand,
    transform_solar_generation,
    transform_weather,
)
from app.pipeline.validator import validate_dataframe

logger = get_logger(__name__)
settings = get_settings()


# ─── Pipeline run helpers ────────────────────────────────────────────────────

def _start_run(db, source_id: int, stage: str) -> PipelineRun:
    run = PipelineRun(
        source_id=source_id,
        status="running",
        started_at=datetime.now(timezone.utc),
        pipeline_stage=stage,
    )
    db.add(run)
    db.flush()  # get run.id without committing
    return run


def _finish_run(
    db,
    run: PipelineRun,
    rows_read: int,
    rows_written: int,
    rows_rejected: int,
    error: Optional[str] = None,
) -> None:
    run.status = "failed" if error else "completed"
    run.completed_at = datetime.now(timezone.utc)
    run.rows_read = rows_read
    run.rows_written = rows_written
    run.rows_rejected = rows_rejected
    run.error_summary = error


# ─── CSV ingestion ───────────────────────────────────────────────────────────

def ingest_solar_csv(
    file_path: str,
    source_id: int,
    timestamp_col: str = "timestamp",
    generation_col: str = "generation_kwh",
    ghi_col: Optional[str] = None,
    dni_col: Optional[str] = None,
    dhi_col: Optional[str] = None,
    temperature_col: Optional[str] = None,
    site_id: Optional[str] = None,
    unit: str = "kWh",
    expected_interval: str = "hourly",
) -> Dict:
    """
    Ingest a solar generation CSV file.

    Returns a summary dict with run_id, rows_written, quality_score, issues.
    """
    logger.info("ingest_solar_csv_start", file=file_path, source_id=source_id)

    with db_session() as db:
        run = _start_run(db, source_id, "solar_csv_ingestion")
        run_id = run.id

        try:
            raw_df = pd.read_csv(file_path)
            rows_read = len(raw_df)

            cleaned_df, val_result = validate_dataframe(
                raw_df,
                required_columns=[timestamp_col, generation_col],
                timestamp_col=timestamp_col,
                expected_interval=expected_interval,
                source_name=f"solar_source_{source_id}",
            )

            records = transform_solar_generation(
                cleaned_df,
                source_id=source_id,
                pipeline_run_id=run_id,
                generation_col=generation_col,
                ghi_col=ghi_col,
                dni_col=dni_col,
                dhi_col=dhi_col,
                temperature_col=temperature_col,
                site_id=site_id,
                unit=unit,
            )

            rows_written = load_solar_generation(db, records)
            rows_rejected = rows_read - len(cleaned_df)

            # Save quality report
            qr_dict = build_quality_report(val_result, run_id, source_id)
            qr = DataQualityReport(**qr_dict)
            db.add(qr)

            _finish_run(db, run, rows_read, rows_written, rows_rejected)

        except Exception as exc:
            logger.error("ingest_solar_csv_failed", error=str(exc))
            _finish_run(db, run, 0, 0, 0, error=str(exc))
            raise

    return {
        "run_id": run_id,
        "rows_read": rows_read,
        "rows_written": rows_written,
        "rows_rejected": rows_rejected,
        "quality_score": qr_dict.get("quality_score"),
        "issues": val_result.issues,
        "warnings": val_result.warnings,
    }


def ingest_weather_csv(
    file_path: str,
    source_id: int,
    timestamp_col: str = "timestamp",
    location_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    col_map: Optional[Dict[str, str]] = None,
    expected_interval: str = "hourly",
) -> Dict:
    """
    Ingest a weather CSV file.
    """
    logger.info("ingest_weather_csv_start", file=file_path, source_id=source_id)

    with db_session() as db:
        run = _start_run(db, source_id, "weather_csv_ingestion")
        run_id = run.id

        try:
            raw_df = pd.read_csv(file_path)
            rows_read = len(raw_df)

            cleaned_df, val_result = validate_dataframe(
                raw_df,
                required_columns=[timestamp_col],
                timestamp_col=timestamp_col,
                expected_interval=expected_interval,
                source_name=f"weather_source_{source_id}",
            )

            records = transform_weather(
                cleaned_df,
                source_id=source_id,
                pipeline_run_id=run_id,
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                col_map=col_map or {},
            )

            rows_written = load_weather(db, records)
            rows_rejected = rows_read - len(cleaned_df)

            qr_dict = build_quality_report(val_result, run_id, source_id)
            qr = DataQualityReport(**qr_dict)
            db.add(qr)

            _finish_run(db, run, rows_read, rows_written, rows_rejected)

        except Exception as exc:
            logger.error("ingest_weather_csv_failed", error=str(exc))
            _finish_run(db, run, 0, 0, 0, error=str(exc))
            raise

    return {
        "run_id": run_id,
        "rows_read": rows_read,
        "rows_written": rows_written,
        "rows_rejected": rows_rejected,
        "quality_score": qr_dict.get("quality_score"),
        "issues": val_result.issues,
        "warnings": val_result.warnings,
    }


# ─── Open-Meteo weather API ingestion ────────────────────────────────────────

OPEN_METEO_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "cloudcover",
    "windspeed_10m",
    "winddirection_10m",
    "relativehumidity_2m",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
]

_OPEN_METEO_COL_MAP = {
    "temperature_c": "temperature_2m",
    "precipitation_mm": "precipitation",
    "cloud_cover_pct": "cloudcover",
    "wind_speed_ms": "windspeed_10m",
    "wind_direction_deg": "winddirection_10m",
    "relative_humidity_pct": "relativehumidity_2m",
    "shortwave_radiation_wm2": "shortwave_radiation",
    "direct_radiation_wm2": "direct_radiation",
    "diffuse_radiation_wm2": "diffuse_radiation",
}


def ingest_open_meteo(
    source_id: int,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    location_id: Optional[str] = None,
) -> Dict:
    """
    Fetch and ingest historical weather data from the Open-Meteo archive API.

    Dates are ISO strings: "2022-01-01".
    Open-Meteo is free for non-commercial use; no API key required.
    Reference: https://open-meteo.com/en/docs/historical-weather-api
    """
    logger.info(
        "ingest_open_meteo_start",
        lat=latitude,
        lon=longitude,
        start=start_date,
        end=end_date,
    )

    url = settings.open_meteo_base_url
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(OPEN_METEO_VARIABLES),
        "timezone": "UTC",
    }

    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    df = pd.DataFrame(hourly)

    # Rename 'time' → timestamp
    if "time" in df.columns:
        df = df.rename(columns={"time": "timestamp"})

    with db_session() as db:
        run = _start_run(db, source_id, "open_meteo_api_ingestion")
        run_id = run.id

        try:
            rows_read = len(df)

            cleaned_df, val_result = validate_dataframe(
                df,
                required_columns=["timestamp"],
                timestamp_col="timestamp",
                expected_interval="hourly",
                source_name=f"open_meteo_{location_id}",
            )

            # Rename Open-Meteo columns to canonical names
            rename = {v: k for k, v in _OPEN_METEO_COL_MAP.items()}
            cleaned_df = cleaned_df.rename(columns=rename)

            records = transform_weather(
                cleaned_df,
                source_id=source_id,
                pipeline_run_id=run_id,
                location_id=location_id or f"{latitude},{longitude}",
                latitude=latitude,
                longitude=longitude,
            )

            rows_written = load_weather(db, records)
            rows_rejected = rows_read - len(cleaned_df)

            qr_dict = build_quality_report(val_result, run_id, source_id)
            qr = DataQualityReport(**qr_dict)
            db.add(qr)

            _finish_run(db, run, rows_read, rows_written, rows_rejected)

        except Exception as exc:
            logger.error("ingest_open_meteo_failed", error=str(exc))
            _finish_run(db, run, 0, 0, 0, error=str(exc))
            raise

    return {
        "run_id": run_id,
        "rows_read": rows_read,
        "rows_written": rows_written,
        "rows_rejected": rows_rejected,
        "quality_score": qr_dict.get("quality_score"),
        "issues": val_result.issues,
        "warnings": val_result.warnings,
    }
