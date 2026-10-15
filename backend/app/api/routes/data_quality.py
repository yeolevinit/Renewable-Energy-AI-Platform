"""Data quality report endpoints."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.data_quality_report import DataQualityReport
from app.schemas.analytics import DataQualityReportResponse

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/latest", response_model=DataQualityReportResponse)
def get_latest_quality_report(
    source_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return the most recent data quality report, optionally filtered by source."""
    from fastapi import HTTPException

    q = db.query(DataQualityReport)
    if source_id is not None:
        q = q.filter(DataQualityReport.source_id == source_id)
    report = q.order_by(DataQualityReport.created_at.desc()).first()
    if not report:
        raise HTTPException(status_code=404, detail="No data quality reports found")
    return report


@router.get("", response_model=List[DataQualityReportResponse])
def list_quality_reports(
    source_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return data quality reports, newest first."""
    q = db.query(DataQualityReport)
    if source_id is not None:
        q = q.filter(DataQualityReport.source_id == source_id)
    return q.order_by(DataQualityReport.created_at.desc()).limit(limit).all()


@router.get("/{report_id}/detail")
def get_quality_detail(report_id: int, db: Session = Depends(get_db)):
    """Return a quality report with parsed JSON fields expanded."""
    from fastapi import HTTPException

    report = db.query(DataQualityReport).filter(DataQualityReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    col_miss = {}
    val_issues = {}
    try:
        if report.column_missingness:
            col_miss = json.loads(report.column_missingness)
        if report.validation_issues:
            val_issues = json.loads(report.validation_issues)
    except json.JSONDecodeError:
        pass

    return {
        "id": report.id,
        "source_id": report.source_id,
        "pipeline_run_id": report.pipeline_run_id,
        "total_rows": report.total_rows,
        "missing_rows": report.missing_rows,
        "duplicate_rows": report.duplicate_rows,
        "invalid_rows": report.invalid_rows,
        "timestamp_errors": report.timestamp_errors,
        "time_gap_count": report.time_gap_count,
        "quality_score": report.quality_score,
        "readiness_status": report.readiness_status,
        "column_missingness": col_miss,
        "validation_issues": val_issues,
        "created_at": report.created_at,
    }
