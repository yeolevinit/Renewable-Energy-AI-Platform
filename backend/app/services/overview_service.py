"""
Overview / dashboard summary service.

Aggregates key platform metrics into a single response
consumed by the dashboard overview page.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.anomaly_alert import AnomalyAlert
from app.models.data_quality_report import DataQualityReport
from app.models.energy_observation import EnergyObservation
from app.models.model_evaluation import ModelEvaluation
from app.models.model_version import ModelVersion
from app.models.pipeline_run import PipelineRun


def get_overview(db: Session) -> dict:
    """Return a consolidated summary for the dashboard overview page."""

    # ── Generation data ───────────────────────────────────────────────────
    gen_agg = db.query(
        func.count(EnergyObservation.id),
        func.min(EnergyObservation.observed_at),
        func.max(EnergyObservation.observed_at),
    ).filter(EnergyObservation.is_valid == True).first()

    # ── Latest pipeline run ───────────────────────────────────────────────
    latest_run = (
        db.query(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .first()
    )

    # ── Latest quality report ─────────────────────────────────────────────
    latest_qr = (
        db.query(DataQualityReport)
        .order_by(DataQualityReport.created_at.desc())
        .first()
    )

    # ── Open anomaly alerts ───────────────────────────────────────────────
    open_alerts = db.query(func.count(AnomalyAlert.id)).filter(
        AnomalyAlert.review_status == "open"
    ).scalar()

    high_alerts = db.query(func.count(AnomalyAlert.id)).filter(
        AnomalyAlert.review_status == "open",
        AnomalyAlert.severity == "high",
    ).scalar()

    # ── Best model on test split ──────────────────────────────────────────
    best_eval = (
        db.query(ModelEvaluation, ModelVersion)
        .join(ModelVersion, ModelEvaluation.model_version_id == ModelVersion.id)
        .filter(
            ModelEvaluation.split_name == "test",
            ModelVersion.status == "active",
            ModelEvaluation.mae.isnot(None),
        )
        .order_by(ModelEvaluation.mae)
        .first()
    )

    return {
        "generation_data": {
            "total_rows": gen_agg[0] or 0,
            "earliest": str(gen_agg[1]) if gen_agg[1] else None,
            "latest": str(gen_agg[2]) if gen_agg[2] else None,
        },
        "latest_pipeline_run": {
            "id": latest_run.id if latest_run else None,
            "status": latest_run.status if latest_run else None,
            "completed_at": str(latest_run.completed_at) if latest_run and latest_run.completed_at else None,
            "rows_written": latest_run.rows_written if latest_run else 0,
        },
        "data_quality": {
            "quality_score": latest_qr.quality_score if latest_qr else None,
            "readiness_status": latest_qr.readiness_status if latest_qr else "unknown",
            "total_rows": latest_qr.total_rows if latest_qr else 0,
        },
        "anomalies": {
            "open_count": open_alerts or 0,
            "high_severity_count": high_alerts or 0,
        },
        "best_model": {
            "model_type": best_eval[1].model_type if best_eval else None,
            "version_tag": best_eval[1].version_tag if best_eval else None,
            "test_mae": round(best_eval[0].mae, 4) if best_eval and best_eval[0].mae else None,
            "test_rmse": round(best_eval[0].rmse, 4) if best_eval and best_eval[0].rmse else None,
        },
    }
