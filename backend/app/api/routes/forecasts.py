"""Forecast and model-evaluation endpoints."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.forecast import Forecast
from app.models.model_evaluation import ModelEvaluation
from app.models.model_version import ModelVersion
from app.schemas.analytics import (
    ForecastPoint,
    ModelEvaluationResponse,
    ModelVersionResponse,
)

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])


@router.get("/generation", response_model=List[ForecastPoint])
def get_generation_forecasts(
    model_version_id: Optional[int] = Query(None),
    forecast_mode: Optional[str] = Query(None, description="test_evaluation or future_forecast"),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Return stored generation forecast points."""
    q = db.query(Forecast).filter(Forecast.forecast_type == "solar_generation")
    if model_version_id:
        q = q.filter(Forecast.model_version_id == model_version_id)
    if forecast_mode:
        q = q.filter(Forecast.forecast_mode == forecast_mode)
    return q.order_by(Forecast.forecast_for).limit(limit).all()


@router.get("/demand", response_model=List[ForecastPoint])
def get_demand_forecasts(
    model_version_id: Optional[int] = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Return stored demand forecast points (if demand module is active)."""
    q = db.query(Forecast).filter(Forecast.forecast_type == "demand")
    if model_version_id:
        q = q.filter(Forecast.model_version_id == model_version_id)
    rows = q.order_by(Forecast.forecast_for).limit(limit).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No demand forecasts available. Demand forecasting is conditional on compatible data.",
        )
    return rows


@router.get("/models", response_model=List[ModelVersionResponse])
def list_model_versions(
    task: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    db: Session = Depends(get_db),
):
    """Return registered model versions."""
    q = db.query(ModelVersion)
    if task:
        q = q.filter(ModelVersion.task == task)
    if status:
        q = q.filter(ModelVersion.status == status)
    return q.order_by(ModelVersion.created_at.desc()).all()


@router.get("/models/evaluations", response_model=List[ModelEvaluationResponse])
def get_model_evaluations(
    model_version_id: Optional[int] = Query(None),
    split_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return model evaluation metrics for comparison."""
    q = db.query(ModelEvaluation)
    if model_version_id:
        q = q.filter(ModelEvaluation.model_version_id == model_version_id)
    if split_name:
        q = q.filter(ModelEvaluation.split_name == split_name)
    return q.order_by(ModelEvaluation.created_at.desc()).all()


@router.get("/models/evaluations/summary")
def get_evaluations_summary(
    split_name: str = Query("test"),
    db: Session = Depends(get_db),
):
    """Return a comparison table of all models on the specified split."""
    evals = (
        db.query(ModelEvaluation, ModelVersion)
        .join(ModelVersion, ModelEvaluation.model_version_id == ModelVersion.id)
        .filter(ModelEvaluation.split_name == split_name)
        .filter(ModelVersion.status == "active")
        .order_by(ModelEvaluation.mae)
        .all()
    )

    return [
        {
            "model_type": mv.model_type,
            "version_tag": mv.version_tag,
            "split_name": ev.split_name,
            "mae": ev.mae,
            "rmse": ev.rmse,
            "r2": ev.r2,
            "mape": ev.mape,
            "baseline_mae": ev.baseline_mae,
            "mae_vs_baseline_pct": (
                round((1 - ev.mae / ev.baseline_mae) * 100, 1)
                if ev.mae and ev.baseline_mae and ev.baseline_mae > 0
                else None
            ),
            "n_samples": ev.n_samples,
            "feature_importances": (
                json.loads(ev.feature_importances) if ev.feature_importances else None
            ),
        }
        for ev, mv in evals
    ]
