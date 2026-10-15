"""
Unit tests for feature engineering.

Critical correctness checks:
- No future data leakage in lag / rolling features
- Chronological split preserves order and correct proportions
- Time features are deterministic and within valid ranges
"""

import numpy as np
import pandas as pd
import pytest

from app.ml.feature_engineering import (
    add_lag_features,
    add_rolling_features,
    add_time_features,
    build_features,
    chronological_split,
)


def _hourly_df(n=500, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "observed_at": dates,
        "generation_kwh": np.clip(rng.normal(5, 2, n), 0, 20),
    })


# ── Time features ─────────────────────────────────────────────────────────────

def test_time_features_hour_range():
    df = _hourly_df()
    df = add_time_features(df)
    assert df["hour"].between(0, 23).all()


def test_time_features_month_range():
    df = _hourly_df()
    df = add_time_features(df)
    assert df["month"].between(1, 12).all()


def test_time_features_cyclical_bounds():
    df = _hourly_df()
    df = add_time_features(df)
    assert df["hour_sin"].between(-1.0, 1.0).all()
    assert df["hour_cos"].between(-1.0, 1.0).all()


def test_time_features_dow_range():
    df = _hourly_df()
    df = add_time_features(df)
    assert df["day_of_week"].between(0, 6).all()


# ── Lag features — no-leakage guarantee ──────────────────────────────────────

def test_lag_1_equals_previous_row():
    df = _hourly_df(n=20)
    df = add_lag_features(df, "generation_kwh", lags=[1])
    # Row i lag_1 must equal row i-1 generation
    for i in range(1, len(df)):
        expected = df["generation_kwh"].iloc[i - 1]
        actual = df["generation_kwh_lag_1"].iloc[i]
        assert abs(actual - expected) < 1e-9, f"Lag mismatch at row {i}"


def test_lag_first_row_is_nan():
    df = _hourly_df(n=10)
    df = add_lag_features(df, "generation_kwh", lags=[1])
    assert pd.isna(df["generation_kwh_lag_1"].iloc[0])


def test_lag_columns_created():
    df = _hourly_df()
    df = add_lag_features(df, "generation_kwh", lags=[1, 6, 24])
    assert "generation_kwh_lag_1" in df.columns
    assert "generation_kwh_lag_6" in df.columns
    assert "generation_kwh_lag_24" in df.columns


# ── Rolling features — no-leakage guarantee ──────────────────────────────────

def test_rolling_excludes_current_row():
    """Rolling mean at row i must NOT include the value at row i."""
    df = pd.DataFrame({
        "observed_at": pd.date_range("2022-01-01", periods=10, freq="h", tz="UTC"),
        "generation_kwh": [float(x) for x in range(10)],  # 0,1,2,...,9
    })
    df = add_rolling_features(df, "generation_kwh", windows=[3])
    # At row 3 (value=3): rolling mean of shifted series uses rows 0,1,2 → mean=1.0
    roll_val = df["generation_kwh_roll_mean_3"].iloc[3]
    assert abs(roll_val - 1.0) < 1e-9, f"Expected 1.0 but got {roll_val}"


def test_rolling_columns_created():
    df = _hourly_df()
    df = add_rolling_features(df, "generation_kwh", windows=[6, 24])
    assert "generation_kwh_roll_mean_6" in df.columns
    assert "generation_kwh_roll_std_24" in df.columns


# ── Chronological split ───────────────────────────────────────────────────────

def test_split_proportions_approx():
    df = _hourly_df(n=1000)
    train, val, test = chronological_split(df, train_ratio=0.70, val_ratio=0.15)
    assert abs(len(train) / 1000 - 0.70) < 0.02
    assert abs(len(val) / 1000 - 0.15) < 0.02
    assert abs(len(test) / 1000 - 0.15) < 0.02


def test_split_no_overlap():
    df = _hourly_df(n=300)
    df = df.reset_index(drop=True)
    train, val, test = chronological_split(df, 0.70, 0.15)
    # Indices must be non-overlapping and cover full range
    all_idx = list(train.index) + list(val.index) + list(test.index)
    assert len(all_idx) == len(df)
    assert len(set(all_idx)) == len(df)


def test_split_chronological_order():
    df = _hourly_df(n=300)
    train, val, test = chronological_split(df, 0.70, 0.15)
    # Last train timestamp must be before first val timestamp
    assert train["observed_at"].iloc[-1] < val["observed_at"].iloc[0]
    assert val["observed_at"].iloc[-1] < test["observed_at"].iloc[0]


def test_split_total_equals_input():
    df = _hourly_df(n=500)
    train, val, test = chronological_split(df, 0.70, 0.15)
    assert len(train) + len(val) + len(test) == len(df)


# ── Full build_features pipeline ─────────────────────────────────────────────

def test_build_features_returns_more_columns():
    df = _hourly_df(n=200)
    df_feat = build_features(df, target_col="generation_kwh")
    assert len(df_feat.columns) > len(df.columns)


def test_build_features_no_future_in_lags():
    """Lag columns must shift forward by the lag amount (shift > 0)."""
    df = _hourly_df(n=100)
    df_feat = build_features(df, target_col="generation_kwh", include_weather=False)
    lag_cols = [c for c in df_feat.columns if "_lag_" in c]
    assert len(lag_cols) > 0
    # All lag values at position 0 should be NaN
    for col in lag_cols:
        assert pd.isna(df_feat[col].iloc[0])
