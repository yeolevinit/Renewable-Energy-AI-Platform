"""ORM model for data quality reports generated after each pipeline run."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    missing_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    timestamp_errors: Mapped[int] = mapped_column(Integer, default=0)
    out_of_range_values: Mapped[int] = mapped_column(Integer, default=0)
    time_gap_count: Mapped[int] = mapped_column(Integer, default=0)
    # Composite quality score 0-100 (higher = better)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON string with per-column missingness details
    column_missingness: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON string with validation issue details
    validation_issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Overall assessment: "good" | "warning" | "poor"
    readiness_status: Mapped[str] = mapped_column(String(20), default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
