"""
Data quality engine.

Computes a structured quality report from a validated DataFrame
and a ValidationResult.  Quality score is a weighted composite
of completeness, duplicate rate, invalid range rate, and gap rate.
"""

from __future__ import annotations

import json
from typing import Optional

import pandas as pd

from app.core.logging import get_logger
from app.pipeline.validator import ValidationResult

logger = get_logger(__name__)

# ─── Quality score weights (must sum to 1.0) ─────────────────────────────────
_W_COMPLETENESS = 0.40
_W_DUPLICATES   = 0.20
_W_RANGE        = 0.20
_W_GAPS         = 0.20


def compute_quality_score(result: ValidationResult) -> float:
    """
    Compute a 0–100 quality score from a ValidationResult.

    Components:
    - Completeness: fraction of non-missing values across all cells
    - Duplicate rate: fraction of duplicate rows (lower = better)
    - Out-of-range rate: fraction of out-of-range rows (lower = better)
    - Gap rate: penalizes time gaps relative to total rows
    """
    n = result.total_rows
    if n == 0:
        return 0.0

    # Completeness (missing rows / total rows — row-level approximation)
    missing_rows = sum(result.missing_by_column.values())
    # Use a row-level approximation: max missing across any column
    max_missing = max(result.missing_by_column.values()) if result.missing_by_column else 0
    completeness = 1.0 - (max_missing / n)

    # Duplicate penalty
    dup_rate = result.duplicate_rows / n
    dup_score = 1.0 - dup_rate

    # Out-of-range penalty
    range_rate = result.out_of_range_rows / n
    range_score = 1.0 - min(range_rate, 1.0)

    # Gap penalty — cap at 0.5 gaps per row
    gap_rate = min(result.time_gap_count / n, 0.5) * 2  # normalize to 0–1
    gap_score = 1.0 - gap_rate

    composite = (
        _W_COMPLETENESS * completeness
        + _W_DUPLICATES * dup_score
        + _W_RANGE * range_score
        + _W_GAPS * gap_score
    )
    return round(min(max(composite * 100.0, 0.0), 100.0), 2)


def readiness_label(score: float) -> str:
    """Map quality score to a human-readable readiness label."""
    if score >= 80:
        return "good"
    elif score >= 50:
        return "warning"
    return "poor"


def build_quality_report(
    result: ValidationResult,
    pipeline_run_id: Optional[int] = None,
    source_id: Optional[int] = None,
) -> dict:
    """
    Build a dict ready for database insertion into data_quality_reports.
    """
    score = compute_quality_score(result)
    status = readiness_label(score)

    column_missingness_json = json.dumps(result.missing_by_column)
    validation_issues_json = json.dumps(
        {"issues": result.issues, "warnings": result.warnings}
    )

    report = {
        "pipeline_run_id": pipeline_run_id,
        "source_id": source_id,
        "total_rows": result.total_rows,
        "missing_rows": result.total_missing,
        "duplicate_rows": result.duplicate_rows,
        "invalid_rows": result.out_of_range_rows,
        "timestamp_errors": result.timestamp_errors,
        "out_of_range_values": result.out_of_range_rows,
        "time_gap_count": result.time_gap_count,
        "quality_score": score,
        "column_missingness": column_missingness_json,
        "validation_issues": validation_issues_json,
        "readiness_status": status,
    }

    logger.info(
        "quality_report_built",
        source_id=source_id,
        quality_score=score,
        status=status,
    )
    return report
