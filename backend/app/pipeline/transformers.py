"""
Data transformation functions.

Converts validated DataFrames into standardized structures
ready for database insertion.  Each transformer returns a list
of dicts that can be bulk-inserted via SQLAlchemy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


def _safe_float(val: Any) -> Optional[float]:
    """Return float or None — avoids inserting NaN into the database."""
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


# ─── Solar / generation transformer ─────────────────────────────────────────

def transform_solar_generation(
    df: pd.DataFrame,
    source_id: int,
    pipeline_run_id: Optional[int],
    generation_col: str = "generation_kwh",
    ghi_col: Optional[str] = None,
    dni_col: Optional[str] = None,
    dhi_col: Optional[str] = None,
    temperature_col: Optional[str] = None,
    power_col: Optional[str] = None,
    site_id: Optional[str] = None,
    unit: str = "kWh",
) -> List[Dict]:
    """
    Transform a validated solar DataFrame to energy_observations dicts.
    """
    records: List[Dict] = []

    for _, row in df.iterrows():
        rec: Dict[str, Any] = {
            "source_id": source_id,
            "pipeline_run_id": pipeline_run_id,
            "observed_at": row["observed_at"],
            "site_id": site_id or str(row.get("site_id", "")) or None,
            "generation_kwh": _safe_float(row.get(generation_col)),
            "power_kw": _safe_float(row.get(power_col)) if power_col else None,
            "ghi": _safe_float(row.get(ghi_col)) if ghi_col else None,
            "dni": _safe_float(row.get(dni_col)) if dni_col else None,
            "dhi": _safe_float(row.get(dhi_col)) if dhi_col else None,
            "temperature_c": _safe_float(row.get(temperature_col)) if temperature_col else None,
            "unit": unit,
            "is_valid": True,
        }
        records.append(rec)

    logger.info("transform_solar_generation", records=len(records))
    return records


# ─── Weather transformer ──────────────────────────────────────────────────────

def transform_weather(
    df: pd.DataFrame,
    source_id: int,
    pipeline_run_id: Optional[int],
    location_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    col_map: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Transform a validated weather DataFrame to weather_observations dicts.

    col_map maps DataFrame column names → canonical field names, e.g.:
        {"temp": "temperature_c", "cloud": "cloud_cover_pct"}
    """
    col_map = col_map or {}

    # Build reverse mapping: canonical → actual col name
    def _get(row: pd.Series, canonical: str) -> Optional[float]:
        actual = col_map.get(canonical, canonical)
        if actual in row.index:
            return _safe_float(row[actual])
        return None

    records: List[Dict] = []
    for _, row in df.iterrows():
        rec: Dict[str, Any] = {
            "source_id": source_id,
            "pipeline_run_id": pipeline_run_id,
            "observed_at": row["observed_at"],
            "location_id": location_id,
            "latitude": latitude,
            "longitude": longitude,
            "temperature_c": _get(row, "temperature_c"),
            "cloud_cover_pct": _get(row, "cloud_cover_pct"),
            "precipitation_mm": _get(row, "precipitation_mm"),
            "wind_speed_ms": _get(row, "wind_speed_ms"),
            "wind_direction_deg": _get(row, "wind_direction_deg"),
            "relative_humidity_pct": _get(row, "relative_humidity_pct"),
            "shortwave_radiation_wm2": _get(row, "shortwave_radiation_wm2"),
            "direct_radiation_wm2": _get(row, "direct_radiation_wm2"),
            "diffuse_radiation_wm2": _get(row, "diffuse_radiation_wm2"),
            "is_valid": True,
        }
        records.append(rec)

    logger.info("transform_weather", records=len(records))
    return records


# ─── Demand transformer ───────────────────────────────────────────────────────

def transform_demand(
    df: pd.DataFrame,
    source_id: int,
    pipeline_run_id: Optional[int],
    demand_col: str = "demand_kwh",
    region_id: Optional[str] = None,
    unit: str = "kWh",
) -> List[Dict]:
    """
    Transform a validated demand DataFrame to demand_observations dicts.
    """
    records: List[Dict] = []
    for _, row in df.iterrows():
        rec: Dict[str, Any] = {
            "source_id": source_id,
            "pipeline_run_id": pipeline_run_id,
            "observed_at": row["observed_at"],
            "region_id": region_id,
            "demand_kwh": _safe_float(row.get(demand_col)),
            "demand_kw": None,
            "unit": unit,
            "is_valid": True,
        }
        records.append(rec)

    logger.info("transform_demand", records=len(records))
    return records
