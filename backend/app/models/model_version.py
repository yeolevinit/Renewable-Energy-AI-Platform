"""ORM model for trained ML model versions and metadata."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # e.g. "solar_generation_forecast", "demand_forecast", "anomaly_detection"
    task: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "xgboost", "random_forest", "linear_regression", "persistence_baseline"
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False)
    # Dates as ISO strings (actual datetime objects stored separately in evaluation)
    train_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    train_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # JSON string of feature names used
    feature_list: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON string of hyperparameters
    hyperparameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "active" | "archived" | "failed"
    status: Mapped[str] = mapped_column(String(20), default="active")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
