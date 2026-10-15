"""ORM model for stored forecast predictions."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False
    )
    # The timestamp being predicted
    forecast_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # When this forecast was generated
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # "solar_generation" | "demand"
    forecast_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kWh")
    site_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # "test_evaluation" | "future_forecast"
    forecast_mode: Mapped[str] = mapped_column(String(30), default="test_evaluation")

    __table_args__ = (
        Index("ix_forecast_type_time", "forecast_type", "forecast_for"),
    )
