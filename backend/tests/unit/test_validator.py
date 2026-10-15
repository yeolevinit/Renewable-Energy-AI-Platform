"""Unit tests for the data validation engine."""

import numpy as np
import pandas as pd
import pytest

from app.pipeline.validator import validate_dataframe


def _make_df(n=50, with_timestamp=True, tz=True):
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC" if tz else None)
    return pd.DataFrame({
        "timestamp": dates if with_timestamp else [None] * n,
        "generation_kwh": np.clip(np.random.default_rng(0).normal(5, 2, n), 0, 20),
    })


# ── Required columns ─────────────────────────────────────────────────────────

def test_missing_required_column_fails():
    df = _make_df()
    df = df.drop(columns=["generation_kwh"])
    _, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert not result.is_valid
    assert any("Missing required columns" in issue for issue in result.issues)


def test_all_required_columns_present_passes():
    df = _make_df()
    cleaned, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert len(result.issues) == 0
    assert "observed_at" in cleaned.columns


# ── Timestamp parsing ─────────────────────────────────────────────────────────

def test_invalid_timestamps_are_dropped():
    df = _make_df(n=10)
    df.loc[3, "timestamp"] = "not-a-date"
    df.loc[7, "timestamp"] = None
    cleaned, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert result.timestamp_errors == 2
    assert len(cleaned) == 8


def test_timezone_normalized_to_utc():
    df = _make_df(tz=False)
    # Naive timestamps — should be treated as UTC
    cleaned, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert cleaned["observed_at"].dt.tz is not None


# ── Duplicate handling ────────────────────────────────────────────────────────

def test_duplicate_timestamps_removed():
    df = _make_df(n=10)
    # Duplicate the first row
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    cleaned, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert result.duplicate_rows == 1
    assert len(cleaned) == 10


# ── Missing values ────────────────────────────────────────────────────────────

def test_missing_values_tracked():
    df = _make_df(n=20)
    df.loc[5, "generation_kwh"] = None
    df.loc[10, "generation_kwh"] = None
    _, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert result.missing_by_column.get("generation_kwh", 0) == 2


# ── Range validation ──────────────────────────────────────────────────────────

def test_out_of_range_values_warned():
    df = _make_df(n=20)
    df.loc[2, "generation_kwh"] = -50.0    # negative — invalid
    df.loc[4, "generation_kwh"] = 2_000_000  # absurdly large
    _, result = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert result.out_of_range_rows >= 2


def test_out_of_range_not_removed():
    """Out-of-range values are flagged but NOT automatically removed."""
    df = _make_df(n=10)
    df.loc[1, "generation_kwh"] = -999.0
    cleaned, _ = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    # Row still present
    assert len(cleaned) == 10


# ── Time gap detection ────────────────────────────────────────────────────────

def test_time_gap_detected():
    dates = pd.date_range("2022-01-01", periods=10, freq="h", tz="UTC").tolist()
    # Insert a 6-hour gap between index 5 and 6
    dates.insert(6, dates[5] + pd.Timedelta("6h"))
    dates.pop(5)
    df = pd.DataFrame({
        "timestamp": dates[:10],
        "generation_kwh": [1.0] * 10,
    })
    _, result = validate_dataframe(
        df, required_columns=["timestamp", "generation_kwh"], expected_interval="hourly"
    )
    assert result.time_gap_count >= 1


# ── Sorted output ─────────────────────────────────────────────────────────────

def test_output_sorted_chronologically():
    df = _make_df(n=10)
    df = df.iloc[::-1].reset_index(drop=True)  # reverse order
    cleaned, _ = validate_dataframe(df, required_columns=["timestamp", "generation_kwh"])
    assert cleaned["observed_at"].is_monotonic_increasing
