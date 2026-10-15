"""ORM model for anomaly detection alerts."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    # Time of the anomalous observation
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # "solar_generation" | "weather" | "demand" | "data_quality"
    series_type: Mapped[str] = mapped_column(String(50), nullable=False)
    site_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "low" | "medium" | "high"
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # "statistical_threshold" | "residual_threshold" | "isolation_forest" | "data_quality"
    detection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "open" | "reviewed" | "resolved" | "false_positive"
    review_status: Mapped[str] = mapped_column(String(20), default="open")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
