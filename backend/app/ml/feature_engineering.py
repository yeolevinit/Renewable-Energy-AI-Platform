"""
Leakage-safe feature engineering for time-series forecasting.

All lag, rolling, and statistical features are computed strictly
from past observations — no future values are used.

Design principles:
- Lag features: shift forward by at least 1 step
- Rolling features: use closed='left' to exclude current observation
- Fit-and-transform objects (e.g. scalers) are fitted on training data only;
  the same fitted object is applied at inference time
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Time features ────────────────────────────────────────────────────────────

def add_time_features(df: pd.DataFrame, timestamp_col: str = "observed_at") -> pd.DataFrame:
    """
    Add calendar time features from the observation timestamp.
    These are deterministically known at prediction time.
    """
    df = df.copy()
    ts = df[timestamp_col]
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek          # 0=Mon, 6=Sun
    df["day_of_year"] = ts.dt.dayofyear
    df["month"] = ts.dt.month
    df["week_of_year"] = ts.dt.isocalendar().week.astype(int)
    df["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)
    # Cyclical encoding — preserves periodicity
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    return df


# ─── Lag features ─────────────────────────────────────────────────────────────

def add_lag_features(
    df: pd.DataFrame,
    target_col: str,
    lags: List[int],
) -> pd.DataFrame:
    """
    Add lag features for the target column.
    lag=1 uses the value 1 step before the current row (no leakage).
    """
    df = df.copy()
    for lag in lags:
        df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)
    return df


# ─── Rolling statistics ───────────────────────────────────────────────────────

def add_rolling_features(
    df: pd.DataFrame,
    target_col: str,
    windows: List[int],
) -> pd.DataFrame:
    """
    Add rolling mean and std using past observations only (min_periods=1).
    The window is shifted by 1 so the current observation is excluded.
    """
    df = df.copy()
    shifted = df[target_col].shift(1)  # exclude current observation
    for w in windows:
        df[f"{target_col}_roll_mean_{w}"] = (
            shifted.rolling(window=w, min_periods=1).mean()
        )
        df[f"{target_col}_roll_std_{w}"] = (
            shifted.rolling(window=w, min_periods=1).std()
        )
    return df


# ─── Weather features ─────────────────────────────────────────────────────────

def add_weather_features(
    df: pd.DataFrame,
    weather_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Add weather-derived features (interaction terms).
    Only include weather_cols that are present in df.
    """
    available_weather = [
        "temperature_c",
        "cloud_cover_pct",
        "shortwave_radiation_wm2",
        "direct_radiation_wm2",
        "diffuse_radiation_wm2",
        "precipitation_mm",
        "relative_humidity_pct",
    ]
    cols_to_use = weather_cols if weather_cols else available_weather
    df = df.copy()

    # Simple interaction: GHI proxy = shortwave - diffuse
    if (
        "shortwave_radiation_wm2" in df.columns
        and "diffuse_radiation_wm2" in df.columns
    ):
        df["ghi_proxy"] = (
            df["shortwave_radiation_wm2"].fillna(0)
            - df["diffuse_radiation_wm2"].fillna(0)
        ).clip(lower=0)

    # Cloud cover interaction with radiation
    if "cloud_cover_pct" in df.columns and "shortwave_radiation_wm2" in df.columns:
        df["cloud_rad_interaction"] = (
            (1 - df["cloud_cover_pct"].fillna(50) / 100)
            * df["shortwave_radiation_wm2"].fillna(0)
        )

    return df


# ─── Master feature builder ───────────────────────────────────────────────────

DEFAULT_LAGS = [1, 2, 3, 6, 12, 24]
DEFAULT_WINDOWS = [3, 6, 12, 24]


def build_features(
    df: pd.DataFrame,
    target_col: str = "generation_kwh",
    timestamp_col: str = "observed_at",
    include_weather: bool = True,
    lags: Optional[List[int]] = None,
    windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Full feature-engineering pipeline for forecasting.

    Returns a DataFrame with all engineered columns appended.
    Rows with NaN introduced by lags will need to be dropped before training.
    """
    df = add_time_features(df, timestamp_col)
    df = add_lag_features(df, target_col, lags or DEFAULT_LAGS)
    df = add_rolling_features(df, target_col, windows or DEFAULT_WINDOWS)
    if include_weather:
        df = add_weather_features(df)
    return df


# ─── Chronological train/val/test split ──────────────────────────────────────

def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split a time-ordered DataFrame chronologically.
    test_ratio = 1 - train_ratio - val_ratio

    IMPORTANT: df must already be sorted by time.
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    logger.info(
        "chronological_split",
        n_total=n,
        n_train=len(train),
        n_val=len(val),
        n_test=len(test),
        train_start=str(train["observed_at"].iloc[0]) if "observed_at" in train.columns else "?",
        train_end=str(train["observed_at"].iloc[-1]) if "observed_at" in train.columns else "?",
        test_start=str(test["observed_at"].iloc[0]) if "observed_at" in test.columns else "?",
        test_end=str(test["observed_at"].iloc[-1]) if "observed_at" in test.columns else "?",
    )

    return train, val, test
