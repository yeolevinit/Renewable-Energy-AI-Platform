"""
Forecasting evaluation metrics.

All metrics here are correct implementations used consistently
across models and baselines.  MAPE is only computed when
safe (no zero or near-zero actuals).
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error."""
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    """
    R² (coefficient of determination).
    Returns None if variance of y_true is zero (constant series).
    """
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return None
    return float(1 - ss_res / ss_tot)


def mape(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    zero_threshold: float = 0.1,
) -> Optional[float]:
    """
    Mean Absolute Percentage Error.

    Returns None if more than 10% of actuals are at or below zero_threshold
    (MAPE is undefined/misleading with near-zero targets).

    zero_threshold: values below this are considered 'near-zero' in the
    context of the dataset's typical unit (e.g. kWh).
    """
    mask = y_true > zero_threshold
    if mask.sum() < len(y_true) * 0.9:
        # Too many near-zero actuals; MAPE not reliable
        return None
    safe_actual = y_true[mask]
    safe_pred = y_pred[mask]
    return float(np.mean(np.abs((safe_actual - safe_pred) / safe_actual)) * 100)


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    zero_threshold: float = 0.1,
) -> Dict[str, Optional[float]]:
    """Return a dict of all metrics for a set of predictions."""
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "r2": r2(y_true, y_pred),
        "mape": mape(y_true, y_pred, zero_threshold),
        "n_samples": int(len(y_true)),
    }


# ─── Baseline predictions ─────────────────────────────────────────────────────

def persistence_baseline(
    y_train: np.ndarray,
    n_steps: int,
    step: int = 1,
) -> np.ndarray:
    """
    Persistence baseline: predict the value from `step` observations ago.
    For a test set, we use the last `step` value from the training set
    and repeat it — simplified for evaluation purposes.
    """
    # Use the last `step` values of training as naive forecast
    if len(y_train) >= step:
        last_val = y_train[-step]
    else:
        last_val = y_train[-1] if len(y_train) > 0 else 0.0
    return np.full(n_steps, last_val)


def seasonal_naive_baseline(
    y_train: np.ndarray,
    n_steps: int,
    period: int = 24,
) -> np.ndarray:
    """
    Seasonal naïve: repeat the last full season from training data.
    For hourly data, period=24 repeats the last 24 hours.
    """
    season = y_train[-period:]
    # Tile to cover n_steps
    reps = (n_steps // period) + 1
    tiled = np.tile(season, reps)
    return tiled[:n_steps]
