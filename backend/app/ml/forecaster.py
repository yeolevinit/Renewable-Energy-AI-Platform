"""
Solar generation forecasting service.

Trains and evaluates:
  1. Seasonal-naïve baseline
  2. Linear Regression
  3. Random Forest Regressor
  4. XGBoost Regressor

Uses chronological splits and leakage-safe feature engineering.
Persists model artifacts and writes evaluation records to the database.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import db_session
from app.ml.feature_engineering import (
    build_features,
    chronological_split,
)
from app.ml.metrics import compute_all_metrics, seasonal_naive_baseline
from app.models.forecast import Forecast
from app.models.model_evaluation import ModelEvaluation
from app.models.model_version import ModelVersion

logger = get_logger(__name__)
settings = get_settings()


# ─── Feature column selection ─────────────────────────────────────────────────

def _select_feature_cols(df: pd.DataFrame, target_col: str) -> List[str]:
    """
    Select numeric feature columns — exclude target, timestamps, IDs,
    and any column that is entirely NaN.
    """
    exclude = {
        target_col, "observed_at", "id", "source_id", "pipeline_run_id",
        "created_at", "site_id", "unit", "is_valid",
    }
    cols = [
        c for c in df.columns
        if c not in exclude
        and pd.api.types.is_numeric_dtype(df[c])
        and df[c].notna().sum() > 0
    ]
    return cols


# ─── Artifact persistence ────────────────────────────────────────────────────

def _artifact_path(version_tag: str, suffix: str = "model") -> Path:
    base = settings.model_artifact_path
    return base / f"{version_tag}_{suffix}.pkl"


def _save_artifact(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f)


def _load_artifact(path: Path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ─── Main training function ───────────────────────────────────────────────────

def train_solar_forecast_models(
    df: pd.DataFrame,
    target_col: str = "generation_kwh",
    timestamp_col: str = "observed_at",
    include_weather: bool = True,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    random_seed: int = 42,
) -> Dict:
    """
    Train and evaluate all candidate models for solar generation forecasting.

    df must be pre-sorted chronologically and contain `target_col`.
    Returns a summary of all model evaluation results.
    """
    logger.info("train_solar_models_start", rows=len(df), target=target_col)

    # ── Feature engineering ───────────────────────────────────────────────
    df_feat = build_features(
        df,
        target_col=target_col,
        timestamp_col=timestamp_col,
        include_weather=include_weather,
    )

    # Drop rows with NaN introduced by lag/rolling features
    df_feat = df_feat.dropna(subset=[target_col]).reset_index(drop=True)

    # Chronological split
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio, val_ratio)

    feature_cols = _select_feature_cols(df_feat, target_col)
    logger.info("feature_columns_selected", n_features=len(feature_cols))

    # Drop rows where ANY feature is NaN (lag-induced at start of series)
    train_df = train_df.dropna(subset=feature_cols).copy()
    val_df = val_df.dropna(subset=feature_cols).copy()
    test_df = test_df.dropna(subset=feature_cols).copy()

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_val = val_df[feature_cols].values
    y_val = val_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    # ── Fit scaler on training data only ──────────────────────────────────
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # ── Dates for logging ──────────────────────────────────────────────────
    def _dates(d: pd.DataFrame):
        if timestamp_col in d.columns:
            return str(d[timestamp_col].iloc[0])[:10], str(d[timestamp_col].iloc[-1])[:10]
        return "?", "?"

    train_start, train_end = _dates(train_df)
    val_start, val_end = _dates(val_df)
    test_start, test_end = _dates(test_df)

    results = {}

    # ── Seasonal-naïve baseline ────────────────────────────────────────────
    baseline_preds = seasonal_naive_baseline(y_train, len(y_test), period=24)
    baseline_metrics = compute_all_metrics(y_test, baseline_preds)
    results["seasonal_naive_baseline"] = baseline_metrics
    logger.info("baseline_evaluated", metrics=baseline_metrics)

    with db_session() as db:
        version_tag = f"solar_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # ── Linear Regression ────────────────────────────────────────────────
        lr = LinearRegression()
        lr.fit(X_train_s, y_train)
        val_preds_lr = lr.predict(X_val_s)
        test_preds_lr = lr.predict(X_test_s)

        lr_val_metrics = compute_all_metrics(y_val, val_preds_lr)
        lr_test_metrics = compute_all_metrics(y_test, test_preds_lr)
        results["linear_regression"] = {"validation": lr_val_metrics, "test": lr_test_metrics}

        _save_model_and_evals(
            db=db,
            model_obj=(lr, scaler),
            model_type="linear_regression",
            version_tag=f"{version_tag}_lr",
            feature_cols=feature_cols,
            target_col=target_col,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            val_metrics=lr_val_metrics,
            test_start=test_start,
            test_end=test_end,
            test_metrics=lr_test_metrics,
            baseline_metrics=baseline_metrics,
            test_df=test_df,
            test_preds=test_preds_lr,
        )

        # ── Random Forest ─────────────────────────────────────────────────────
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=random_seed,
            n_jobs=-1,
        )
        rf.fit(X_train, y_train)  # RF doesn't need scaled inputs
        val_preds_rf = rf.predict(X_val)
        test_preds_rf = rf.predict(X_test)

        rf_val_metrics = compute_all_metrics(y_val, val_preds_rf)
        rf_test_metrics = compute_all_metrics(y_test, test_preds_rf)
        fi_rf = dict(zip(feature_cols, rf.feature_importances_.tolist()))
        results["random_forest"] = {"validation": rf_val_metrics, "test": rf_test_metrics}

        _save_model_and_evals(
            db=db,
            model_obj=(rf, None),
            model_type="random_forest",
            version_tag=f"{version_tag}_rf",
            feature_cols=feature_cols,
            target_col=target_col,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            val_metrics=rf_val_metrics,
            test_start=test_start,
            test_end=test_end,
            test_metrics=rf_test_metrics,
            baseline_metrics=baseline_metrics,
            test_df=test_df,
            test_preds=test_preds_rf,
            feature_importances=fi_rf,
        )

        # ── XGBoost ────────────────────────────────────────────────────────────
        xgb = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_seed,
            verbosity=0,
        )
        xgb.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        val_preds_xgb = xgb.predict(X_val)
        test_preds_xgb = xgb.predict(X_test)

        xgb_val_metrics = compute_all_metrics(y_val, val_preds_xgb)
        xgb_test_metrics = compute_all_metrics(y_test, test_preds_xgb)
        fi_xgb = dict(zip(feature_cols, xgb.feature_importances_.tolist()))
        results["xgboost"] = {"validation": xgb_val_metrics, "test": xgb_test_metrics}

        _save_model_and_evals(
            db=db,
            model_obj=(xgb, None),
            model_type="xgboost",
            version_tag=f"{version_tag}_xgb",
            feature_cols=feature_cols,
            target_col=target_col,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            val_metrics=xgb_val_metrics,
            test_start=test_start,
            test_end=test_end,
            test_metrics=xgb_test_metrics,
            baseline_metrics=baseline_metrics,
            test_df=test_df,
            test_preds=test_preds_xgb,
            feature_importances=fi_xgb,
        )

    results["baseline"] = baseline_metrics
    results["feature_columns"] = feature_cols
    results["split_dates"] = {
        "train": [train_start, train_end],
        "val": [val_start, val_end],
        "test": [test_start, test_end],
    }

    logger.info("train_solar_models_complete", models_trained=3)
    return results


def _save_model_and_evals(
    db,
    model_obj,
    model_type: str,
    version_tag: str,
    feature_cols: List[str],
    target_col: str,
    train_start: str,
    train_end: str,
    val_start: str,
    val_end: str,
    val_metrics: Dict,
    test_start: str,
    test_end: str,
    test_metrics: Dict,
    baseline_metrics: Dict,
    test_df: pd.DataFrame,
    test_preds: np.ndarray,
    feature_importances: Optional[Dict] = None,
) -> int:
    """Save model artifact, version record, evaluations, and test forecasts."""
    artifact_path = _artifact_path(version_tag)
    _save_artifact(model_obj, artifact_path)

    mv = ModelVersion(
        task="solar_generation_forecast",
        model_type=model_type,
        version_tag=version_tag,
        train_start=train_start,
        train_end=train_end,
        feature_list=json.dumps(feature_cols),
        artifact_path=str(artifact_path),
        status="active",
    )
    db.add(mv)
    db.flush()
    mv_id = mv.id

    # Validation evaluation
    db.add(ModelEvaluation(
        model_version_id=mv_id,
        split_name="validation",
        split_start=val_start,
        split_end=val_end,
        n_samples=val_metrics.get("n_samples", 0),
        mae=val_metrics.get("mae"),
        rmse=val_metrics.get("rmse"),
        r2=val_metrics.get("r2"),
        mape=val_metrics.get("mape"),
        baseline_mae=baseline_metrics.get("mae"),
        baseline_rmse=baseline_metrics.get("rmse"),
        feature_importances=json.dumps(feature_importances) if feature_importances else None,
    ))

    # Test evaluation
    db.add(ModelEvaluation(
        model_version_id=mv_id,
        split_name="test",
        split_start=test_start,
        split_end=test_end,
        n_samples=test_metrics.get("n_samples", 0),
        mae=test_metrics.get("mae"),
        rmse=test_metrics.get("rmse"),
        r2=test_metrics.get("r2"),
        mape=test_metrics.get("mape"),
        baseline_mae=baseline_metrics.get("mae"),
        baseline_rmse=baseline_metrics.get("rmse"),
        feature_importances=json.dumps(feature_importances) if feature_importances else None,
    ))

    # Store test-period predictions
    timestamp_col = "observed_at"
    for i, (_, row) in enumerate(test_df.iterrows()):
        if i >= len(test_preds):
            break
        db.add(Forecast(
            model_version_id=mv_id,
            forecast_for=row[timestamp_col],
            forecast_type="solar_generation",
            predicted_value=float(test_preds[i]),
            actual_value=float(row[target_col]) if pd.notna(row.get(target_col)) else None,
            unit="kWh",
            forecast_mode="test_evaluation",
        ))

    logger.info("model_saved", model_type=model_type, version_tag=version_tag, mv_id=mv_id)
    return mv_id


# ─── Inference ────────────────────────────────────────────────────────────────

def load_model(version_tag: str) -> Tuple:
    """Load a saved model artifact (model, optional_scaler)."""
    path = _artifact_path(version_tag)
    return _load_artifact(path)


def predict(
    model_tuple: Tuple,
    feature_df: pd.DataFrame,
    feature_cols: List[str],
    use_scaler: bool = False,
) -> np.ndarray:
    """
    Run inference on a feature DataFrame.

    model_tuple: (model, scaler) — scaler may be None.
    """
    model, scaler = model_tuple
    X = feature_df[feature_cols].values

    if use_scaler and scaler is not None:
        X = scaler.transform(X)

    preds = model.predict(X)
    return np.clip(preds, 0, None)  # generation cannot be negative
