"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-10-15

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── data_sources ────────────────────────────────────────────────────────
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("data_category", sa.String(50), nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("licence_notes", sa.Text, nullable=True),
        sa.Column("geographic_scope", sa.String(200), nullable=True),
        sa.Column("temporal_resolution", sa.String(50), nullable=True),
        sa.Column("date_coverage_start", sa.String(20), nullable=True),
        sa.Column("date_coverage_end", sa.String(20), nullable=True),
        sa.Column("units", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("local_file_path", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── pipeline_runs ────────────────────────────────────────────────────────
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_read", sa.Integer, server_default="0"),
        sa.Column("rows_written", sa.Integer, server_default="0"),
        sa.Column("rows_rejected", sa.Integer, server_default="0"),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("pipeline_stage", sa.String(100), nullable=True),
        sa.Column("config_snapshot", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── energy_observations ──────────────────────────────────────────────────
    op.create_table(
        "energy_observations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("site_id", sa.String(100), nullable=True),
        sa.Column("generation_kwh", sa.Float, nullable=True),
        sa.Column("power_kw", sa.Float, nullable=True),
        sa.Column("dni", sa.Float, nullable=True),
        sa.Column("ghi", sa.Float, nullable=True),
        sa.Column("dhi", sa.Float, nullable=True),
        sa.Column("temperature_c", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kWh"),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_energy_obs_id", "energy_observations", ["id"])
    op.create_index("ix_energy_obs_observed_at", "energy_observations", ["observed_at"])
    op.create_index("ix_energy_obs_source_time", "energy_observations", ["source_id", "observed_at"])
    op.create_index("ix_energy_obs_site_time", "energy_observations", ["site_id", "observed_at"])

    # ── weather_observations ─────────────────────────────────────────────────
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_id", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("temperature_c", sa.Float, nullable=True),
        sa.Column("cloud_cover_pct", sa.Float, nullable=True),
        sa.Column("precipitation_mm", sa.Float, nullable=True),
        sa.Column("wind_speed_ms", sa.Float, nullable=True),
        sa.Column("wind_direction_deg", sa.Float, nullable=True),
        sa.Column("relative_humidity_pct", sa.Float, nullable=True),
        sa.Column("shortwave_radiation_wm2", sa.Float, nullable=True),
        sa.Column("direct_radiation_wm2", sa.Float, nullable=True),
        sa.Column("diffuse_radiation_wm2", sa.Float, nullable=True),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_weather_obs_id", "weather_observations", ["id"])
    op.create_index("ix_weather_obs_observed_at", "weather_observations", ["observed_at"])
    op.create_index("ix_weather_obs_source_time", "weather_observations", ["source_id", "observed_at"])

    # ── demand_observations ──────────────────────────────────────────────────
    op.create_table(
        "demand_observations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("region_id", sa.String(100), nullable=True),
        sa.Column("demand_kwh", sa.Float, nullable=True),
        sa.Column("demand_kw", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kWh"),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_demand_obs_id", "demand_observations", ["id"])
    op.create_index("ix_demand_obs_source_time", "demand_observations", ["source_id", "observed_at"])

    # ── data_quality_reports ─────────────────────────────────────────────────
    op.create_table(
        "data_quality_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_rows", sa.Integer, server_default="0"),
        sa.Column("missing_rows", sa.Integer, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer, server_default="0"),
        sa.Column("invalid_rows", sa.Integer, server_default="0"),
        sa.Column("timestamp_errors", sa.Integer, server_default="0"),
        sa.Column("out_of_range_values", sa.Integer, server_default="0"),
        sa.Column("time_gap_count", sa.Integer, server_default="0"),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("column_missingness", sa.Text, nullable=True),
        sa.Column("validation_issues", sa.Text, nullable=True),
        sa.Column("readiness_status", sa.String(20), server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── model_versions ───────────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("version_tag", sa.String(50), nullable=False),
        sa.Column("train_start", sa.String(20), nullable=True),
        sa.Column("train_end", sa.String(20), nullable=True),
        sa.Column("feature_list", sa.Text, nullable=True),
        sa.Column("hyperparameters", sa.Text, nullable=True),
        sa.Column("artifact_path", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── model_evaluations ────────────────────────────────────────────────────
    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_version_id", sa.Integer, sa.ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("split_name", sa.String(20), nullable=False),
        sa.Column("split_start", sa.String(20), nullable=True),
        sa.Column("split_end", sa.String(20), nullable=True),
        sa.Column("n_samples", sa.Integer, server_default="0"),
        sa.Column("mae", sa.Float, nullable=True),
        sa.Column("rmse", sa.Float, nullable=True),
        sa.Column("r2", sa.Float, nullable=True),
        sa.Column("mape", sa.Float, nullable=True),
        sa.Column("baseline_mae", sa.Float, nullable=True),
        sa.Column("baseline_rmse", sa.Float, nullable=True),
        sa.Column("extra_metrics", sa.Text, nullable=True),
        sa.Column("feature_importances", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── forecasts ────────────────────────────────────────────────────────────
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_version_id", sa.Integer, sa.ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("forecast_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("forecast_type", sa.String(50), nullable=False),
        sa.Column("predicted_value", sa.Float, nullable=False),
        sa.Column("actual_value", sa.Float, nullable=True),
        sa.Column("lower_bound", sa.Float, nullable=True),
        sa.Column("upper_bound", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), server_default="kWh"),
        sa.Column("site_id", sa.String(100), nullable=True),
        sa.Column("forecast_mode", sa.String(30), server_default="test_evaluation"),
    )
    op.create_index("ix_forecasts_id", "forecasts", ["id"])
    op.create_index("ix_forecasts_forecast_for", "forecasts", ["forecast_for"])
    op.create_index("ix_forecast_type_time", "forecasts", ["forecast_type", "forecast_for"])

    # ── anomaly_alerts ───────────────────────────────────────────────────────
    op.create_table(
        "anomaly_alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("series_type", sa.String(50), nullable=False),
        sa.Column("site_id", sa.String(100), nullable=True),
        sa.Column("observed_value", sa.Float, nullable=True),
        sa.Column("expected_value", sa.Float, nullable=True),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("detection_method", sa.String(50), nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("review_status", sa.String(20), server_default="open"),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anomaly_alerts_id", "anomaly_alerts", ["id"])
    op.create_index("ix_anomaly_alerts_observed_at", "anomaly_alerts", ["observed_at"])

    # ── scenarios ────────────────────────────────────────────────────────────
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("analysis_start", sa.String(20), nullable=False),
        sa.Column("analysis_end", sa.String(20), nullable=False),
        sa.Column("assumptions", sa.Text, nullable=True),
        sa.Column("total_generation_kwh", sa.Float, nullable=True),
        sa.Column("total_demand_kwh", sa.Float, nullable=True),
        sa.Column("net_balance_kwh", sa.Float, nullable=True),
        sa.Column("balance_status", sa.String(30), nullable=True),
        sa.Column("result_series", sa.Text, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("scenarios")
    op.drop_table("anomaly_alerts")
    op.drop_table("forecasts")
    op.drop_table("model_evaluations")
    op.drop_table("model_versions")
    op.drop_table("data_quality_reports")
    op.drop_table("demand_observations")
    op.drop_table("weather_observations")
    op.drop_table("energy_observations")
    op.drop_table("pipeline_runs")
    op.drop_table("data_sources")
