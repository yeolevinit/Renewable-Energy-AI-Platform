"""Pipeline and data-source Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    name: str
    source_type: str
    data_category: str
    url: Optional[str] = None
    licence_notes: Optional[str] = None
    geographic_scope: Optional[str] = None
    temporal_resolution: Optional[str] = None
    date_coverage_start: Optional[str] = None
    date_coverage_end: Optional[str] = None
    units: Optional[str] = None
    description: Optional[str] = None
    local_file_path: Optional[str] = None


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceResponse(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: Optional[int]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    rows_read: int
    rows_written: int
    rows_rejected: int
    pipeline_stage: Optional[str]
    error_summary: Optional[str]
    created_at: datetime


class IngestCSVRequest(BaseModel):
    source_id: int
    file_path: str = Field(..., description="Absolute or relative path to the CSV file")
    timestamp_col: str = "timestamp"
    generation_col: str = "generation_kwh"
    ghi_col: Optional[str] = None
    dni_col: Optional[str] = None
    dhi_col: Optional[str] = None
    temperature_col: Optional[str] = None
    site_id: Optional[str] = None
    unit: str = "kWh"
    expected_interval: str = "hourly"


class IngestOpenMeteoRequest(BaseModel):
    source_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    location_id: Optional[str] = None


class PipelineRunResult(BaseModel):
    run_id: int
    rows_read: int
    rows_written: int
    rows_rejected: int
    quality_score: Optional[float]
    issues: List[str]
    warnings: List[str]
