"""
Shared pytest fixtures.

Uses an in-memory SQLite database so tests run without a PostgreSQL instance.
The application database.py engine is monkey-patched via environment override.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# ── Make sure backend/ is on sys.path ────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Use SQLite for tests — avoids PostgreSQL dependency
os.environ.setdefault(
    "DATABASE_URL", "sqlite:///./test_reai.db"
)
os.environ.setdefault("DEBUG", "false")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.core.config import get_settings


# ── In-memory SQLite engine ───────────────────────────────────────────────────
TEST_DB_URL = "sqlite://"   # in-memory

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a transactional test session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── FastAPI test client ───────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def test_client(engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.database import get_db
    from app.main import app

    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


# ── Sample DataFrames ─────────────────────────────────────────────────────────
@pytest.fixture
def solar_sample_df():
    """Small synthetic solar generation DataFrame for pipeline tests."""
    import numpy as np
    dates = pd.date_range("2022-01-01", periods=200, freq="h", tz="UTC")
    rng = np.random.default_rng(0)
    generation = np.clip(
        10 * np.sin(np.pi * dates.hour / 12) + rng.normal(0, 0.5, 200),
        0, 20
    )
    return pd.DataFrame({
        "timestamp": dates,
        "generation_kwh": generation,
        "ghi": np.clip(generation * 45, 0, 900),
        "temperature_c": 25 + rng.normal(0, 2, 200),
    })


@pytest.fixture
def weather_sample_df():
    """Small synthetic weather DataFrame for pipeline tests."""
    import numpy as np
    dates = pd.date_range("2022-01-01", periods=200, freq="h", tz="UTC")
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "timestamp": dates,
        "temperature_c": 25 + rng.normal(0, 2, 200),
        "cloud_cover_pct": np.clip(rng.normal(40, 15, 200), 0, 100),
        "shortwave_radiation_wm2": np.clip(rng.normal(300, 100, 200), 0, 900),
    })
