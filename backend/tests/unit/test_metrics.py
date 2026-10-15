"""Unit tests for forecasting metrics."""

import numpy as np
import pytest

from app.ml.metrics import (
    mae,
    rmse,
    r2,
    mape,
    compute_all_metrics,
    persistence_baseline,
    seasonal_naive_baseline,
)


def test_mae_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0])
    assert mae(y, y) == 0.0


def test_mae_known_value():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])
    # |−2| + |2| + |−3| / 3 = 7/3
    assert abs(mae(y_true, y_pred) - 7 / 3) < 1e-9


def test_rmse_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0])
    assert rmse(y, y) == 0.0


def test_rmse_known_value():
    y_true = np.array([0.0, 0.0])
    y_pred = np.array([3.0, 4.0])
    # sqrt((9+16)/2) = sqrt(12.5)
    expected = np.sqrt(12.5)
    assert abs(rmse(y_true, y_pred) - expected) < 1e-9


def test_r2_perfect_prediction():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert abs(r2(y, y) - 1.0) < 1e-9


def test_r2_constant_series_returns_none():
    y = np.array([5.0, 5.0, 5.0])
    assert r2(y, y) is None


def test_r2_worst_case_negative():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([3.0, 2.0, 1.0])
    assert r2(y_true, y_pred) < 0


def test_mape_returns_none_for_zero_actuals():
    y_true = np.array([0.0, 0.0, 0.0])
    y_pred = np.array([1.0, 2.0, 3.0])
    # All actuals at or below threshold → None
    assert mape(y_true, y_pred) is None


def test_mape_known_value():
    y_true = np.array([100.0, 200.0])
    y_pred = np.array([110.0, 190.0])
    # |−10/100| + |10/200| / 2 * 100 = (0.1 + 0.05)/2*100 = 7.5
    result = mape(y_true, y_pred, zero_threshold=0.1)
    assert result is not None
    assert abs(result - 7.5) < 1e-6


def test_compute_all_metrics_returns_required_keys():
    y = np.array([1.0, 2.0, 3.0])
    result = compute_all_metrics(y, y)
    for key in ("mae", "rmse", "r2", "n_samples"):
        assert key in result


def test_compute_all_metrics_n_samples():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = compute_all_metrics(y, y)
    assert result["n_samples"] == 5


def test_persistence_baseline_shape():
    y_train = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    preds = persistence_baseline(y_train, n_steps=10)
    assert len(preds) == 10


def test_persistence_baseline_uses_last_value():
    y_train = np.array([1.0, 2.0, 7.0])
    preds = persistence_baseline(y_train, n_steps=3, step=1)
    assert all(p == 7.0 for p in preds)


def test_seasonal_naive_baseline_shape():
    y_train = np.arange(48, dtype=float)
    preds = seasonal_naive_baseline(y_train, n_steps=24, period=24)
    assert len(preds) == 24


def test_seasonal_naive_baseline_repeats_season():
    y_train = np.array([float(i) for i in range(24)] * 3)
    preds = seasonal_naive_baseline(y_train, n_steps=24, period=24)
    # Should repeat the last 24 values
    expected = y_train[-24:]
    np.testing.assert_array_almost_equal(preds, expected)
