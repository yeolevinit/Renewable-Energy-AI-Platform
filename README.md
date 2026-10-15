# Renewable Energy AI Platform
### AI-Driven Data Engineering and Predictive Analytics

> Final-year major engineering project — Artificial Intelligence and Data Science  
> **This is an academic prototype using historical/synthetic data. Not for operational use.**

---

## What it does

End-to-end software platform that:

1. Ingests solar generation and weather data via CSV or Open-Meteo API  
2. Validates, cleans, and stores records in PostgreSQL with quality scoring  
3. Engineers leakage-safe features and trains Linear Regression, Random Forest, and XGBoost  
4. Detects anomalous generation patterns (statistical + residual + Isolation Forest)  
5. Calculates energy-balance gaps when compatible demand data is available  
6. Runs what-if scenario simulations with user-defined assumptions  
7. Presents everything through a React + Plotly dashboard backed by FastAPI

---

## Quick start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |

### 1 — Database setup

```powershell
# Run as postgres superuser (supply your postgres password)
.\scripts\setup_database.ps1 -PgPassword "your_postgres_password"
```

Or manually:
```sql
CREATE USER reai_user WITH PASSWORD 'reai_password';
CREATE DATABASE renewable_energy_ai OWNER reai_user;
GRANT ALL PRIVILEGES ON DATABASE renewable_energy_ai TO reai_user;
```

### 2 — Backend

```powershell
# From project root
python -m venv venv
.\venv\Scripts\pip install -r backend\requirements.txt

# Copy and edit environment file
copy .env.example .env
# Set DATABASE_URL if different from default

# Apply migrations
$env:PYTHONPATH=".\backend"
.\venv\Scripts\alembic upgrade head

# Generate synthetic sample data
.\venv\Scripts\python scripts\generate_sample_data.py

# Start API server
$env:PYTHONPATH=".\backend"
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### 3 — Frontend

```powershell
cd frontend
npm install
npm run dev       # http://localhost:3000
```

### 4 — Run tests

```powershell
# From project root
$env:PYTHONPATH=".\backend"
.\venv\Scripts\pytest backend\tests -v
```

---

## Typical workflow (using sample data)

1. **Pipeline page** → Register a source (category: `solar_generation`)  
2. **Pipeline page → Ingest Solar CSV** → Use `data/samples/solar_generation_sample.csv`  
3. **Data Quality page** → Review validation results and quality score  
4. **Generation page** → Explore historical generation series  
5. **Models page** → Select the source and click "Train models"  
6. **Models page** → Compare MAE/RMSE across Linear Regression, Random Forest, XGBoost  
7. **Anomalies page** → Review flagged observations  
8. **Scenario Lab** → Run a what-if with e.g. −20% generation adjustment  

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── analytics/       # Anomaly detection, energy balance
│   │   ├── core/            # Config, logging
│   │   ├── db/              # SQLAlchemy engine, session
│   │   ├── ml/              # Feature engineering, forecaster, metrics
│   │   ├── models/          # ORM models (11 tables)
│   │   ├── pipeline/        # Validator, transformer, loader, quality engine
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Overview aggregation service
│   │   └── main.py          # FastAPI app entry point
│   ├── alembic/             # Database migrations
│   └── tests/               # 93 unit + integration tests
├── frontend/
│   └── src/
│       ├── components/      # Layout, PlotWrapper, KpiCard, etc.
│       ├── pages/           # 9 dashboard pages
│       └── services/api.js  # Axios API client
├── data/
│   └── samples/             # Synthetic sample CSVs (2 years hourly)
├── scripts/
│   ├── generate_sample_data.py
│   └── setup_database.ps1
└── docs/
```

---

## Technology stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy 2, PostgreSQL, Pandas, Scikit-learn, XGBoost, Alembic, Pytest  
**Frontend:** React 19, Vite, React Router, TanStack Query, Plotly.js, Axios  
**ML:** Linear Regression, Random Forest, XGBoost, Isolation Forest  
**Data sources:** CSV files, Open-Meteo historical weather API (free, no key)

---

## Important caveats

- **Synthetic sample data** — `data/samples/` files are generated for development only. Do not present as real measurements.
- **Demand module** — conditional on sourcing a compatible demand dataset with matching time intervals, units, and geographic boundary.
- **Anomaly alerts** — indicate unusual observations for investigation. They do not confirm equipment failure.
- **Scenario outputs** — simulated estimates under user-defined assumptions. Not operational forecasts.
- **MAPE** — only reported when zero-generation hours are excluded (clearly labelled).

---

## Dataset audit

See `docs/dataset_audit.md` for candidate source evaluation, provenance, and licence notes.
