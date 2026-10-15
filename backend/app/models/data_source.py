"""ORM model for registered data sources."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "solar_generation", "weather", "demand"
    data_category: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    licence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_scope: Mapped[str | None] = mapped_column(String(200), nullable=True)
    temporal_resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "hourly", "daily"
    date_coverage_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_coverage_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    units: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
