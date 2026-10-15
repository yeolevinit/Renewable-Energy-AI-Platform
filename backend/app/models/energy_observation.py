"""ORM model for solar/renewable energy generation observations."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class EnergyObservation(Base):
    __tablename__ = "energy_observations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    # Timestamp of the observation (UTC-normalized)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    site_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Solar irradiance or generation value
    generation_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Instantaneous power if available
    power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Direct Normal Irradiance (W/m²)
    dni: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Global Horizontal Irradiance (W/m²)
    ghi: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Diffuse Horizontal Irradiance (W/m²)
    dhi: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kWh")
    is_valid: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_energy_obs_source_time", "source_id", "observed_at"),
        Index("ix_energy_obs_site_time", "site_id", "observed_at"),
    )
