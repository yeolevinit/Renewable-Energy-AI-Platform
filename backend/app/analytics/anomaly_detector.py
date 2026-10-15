"""
Anomaly detection for solar generation and weather series.

Methods implemented:
1. Statistical threshold (z-score / IQR)
2. Forecast-residual threshold (requires a trained model's test forecasts)
3. Isolation Forest (unsupervised; used when no labels are available)

Alerts include: timestamp, observed value, expected value, score, method,
and a human-readable explanation.

IMPORTANT: An alert means "unusual pattern — investigation recommended."
It does NOT confirm equipment failure or a physical fault.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.core.logging import get_logger
from app.db.database import db_session
from app.models.anomaly_alert import AnomalyAlert

logger = get_logger(__name__)

# ─── Statistical threshold ────────────────────────────────────────────────────

def detect_statistical_anomalies(
    df: pd.DataFrame,
    value_col: str,
    timestamp_col: str = "observed_at",
    z_threshold: float = 3.0,
    series_type: str = "solar_generation",
    source_id: Optional[int] = None,
    site_id: Optional[str] = None,
) -> List[Dict]:
    """
    Flag observations whose z-score exceeds z_threshold.

    Returns a list of alert dicts ready for database insertion.
    """
    series = df[value_col].dropna()
    if len(series) < 10:
        logger.warning("statistical_anomaly_insufficient_data", col=value_col, n=len(series))
        return []

    mean = series.mean()
    std = series.std()

    if std == 0:
        return []  # constant series — no meaningful z-score

    alerts = []
    for _, row in df.iterrows():
        val = row.get(value_col)
        if val is None or pd.isna(val):
            continue
        z = abs((val - mean) / std)
        if z > z_threshold:
            severity = "high" if z > z_threshold * 1.5 else "medium"
            alerts.append({
                "source_id": source_id,
                "observed_at": row[timestamp_col],
                "series_type": series_type,
                "site_id": site_id,
                "observed_value": float(val),
                "expected_value": float(mean),
                "anomaly_score": float(z),
                "severity": severity,
                "detection_method": "statistical_threshold",
                "explanation": (
                    f"Value {val:.2f} is {z:.1f} standard deviations from the series mean "
                    f"({mean:.2f} ± {std:.2f}). Investigation recommended."
                ),
                "review_status": "open",
            })

    logger.info("statistical_anomalies_detected", count=len(alerts), col=value_col)
    return alerts


# ─── Residual-based threshold ─────────────────────────────────────────────────

def detect_residual_anomalies(
    actual: np.ndarray,
    predicted: np.ndarray,
    timestamps: pd.Series,
    residual_threshold_factor: float = 2.5,
    series_type: str = "solar_generation",
    source_id: Optional[int] = None,
    site_id: Optional[str] = None,
) -> List[Dict]:
    """
    Flag observations where |actual - predicted| > threshold_factor × MAD.

    MAD = Median Absolute Deviation of residuals.
    """
    residuals = actual - predicted
    mad = np.median(np.abs(residuals - np.median(residuals)))
    if mad == 0:
        mad = np.std(residuals) or 1.0

    threshold = residual_threshold_factor * mad
    alerts = []

    for i, (act, pred, ts) in enumerate(zip(actual, predicted, timestamps)):
        res = abs(act - pred)
        if res > threshold:
            score = float(res / mad)
            severity = "high" if score > residual_threshold_factor * 1.5 else "medium"
            alerts.append({
                "source_id": source_id,
                "observed_at": ts,
                "series_type": series_type,
                "site_id": site_id,
                "observed_value": float(act),
                "expected_value": float(pred),
                "anomaly_score": score,
                "severity": severity,
                "detection_method": "residual_threshold",
                "explanation": (
                    f"Observed value {act:.2f} differs from model prediction {pred:.2f} "
                    f"by {res:.2f} (threshold: {threshold:.2f}). "
                    "This may indicate an unusual generation event."
                ),
                "review_status": "open",
            })

    logger.info("residual_anomalies_detected", count=len(alerts))
    return alerts


# ─── Isolation Forest ────────────────────────────────────────────────────────

def detect_isolation_forest_anomalies(
    df: pd.DataFrame,
    feature_cols: List[str],
    timestamp_col: str = "observed_at",
    contamination: float = 0.05,
    series_type: str = "solar_generation",
    source_id: Optional[int] = None,
    site_id: Optional[str] = None,
    random_state: int = 42,
) -> List[Dict]:
    """
    Use Isolation Forest on multivariate features to detect anomalies.

    contamination: expected proportion of outliers (0 < contamination < 0.5).
    Only use this when statistical methods are insufficient and the feature
    set is meaningful.
    """
    available = [c for c in feature_cols if c in df.columns]
    if not available:
        logger.warning("isolation_forest_no_features")
        return []

    sub = df[available + [timestamp_col]].dropna()
    if len(sub) < 20:
        return []

    X = sub[available].values
    iso = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    labels = iso.fit_predict(X)
    scores = iso.score_samples(X)

    alerts = []
    for i, (label, score) in enumerate(zip(labels, scores)):
        if label == -1:  # anomaly
            row = sub.iloc[i]
            alerts.append({
                "source_id": source_id,
                "observed_at": row[timestamp_col],
                "series_type": series_type,
                "site_id": site_id,
                "observed_value": None,
                "expected_value": None,
                "anomaly_score": float(-score),  # invert: higher = more anomalous
                "severity": "medium",
                "detection_method": "isolation_forest",
                "explanation": (
                    f"Isolation Forest flagged this observation as anomalous "
                    f"(score: {score:.3f}). The pattern differs from the majority "
                    "of the training data. Further investigation is recommended."
                ),
                "review_status": "open",
            })

    logger.info("isolation_forest_anomalies_detected", count=len(alerts))
    return alerts


# ─── Persist alerts ───────────────────────────────────────────────────────────

def save_alerts(alerts: List[Dict]) -> int:
    """Bulk-insert anomaly alerts into the database. Returns inserted count."""
    if not alerts:
        return 0
    with db_session() as db:
        for alert in alerts:
            db.add(AnomalyAlert(**alert))
    logger.info("alerts_saved", count=len(alerts))
    return len(alerts)
