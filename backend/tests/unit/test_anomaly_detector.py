"""Unit tests for the anomaly detection module."""

import numpy as np
import pandas as pd
import pytest

from app.analytics.anomaly_detector import (
    detect_statistical_anomalies,
    detect_residual_anomalies,
)


def _base_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    values = rng.normal(50, 5, n)
    return pd.DataFrame({"observed_at": dates, "generation_kwh": values})


# ── Statistical threshold ─────────────────────────────────────────────────────

def test_statistical_detects_injected_spike():
    df = _base_df()
    # Inject an extreme spike
    df.loc[100, "generation_kwh"] = 500.0
    alerts = detect_statistical_anomalies(df, "generation_kwh")
    observed_times = [a["observed_at"] for a in alerts]
    assert df.loc[100, "observed_at"] in observed_times


def test_statistical_detects_injected_drop():
    df = _base_df()
    df.loc[50, "generation_kwh"] = -200.0
    alerts = detect_statistical_anomalies(df, "generation_kwh")
    observed_times = [a["observed_at"] for a in alerts]
    assert df.loc[50, "observed_at"] in observed_times


def test_statistical_clean_series_no_alerts():
    """A perfectly normal series should produce no or very few alerts."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-01", periods=500, freq="h", tz="UTC")
    values = rng.normal(50, 3, 500)
    df = pd.DataFrame({"observed_at": dates, "generation_kwh": values})
    alerts = detect_statistical_anomalies(df, "generation_kwh", z_threshold=4.0)
    # At z=4 we expect almost nothing in a normal distribution of 500
    assert len(alerts) <= 5


def test_statistical_alert_structure():
    df = _base_df()
    df.loc[10, "generation_kwh"] = 999.0
    alerts = detect_statistical_anomalies(df, "generation_kwh")
    assert len(alerts) >= 1
    alert = alerts[0]
    required = {
        "observed_at", "series_type", "observed_value", "expected_value",
        "anomaly_score", "severity", "detection_method", "explanation", "review_status",
    }
    assert required.issubset(set(alert.keys()))


def test_statistical_insufficient_data_returns_empty():
    df = _base_df(n=5)
    alerts = detect_statistical_anomalies(df, "generation_kwh")
    assert alerts == []


def test_statistical_severity_high_for_extreme():
    df = _base_df(n=300)
    df.loc[150, "generation_kwh"] = 1000.0  # very extreme
    alerts = detect_statistical_anomalies(df, "generation_kwh", z_threshold=3.0)
    high_alerts = [a for a in alerts if a["severity"] == "high"]
    assert len(high_alerts) >= 1


# ── Residual threshold ────────────────────────────────────────────────────────

def test_residual_detects_large_deviation():
    rng = np.random.default_rng(0)
    actual = rng.normal(50, 2, 100)
    predicted = actual.copy()
    actual[40] = 200.0  # large residual
    dates = pd.Series(pd.date_range("2022-01-01", periods=100, freq="h", tz="UTC"))
    alerts = detect_residual_anomalies(actual, predicted, dates)
    assert any(a["observed_at"] == dates.iloc[40] for a in alerts)


def test_residual_alert_structure():
    rng = np.random.default_rng(0)
    actual = rng.normal(50, 2, 50)
    predicted = actual.copy()
    actual[25] = 500.0
    dates = pd.Series(pd.date_range("2022-01-01", periods=50, freq="h", tz="UTC"))
    alerts = detect_residual_anomalies(actual, predicted, dates)
    assert len(alerts) >= 1
    a = alerts[0]
    assert "observed_value" in a
    assert "expected_value" in a
    assert a["detection_method"] == "residual_threshold"


def test_residual_clean_series_no_alerts():
    rng = np.random.default_rng(1)
    actual = rng.normal(50, 2, 200)
    predicted = actual + rng.normal(0, 0.1, 200)  # very close predictions
    dates = pd.Series(pd.date_range("2022-01-01", periods=200, freq="h", tz="UTC"))
    # Use a very high threshold — no structurally large deviations exist
    alerts = detect_residual_anomalies(actual, predicted, dates, residual_threshold_factor=10.0)
    assert len(alerts) == 0
