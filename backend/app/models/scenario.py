"""ORM model for what-if scenario simulations."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Start/end as ISO date strings of the analysis window
    analysis_start: Mapped[str] = mapped_column(String(20), nullable=False)
    analysis_end: Mapped[str] = mapped_column(String(20), nullable=False)
    # JSON string of user-defined assumptions (e.g. generation_adjustment_pct)
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Summary results
    total_generation_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_demand_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_balance_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "surplus" | "deficit" | "balanced" | "generation_only"
    balance_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # JSON string with time-series of hourly/interval results
    result_series: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
