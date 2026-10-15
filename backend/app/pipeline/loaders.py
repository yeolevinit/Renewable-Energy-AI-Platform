"""
Database loader — bulk-inserts transformed records with idempotency.

Strategy: use INSERT ... ON CONFLICT DO NOTHING for idempotent reruns,
keyed on (source_id, observed_at) for time-series tables.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.energy_observation import EnergyObservation
from app.models.weather_observation import WeatherObservation
from app.models.demand_observation import DemandObservation

logger = get_logger(__name__)

# ─── Unique constraint columns for each table ────────────────────────────────
_CONFLICT_COLS: Dict[str, List[str]] = {
    "energy_observations": ["source_id", "observed_at"],
    "weather_observations": ["source_id", "observed_at"],
    "demand_observations": ["source_id", "observed_at"],
}

_MODEL_MAP = {
    "energy_observations": EnergyObservation,
    "weather_observations": WeatherObservation,
    "demand_observations": DemandObservation,
}

_CHUNK_SIZE = 500


def _bulk_insert_idempotent(
    db: Session,
    table_name: str,
    records: List[Dict],
) -> int:
    """
    Bulk insert records using PostgreSQL INSERT ON CONFLICT DO NOTHING.
    Returns the number of rows actually inserted.
    """
    if not records:
        return 0

    model = _MODEL_MAP[table_name]
    inserted_total = 0

    for i in range(0, len(records), _CHUNK_SIZE):
        chunk = records[i : i + _CHUNK_SIZE]
        stmt = pg_insert(model.__table__).values(chunk)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=_CONFLICT_COLS[table_name]
        )
        result = db.execute(stmt)
        inserted_total += result.rowcount if result.rowcount >= 0 else len(chunk)

    logger.info(
        "bulk_insert_complete",
        table=table_name,
        attempted=len(records),
        inserted=inserted_total,
    )
    return inserted_total


def load_solar_generation(
    db: Session,
    records: List[Dict],
) -> int:
    """Load solar generation records; returns rows inserted."""
    return _bulk_insert_idempotent(db, "energy_observations", records)


def load_weather(
    db: Session,
    records: List[Dict],
) -> int:
    """Load weather records; returns rows inserted."""
    return _bulk_insert_idempotent(db, "weather_observations", records)


def load_demand(
    db: Session,
    records: List[Dict],
) -> int:
    """Load demand records; returns rows inserted."""
    return _bulk_insert_idempotent(db, "demand_observations", records)
