"""ORM model for model evaluation results on chronological splits."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False
    )
    # "validation" | "test"
    split_name: Mapped[str] = mapped_column(String(20), nullable=False)
    split_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    split_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    n_samples: Mapped[int] = mapped_column(Integer, default=0)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Baseline MAE for comparison
    baseline_mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON string with additional metrics
    extra_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON string with feature importances
    feature_importances: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
