# Dataset Audit

## Status: Feasibility investigation — selections not yet finalised

All entries below are candidate sources requiring verification of licence, temporal coverage, and field availability before use in the final project.

---

## Candidate 1 — Open-Meteo Historical Weather API

| Field | Value |
|-------|-------|
| URL | https://open-meteo.com/en/docs/historical-weather-api |
| Type | REST API |
| Coverage | Global, 1940–recent |
| Resolution | Hourly |
| Licence | CC BY 4.0 for non-commercial / academic use |
| Variables available | temperature_2m, precipitation, cloudcover, windspeed_10m, shortwave_radiation, direct_radiation, diffuse_radiation, relativehumidity_2m |
| Timezone | UTC (configurable) |
| Units | °C, mm, %, m/s, W/m² |
| API key required | No |
| Ingestion status | Implemented in `ingestion_service.ingest_open_meteo()` |
| **Limitations** | Reanalysis / modelled data, not station measurements. Accuracy varies by location. Not suitable as ground-truth solar resource without independent validation. |

---

## Candidate 2 — NREL NSRDB (National Solar Radiation Database)

| Field | Value |
|-------|-------|
| URL | https://nsrdb.nrel.gov/ |
| Type | API + downloadable CSV |
| Coverage | USA, India, other regions (varies by dataset) |
| Resolution | 30-min or hourly |
| Licence | Free for non-commercial / research use; requires registration |
| Variables | GHI, DNI, DHI, temperature, wind speed, cloud type |
| API key required | Yes (free registration at developer.nrel.gov) |
| Ingestion status | Not yet implemented; requires API key |
| **Limitations** | Access requires free API key. Indian coverage available via NSRDB India dataset. Must verify exact lat/lon availability before finalising. |

---

## Candidate 3 — Kaggle Solar Generation Dataset

| Field | Value |
|-------|-------|
| Example dataset | "Solar Power Generation Data" (multiple variants) |
| URL | https://www.kaggle.com/datasets |
| Type | CSV download |
| Coverage | Typically 1–2 plants, limited date ranges |
| Resolution | 15-min or hourly depending on dataset |
| Licence | Verify per-dataset (many are CC0 or CC BY) |
| Variables | DC power, AC power, daily yield, irradiation, ambient temperature |
| Units | kW (power) — must convert to kWh if energy over interval is needed |
| Ingestion status | Supported via `ingest_solar_csv()` with column mapping |
| **Limitations** | Provenance of Kaggle uploads must be verified against original source. Many are from a single real plant with limited temporal coverage. Units may be kW not kWh — handle carefully. |

---

## Candidate 4 — Central Electricity Authority of India (CEA)

| Field | Value |
|-------|-------|
| URL | https://cea.nic.in/ |
| Type | PDF/Excel reports, limited CSV |
| Coverage | India national grid, state-level |
| Resolution | Monthly/annual aggregate (not hourly) |
| Licence | Government of India open data; verify current terms |
| Variables | Total generation by source (GW, MWh); installed capacity |
| Ingestion status | Not implemented — no suitable hourly API identified |
| **Limitations** | Data is aggregate and high-level — not compatible for direct hourly generation-demand gap analysis against a single-site solar forecast. Could be used for context/normalisation only. A compatible hourly demand dataset for a specific feeder or distribution zone would need separate sourcing. |

---

## Synthetic Sample Data (Development Only)

| Field | Value |
|-------|-------|
| Files | `data/samples/solar_generation_sample.csv`, `weather_sample.csv`, `demand_sample.csv` |
| Generator | `scripts/generate_sample_data.py` |
| Coverage | 2022-01-01 to 2023-12-31, hourly (17,520 rows each) |
| Location | Hypothetical 100 kWp rooftop, Pune, India (18.52°N, 73.86°E) |
| **Status** | SYNTHETIC — for development and testing only. Must not be presented as real measured data in any academic submission or operational context. |

---

## Alignment Assessment

To calculate a valid generation-demand gap:

| Requirement | Solar (Open-Meteo/NSRDB) | Demand (CEA) | Compatible? |
|-------------|--------------------------|--------------|-------------|
| Hourly resolution | ✓ | ✗ (monthly) | **No** |
| Same geographic boundary | Site-specific | National | **No** |
| Same units | kWh/interval | MWh aggregate | **No** |

**Conclusion:** A meaningful generation-demand balance requires a local hourly demand dataset for the same geographic scope as the solar generation data. CEA national data is not directly comparable. This module remains conditional on sourcing a compatible dataset. Until then, the platform operates in generation-only mode with user-assumption-based scenarios.
