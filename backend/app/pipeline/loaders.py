"""
Database loader — bulk-inserts transformed records with idempotency.

Uses dialect-aware INSERT ON CONFLICT DO NOTHING for PostgreSQL,
and INSERT OR IGNORE for SQLite (used in development/testing).
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.energy_observation import EnergyObservation
from app.models.weather_observation import WeatherObservation
from app.models.demand_observation import DemandObservation

logger = get_logger(__name__)

_MODEL_MAP = {
    "energy_observations": EnergyObservation,
    "weather_observations": WeatherObservation,
    "demand_observations": DemandObservation,
}

_CHUNK_SIZE = 500


def _is_postgres(session: Session) -> bool:
    return session.bind.dialect.name == "postgresql"


def _bulk_insert_idempotent(
    db: Session,
    table_name: str,
    records: List[Dict],
) -> int:
    if not records:
        return 0

    model = _MODEL_MAP[table_name]
    inserted_total = 0

    if _is_postgres(db):
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        conflict_cols = ["source_id", "observed_at"]
        for i in range(0, len(records), _CHUNK_SIZE):
            chunk = records[i: i + _CHUNK_SIZE]
            stmt = pg_insert(model.__table__).values(chunk)
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
            result = db.execute(stmt)
            inserted_total += result.rowcount if result.rowcount >= 0 else len(chunk)
    else:
        # SQLite — use individual INSERT OR IGNORE via ORM
        for i in range(0, len(records), _CHUNK_SIZE):
            chunk = records[i: i + _CHUNK_SIZE]
            for rec in chunk:
                # Check for existing row to achieve idempotency
                exists = db.query(model).filter_by(
                    source_id=rec["source_id"],
                    observed_at=rec["observed_at"],
                ).first()
                if not exists:
                    db.add(model(**rec))
                    inserted_total += 1

    logger.info("bulk_insert_complete", table=table_name,
                attempted=len(records), inserted=inserted_total)
    return inserted_total


def load_solar_generation(db: Session, records: List[Dict]) -> int:
    return _bulk_insert_idempotent(db, "energy_observations", records)


def load_weather(db: Session, records: List[Dict]) -> int:
    return _bulk_insert_idempotent(db, "weather_observations", records)


def load_demand(db: Session, records: List[Dict]) -> int:
    return _bulk_insert_idempotent(db, "demand_observations", records)
