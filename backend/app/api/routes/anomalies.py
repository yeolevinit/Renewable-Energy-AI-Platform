"""Anomaly alert endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.anomaly_alert import AnomalyAlert
from app.schemas.analytics import AnomalyAlertResponse, UpdateAlertStatusRequest

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])

_VALID_STATUSES = {"open", "reviewed", "resolved", "false_positive"}
_VALID_SEVERITIES = {"low", "medium", "high"}


@router.get("", response_model=List[AnomalyAlertResponse])
def list_anomalies(
    series_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    start: Optional[str] = Query(None, description="ISO date string"),
    end: Optional[str] = Query(None, description="ISO date string"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Return anomaly alerts with optional filters."""
    q = db.query(AnomalyAlert)

    if series_type:
        q = q.filter(AnomalyAlert.series_type == series_type)
    if severity:
        if severity not in _VALID_SEVERITIES:
            raise HTTPException(status_code=422, detail=f"severity must be one of {_VALID_SEVERITIES}")
        q = q.filter(AnomalyAlert.severity == severity)
    if review_status:
        if review_status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"review_status must be one of {_VALID_STATUSES}")
        q = q.filter(AnomalyAlert.review_status == review_status)
    if start:
        q = q.filter(AnomalyAlert.observed_at >= datetime.fromisoformat(start))
    if end:
        q = q.filter(AnomalyAlert.observed_at <= datetime.fromisoformat(end))

    return q.order_by(AnomalyAlert.observed_at.desc()).limit(limit).all()


@router.get("/summary")
def get_anomaly_summary(db: Session = Depends(get_db)):
    """Return counts by severity and status."""
    from sqlalchemy import func

    severity_counts = (
        db.query(AnomalyAlert.severity, func.count(AnomalyAlert.id))
        .group_by(AnomalyAlert.severity)
        .all()
    )
    status_counts = (
        db.query(AnomalyAlert.review_status, func.count(AnomalyAlert.id))
        .group_by(AnomalyAlert.review_status)
        .all()
    )
    total = db.query(func.count(AnomalyAlert.id)).scalar()

    return {
        "total": total,
        "by_severity": {s: c for s, c in severity_counts},
        "by_status": {s: c for s, c in status_counts},
    }


@router.get("/{alert_id}", response_model=AnomalyAlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/status", response_model=AnomalyAlertResponse)
def update_alert_status(
    alert_id: int,
    payload: UpdateAlertStatusRequest,
    db: Session = Depends(get_db),
):
    """Update the review status of an anomaly alert."""
    alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.review_status = payload.review_status
    if payload.review_notes:
        alert.review_notes = payload.review_notes
    db.flush()
    return alert
