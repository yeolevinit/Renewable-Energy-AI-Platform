"""
End-to-end prototype demo script.

Runs the complete pipeline on the synthetic sample dataset:
  1. Creates DB tables
  2. Registers a data source
  3. Ingests solar generation CSV
  4. Trains all ML models
  5. Runs anomaly detection
  6. Runs a scenario

Prints a concise status report. All data is SYNTHETIC.
"""

import os
import sys
from pathlib import Path

# Set up paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:///./reai.db")
os.environ.setdefault("DEBUG", "false")

from app.db.database import create_all_tables, db_session
from app.models.data_source import DataSource
from app.pipeline.ingestion_service import ingest_solar_csv
from app.core.logging import configure_logging

configure_logging(debug=False)

SOLAR_CSV = str(ROOT / "data" / "samples" / "solar_generation_sample.csv")


def step(n, msg):
    print(f"\n[{n}] {msg}")


def main():
    print("=" * 60)
    print(" Renewable Energy AI Platform — Prototype Demo")
    print(" NOTE: All data is SYNTHETIC — development only")
    print("=" * 60)

    # 1 — Create tables
    step(1, "Creating database tables...")
    create_all_tables()
    print("    OK")

    # 2 — Register source
    step(2, "Registering data source...")
    with db_session() as db:
        existing = db.query(DataSource).filter_by(name="pune_solar_sample").first()
        if existing:
            source_id = existing.id
            print(f"    Already exists — source_id={source_id}")
        else:
            src = DataSource(
                name="pune_solar_sample",
                source_type="csv",
                data_category="solar_generation",
                geographic_scope="Pune, India (synthetic)",
                temporal_resolution="hourly",
                date_coverage_start="2022-01-01",
                date_coverage_end="2023-12-31",
                units="kWh",
                local_file_path=SOLAR_CSV,
                description="Synthetic 100 kWp rooftop solar — DEVELOPMENT ONLY",
            )
            db.add(src)
            db.flush()
            source_id = src.id
            print(f"    Registered — source_id={source_id}")

    # 3 — Ingest CSV
    step(3, "Ingesting solar generation CSV...")
    result = ingest_solar_csv(
        file_path=SOLAR_CSV,
        source_id=source_id,
        timestamp_col="timestamp",
        generation_col="generation_kwh",
        ghi_col="ghi",
        temperature_col="temperature_c",
        site_id="pune_rooftop_100kwp",
    )
    print(f"    Rows read:    {result['rows_read']:,}")
    print(f"    Rows written: {result['rows_written']:,}")
    print(f"    Quality score:{result['quality_score']}%")
    if result["issues"]:
        print(f"    Issues:       {result['issues']}")
    if result["warnings"]:
        print(f"    Warnings ({len(result['warnings'])}): {result['warnings'][0][:80]}…")

    # 4 — Train models
    step(4, "Training solar forecasting models (70/15/15 split)...")
    import pandas as pd
    from app.ml.forecaster import train_solar_forecast_models
    from app.models.energy_observation import EnergyObservation

    with db_session() as db:
        rows = (db.query(EnergyObservation)
                .filter(EnergyObservation.source_id == source_id,
                        EnergyObservation.is_valid == True)
                .order_by(EnergyObservation.observed_at).all())

    df = pd.DataFrame([{
        "observed_at": r.observed_at,
        "generation_kwh": r.generation_kwh,
        "ghi": r.ghi,
        "temperature_c": r.temperature_c,
    } for r in rows])

    results = train_solar_forecast_models(df, target_col="generation_kwh", include_weather=True)

    for model in ["linear_regression", "random_forest", "xgboost"]:
        m = results.get(model, {}).get("test", {})
        print(f"    {model:20s}  MAE={m.get('mae', 0):.4f}  RMSE={m.get('rmse', 0):.4f}  R²={m.get('r2') or 0:.4f}")

    baseline = results.get("baseline", {})
    print(f"    {'seasonal_naive':20s}  MAE={baseline.get('mae', 0):.4f}  RMSE={baseline.get('rmse', 0):.4f}")
    print(f"    Test period: {results['split_dates']['test'][0]} to {results['split_dates']['test'][1]}")

    # 5 — Anomaly detection
    step(5, "Running anomaly detection...")
    from app.analytics.anomaly_detector import detect_statistical_anomalies, save_alerts
    alerts = detect_statistical_anomalies(df, "generation_kwh", source_id=source_id)
    saved = save_alerts(alerts)
    print(f"    Alerts detected: {saved}")

    # 6 — Scenario
    step(6, "Running what-if scenario (−20% generation)...")
    from app.analytics.energy_balance import run_scenario
    gen_sub = df[df["observed_at"].astype(str).str.startswith("2022-06")].copy()
    scenario = run_scenario(
        "June 2022 − 20% generation",
        gen_sub.rename(columns={"generation_kwh": "generation_kwh"}),
        None,
        generation_adjustment_pct=-20.0,
    )
    print(f"    Total generation: {scenario['total_generation_kwh']:,.0f} kWh")
    print(f"    Balance status:   {scenario['balance_status']}")
    print(f"    Recommendation:   {scenario['recommendation'][:80]}…")

    print("\n" + "=" * 60)
    print(" Demo complete. Start the server:")
    print("   Backend:  .\\venv\\Scripts\\uvicorn app.main:app --reload --port 8000")
    print("   Frontend: cd frontend && npm run dev")
    print("   API docs: http://localhost:8000/api/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
