"""Unit tests for the data quality engine."""

import pytest
from app.pipeline.validator import ValidationResult
from app.pipeline.quality_engine import (
    compute_quality_score,
    readiness_label,
    build_quality_report,
)


def _perfect_result(total=1000):
    r = ValidationResult()
    r.total_rows = total
    return r


def _bad_result(total=1000):
    r = ValidationResult()
    r.total_rows = total
    r.duplicate_rows = 400          # 40% duplicates
    r.out_of_range_rows = 300       # 30% out of range
    r.time_gap_count = 200          # 20% gap rate
    r.missing_by_column = {"generation_kwh": 600}  # 60% missing
    return r


def test_perfect_data_scores_near_100():
    score = compute_quality_score(_perfect_result())
    assert score >= 95.0


def test_bad_data_scores_low():
    score = compute_quality_score(_bad_result())
    assert score < 60.0


def test_empty_data_scores_zero():
    r = ValidationResult()
    r.total_rows = 0
    assert compute_quality_score(r) == 0.0


def test_score_clamped_0_to_100():
    score = compute_quality_score(_perfect_result())
    assert 0.0 <= score <= 100.0
    score2 = compute_quality_score(_bad_result())
    assert 0.0 <= score2 <= 100.0


def test_readiness_good():
    assert readiness_label(90.0) == "good"
    assert readiness_label(80.0) == "good"


def test_readiness_warning():
    assert readiness_label(70.0) == "warning"
    assert readiness_label(50.0) == "warning"


def test_readiness_poor():
    assert readiness_label(49.9) == "poor"
    assert readiness_label(0.0) == "poor"


def test_build_quality_report_keys():
    r = _perfect_result()
    report = build_quality_report(r, pipeline_run_id=1, source_id=2)
    required_keys = [
        "pipeline_run_id", "source_id", "total_rows", "missing_rows",
        "duplicate_rows", "invalid_rows", "timestamp_errors",
        "out_of_range_values", "time_gap_count", "quality_score",
        "column_missingness", "validation_issues", "readiness_status",
    ]
    for key in required_keys:
        assert key in report, f"Missing key: {key}"


def test_build_quality_report_correct_ids():
    r = _perfect_result()
    report = build_quality_report(r, pipeline_run_id=7, source_id=3)
    assert report["pipeline_run_id"] == 7
    assert report["source_id"] == 3


def test_build_quality_report_good_status():
    r = _perfect_result()
    report = build_quality_report(r)
    assert report["readiness_status"] == "good"


def test_build_quality_report_poor_status():
    r = _bad_result()
    report = build_quality_report(r)
    assert report["readiness_status"] in ("warning", "poor")
