"""Analytics, forecast, anomaly and scenario Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Data quality ──────────────────────────────────────────────────────────────

class DataQualityReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pipeline_run_id: Optional[int]
    source_id: Optional[int]
    total_rows: int
    missing_rows: int
    duplicate_rows: int
    invalid_rows: int
    timestamp_errors: int
    out_of_range_values: int
    time_gap_count: int
    quality_score: Optional[float]
    column_missingness: Optional[str]  # JSON string
    validation_issues: Optional[str]   # JSON string
    readiness_status: str
    created_at: datetime


# ── Generation observations ───────────────────────────────────────────────────

class GenerationPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    observed_at: datetime
    generation_kwh: Optional[float]
    ghi: Optional[float] = None
    temperature_c: Optional[float] = None
    site_id: Optional[str] = None


# ── Forecasts ─────────────────────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    forecast_for: datetime
    predicted_value: float
    actual_value: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    unit: str


class ModelEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model_version_id: int
    split_name: str
    split_start: Optional[str]
    split_end: Optional[str]
    n_samples: int
    mae: Optional[float]
    rmse: Optional[float]
    r2: Optional[float]
    mape: Optional[float]
    baseline_mae: Optional[float]
    baseline_rmse: Optional[float]
    feature_importances: Optional[str]
    created_at: datetime


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task: str
    model_type: str
    version_tag: str
    train_start: Optional[str]
    train_end: Optional[str]
    feature_list: Optional[str]
    status: str
    created_at: datetime


# ── Anomaly alerts ────────────────────────────────────────────────────────────

class AnomalyAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: Optional[int]
    observed_at: datetime
    series_type: str
    site_id: Optional[str]
    observed_value: Optional[float]
    expected_value: Optional[float]
    anomaly_score: Optional[float]
    severity: str
    detection_method: str
    explanation: Optional[str]
    review_status: str
    created_at: datetime


class UpdateAlertStatusRequest(BaseModel):
    review_status: str = Field(
        ...,
        pattern="^(reviewed|resolved|false_positive|open)$",
    )
    review_notes: Optional[str] = None


# ── Scenarios ─────────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    name: str
    description: Optional[str] = None
    analysis_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    analysis_end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    generation_adjustment_pct: float = Field(
        0.0, ge=-100.0, le=200.0,
        description="Percentage adjustment to generation (e.g. -20 = 20% reduction)",
    )
    demand_adjustment_pct: float = Field(
        0.0, ge=-100.0, le=200.0,
        description="Percentage adjustment to demand",
    )


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    analysis_start: str
    analysis_end: str
    assumptions: Optional[str]
    total_generation_kwh: Optional[float]
    total_demand_kwh: Optional[float]
    net_balance_kwh: Optional[float]
    balance_status: Optional[str]
    recommendation: Optional[str]
    created_at: datetime
