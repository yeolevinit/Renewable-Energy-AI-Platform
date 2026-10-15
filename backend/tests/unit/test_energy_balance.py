"""Unit tests for energy balance and scenario calculations."""

import pandas as pd
import numpy as np
import pytest

from app.analytics.energy_balance import calculate_energy_balance, run_scenario


def _gen_df(n=24, base=100.0):
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "observed_at": dates,
        "generation_kwh": [base] * n,
    })


def _dem_df(n=24, base=100.0):
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "observed_at": dates,
        "demand_kwh": [base] * n,
    })


# ── Generation-only (no demand) ───────────────────────────────────────────────

def test_generation_only_status():
    result = calculate_energy_balance(_gen_df(), demand_df=None)
    assert result.balance_status == "generation_only"
    assert result.total_generation_kwh == pytest.approx(2400.0)
    assert result.total_demand_kwh == 0.0


# ── Balanced ──────────────────────────────────────────────────────────────────

def test_balanced_status():
    result = calculate_energy_balance(_gen_df(base=100), _dem_df(base=100))
    assert result.balance_status == "balanced"
    assert result.net_balance_kwh == pytest.approx(0.0, abs=1.0)


# ── Surplus ───────────────────────────────────────────────────────────────────

def test_surplus_status():
    result = calculate_energy_balance(_gen_df(base=150), _dem_df(base=100))
    assert result.balance_status == "surplus"
    assert result.net_balance_kwh > 0


def test_surplus_periods_counted():
    result = calculate_energy_balance(_gen_df(base=150), _dem_df(base=100))
    assert result.surplus_periods == 24
    assert result.deficit_periods == 0


# ── Deficit ───────────────────────────────────────────────────────────────────

def test_deficit_status():
    result = calculate_energy_balance(_gen_df(base=80), _dem_df(base=100))
    assert result.balance_status == "deficit"
    assert result.net_balance_kwh < 0


def test_deficit_periods_counted():
    result = calculate_energy_balance(_gen_df(base=80), _dem_df(base=100))
    assert result.deficit_periods == 24
    assert result.surplus_periods == 0


# ── Adjustments ───────────────────────────────────────────────────────────────

def test_generation_adjustment_reduces_output():
    baseline = calculate_energy_balance(_gen_df(base=100), _dem_df(base=80))
    adjusted = calculate_energy_balance(
        _gen_df(base=100), _dem_df(base=80),
        generation_adjustment_pct=-20.0,
    )
    assert adjusted.total_generation_kwh < baseline.total_generation_kwh


def test_generation_adjustment_100pct_reduction_gives_zero():
    result = calculate_energy_balance(
        _gen_df(base=100), _dem_df(base=100),
        generation_adjustment_pct=-100.0,
    )
    assert result.total_generation_kwh == pytest.approx(0.0, abs=0.01)


def test_demand_adjustment_increases_demand():
    baseline = calculate_energy_balance(_gen_df(base=100), _dem_df(base=80))
    adjusted = calculate_energy_balance(
        _gen_df(base=100), _dem_df(base=80),
        demand_adjustment_pct=25.0,
    )
    assert adjusted.total_demand_kwh > baseline.total_demand_kwh


# ── No timestamp overlap ──────────────────────────────────────────────────────

def test_no_overlap_returns_generation_only():
    gen = _gen_df()
    dem = pd.DataFrame({
        "observed_at": pd.date_range("2023-06-01", periods=24, freq="h", tz="UTC"),
        "demand_kwh": [100.0] * 24,
    })
    result = calculate_energy_balance(gen, dem)
    assert result.balance_status == "generation_only"


# ── Recommendation contains relevant text ─────────────────────────────────────

def test_recommendation_mentions_deficit():
    result = calculate_energy_balance(_gen_df(base=50), _dem_df(base=100))
    assert "deficit" in result.recommendation.lower() or "demand" in result.recommendation.lower()


def test_recommendation_mentions_surplus():
    result = calculate_energy_balance(_gen_df(base=200), _dem_df(base=100))
    assert "surplus" in result.recommendation.lower() or "generation" in result.recommendation.lower()


# ── run_scenario hand-calculation check ──────────────────────────────────────

def test_run_scenario_net_balance_matches_hand_calc():
    """Verify scenario net balance equals gen - demand hand calculation."""
    gen = _gen_df(n=10, base=120.0)
    dem = _dem_df(n=10, base=100.0)
    result = run_scenario(
        "test",
        gen, dem,
        generation_adjustment_pct=0.0,
        demand_adjustment_pct=0.0,
    )
    expected_net = 10 * 120.0 - 10 * 100.0  # 200 kWh surplus
    assert abs(result["net_balance_kwh"] - expected_net) < 0.5


def test_run_scenario_is_simulated_flag():
    gen = _gen_df()
    result = run_scenario("test", gen, None)
    assert result["is_simulated"] is True


def test_run_scenario_has_recommendation():
    gen = _gen_df()
    result = run_scenario("test", gen, None)
    assert isinstance(result["recommendation"], str)
    assert len(result["recommendation"]) > 10
