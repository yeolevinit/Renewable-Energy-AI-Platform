"""Unit tests for pipeline transformers."""

import pandas as pd
import numpy as np
import pytest

from app.pipeline.transformers import (
    transform_solar_generation,
    transform_weather,
    transform_demand,
    _safe_float,
)


def _valid_df(n=10):
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "observed_at": dates,
        "generation_kwh": np.linspace(0, 10, n),
        "ghi": np.linspace(0, 800, n),
    })


# ── _safe_float ───────────────────────────────────────────────────────────────

def test_safe_float_nan_returns_none():
    assert _safe_float(float("nan")) is None


def test_safe_float_none_returns_none():
    assert _safe_float(None) is None


def test_safe_float_valid_value():
    assert _safe_float("3.14") == pytest.approx(3.14)


def test_safe_float_zero():
    assert _safe_float(0) == 0.0


# ── Solar transformer ────────────────────────────────────────────────────────

def test_solar_transformer_record_count():
    df = _valid_df(n=24)
    records = transform_solar_generation(df, source_id=1, pipeline_run_id=1)
    assert len(records) == 24


def test_solar_transformer_required_keys():
    df = _valid_df()
    records = transform_solar_generation(df, source_id=1, pipeline_run_id=None)
    record = records[0]
    for key in ("source_id", "observed_at", "generation_kwh", "unit", "is_valid"):
        assert key in record


def test_solar_transformer_source_id_set():
    df = _valid_df()
    records = transform_solar_generation(df, source_id=42, pipeline_run_id=None)
    assert all(r["source_id"] == 42 for r in records)


def test_solar_transformer_nan_becomes_none():
    df = _valid_df(n=5)
    df.loc[2, "generation_kwh"] = float("nan")
    records = transform_solar_generation(df, source_id=1, pipeline_run_id=None)
    assert records[2]["generation_kwh"] is None


def test_solar_transformer_unit_propagated():
    df = _valid_df()
    records = transform_solar_generation(df, source_id=1, pipeline_run_id=None, unit="MWh")
    assert all(r["unit"] == "MWh" for r in records)


def test_solar_transformer_is_valid_true():
    df = _valid_df()
    records = transform_solar_generation(df, source_id=1, pipeline_run_id=None)
    assert all(r["is_valid"] is True for r in records)


# ── Weather transformer ───────────────────────────────────────────────────────

def test_weather_transformer_record_count():
    df = pd.DataFrame({
        "observed_at": pd.date_range("2022-01-01", periods=12, freq="h", tz="UTC"),
        "temperature_c": [25.0] * 12,
    })
    records = transform_weather(df, source_id=2, pipeline_run_id=None)
    assert len(records) == 12


def test_weather_transformer_col_map():
    df = pd.DataFrame({
        "observed_at": pd.date_range("2022-01-01", periods=5, freq="h", tz="UTC"),
        "temp": [20.0, 21.0, 22.0, 23.0, 24.0],
    })
    col_map = {"temperature_c": "temp"}
    records = transform_weather(df, source_id=1, pipeline_run_id=None, col_map=col_map)
    assert records[0]["temperature_c"] == pytest.approx(20.0)


# ── Demand transformer ────────────────────────────────────────────────────────

def test_demand_transformer_record_count():
    df = pd.DataFrame({
        "observed_at": pd.date_range("2022-01-01", periods=8, freq="h", tz="UTC"),
        "demand_kwh": [500.0] * 8,
    })
    records = transform_demand(df, source_id=3, pipeline_run_id=None)
    assert len(records) == 8


def test_demand_transformer_region_id():
    df = pd.DataFrame({
        "observed_at": pd.date_range("2022-01-01", periods=3, freq="h", tz="UTC"),
        "demand_kwh": [100.0, 200.0, 300.0],
    })
    records = transform_demand(df, source_id=1, pipeline_run_id=None, region_id="test_region")
    assert all(r["region_id"] == "test_region" for r in records)
