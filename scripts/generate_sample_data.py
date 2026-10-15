"""
Sample dataset generator.

Produces realistic synthetic hourly solar generation and weather data
for 2 years (2022-2023) for a hypothetical 100 kWp rooftop solar installation
in Pune, India (lat 18.52, lon 73.86).

Outputs:
  data/samples/solar_generation_sample.csv
  data/samples/weather_sample.csv
  data/samples/demand_sample.csv  (simplified regional proxy)

IMPORTANT: This data is entirely synthetic and is intended only for
development, testing, and demonstration. It must not be presented as
real measured data in academic or operational contexts.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
SEED = 42
START = "2022-01-01"
END = "2023-12-31 23:00"
CAPACITY_KWP = 100.0   # installed capacity
LATITUDE = 18.52
LONGITUDE = 73.86

rng = np.random.default_rng(SEED)

# ── Time index ────────────────────────────────────────────────────────────────
idx = pd.date_range(START, END, freq="h", tz="UTC")
n = len(idx)
df = pd.DataFrame({"timestamp": idx})

hour = idx.hour.values
doy = idx.dayofyear.values
month = idx.month.values

# ── Solar irradiance simulation ───────────────────────────────────────────────
# Seasonal amplitude: higher in summer months for India (March-May peak)
seasonal = 0.5 + 0.4 * np.cos(2 * np.pi * (doy - 80) / 365)  # peaks ~March
# Daily bell curve centered at solar noon (~12 UTC+5:30 → ~6:30 UTC)
solar_noon_utc = 6.5
daily = np.maximum(0, np.cos(np.pi * (hour - solar_noon_utc) / 6))
daily[hour < 1] = 0
daily[hour > 12] = 0

# Base GHI (W/m²)
ghi_base = 950 * seasonal * daily
# Add cloud noise
cloud_cover = np.clip(
    0.2 + 0.3 * np.sin(2 * np.pi * doy / 365 + rng.normal(0, 0.1, n))
    + rng.normal(0, 0.15, n),
    0, 1
)
# Monsoon boost (June-September)
monsoon_mask = (month >= 6) & (month <= 9)
cloud_cover[monsoon_mask] = np.clip(cloud_cover[monsoon_mask] + 0.35, 0, 1)

ghi = ghi_base * (1 - 0.7 * cloud_cover) + rng.normal(0, 5, n)
ghi = np.clip(ghi, 0, 1100)

dni = ghi * (1 - 0.3 * cloud_cover)
dhi = ghi - dni * np.maximum(0, np.cos(np.pi * (hour - solar_noon_utc) / 12))
dhi = np.clip(dhi, 0, ghi)
dni = np.clip(dni, 0, 1000)

# ── Temperature (°C) ─────────────────────────────────────────────────────────
temp_base = 25 + 8 * np.sin(2 * np.pi * (doy - 60) / 365)
temp_diurnal = 5 * np.sin(2 * np.pi * (hour - 6) / 24)
temperature = temp_base + temp_diurnal + rng.normal(0, 1.5, n)

# ── Generation (kWh per hour) ─────────────────────────────────────────────────
# PR (Performance Ratio) varies with temperature: 0.75 base, -0.004/°C above 25
pr = np.clip(0.78 - 0.004 * np.maximum(0, temperature - 25), 0.5, 0.85)
generation = (ghi / 1000) * CAPACITY_KWP * pr
generation = np.clip(generation, 0, CAPACITY_KWP)
# Add realistic noise and occasional zero events (shading, outages)
noise = rng.normal(0, 0.02 * generation + 0.01)
generation = np.clip(generation + noise, 0, CAPACITY_KWP)

# Inject ~3 anomalous low-generation periods (simulated faults)
fault_starts = [1200, 5000, 12000]
for fs in fault_starts:
    if fs + 5 < n:
        generation[fs:fs+5] *= 0.15

# Night hours must be exactly zero
generation[(hour < 1) | (hour > 12)] = 0.0

# ── Build solar generation CSV ────────────────────────────────────────────────
solar_df = pd.DataFrame({
    "timestamp": idx,
    "generation_kwh": np.round(generation, 4),
    "ghi": np.round(ghi, 2),
    "dni": np.round(dni, 2),
    "dhi": np.round(dhi, 2),
    "temperature_c": np.round(temperature, 2),
    "site_id": "pune_rooftop_100kwp",
})

# ── Build weather CSV ─────────────────────────────────────────────────────────
wind_speed = np.clip(3 + 2 * np.sin(2 * np.pi * doy / 365) + rng.normal(0, 1, n), 0, 25)
humidity = np.clip(55 + 25 * np.sin(2 * np.pi * (doy - 150) / 365) + rng.normal(0, 5, n), 20, 99)
precipitation = np.where(
    monsoon_mask & (rng.uniform(0, 1, n) < 0.15),
    rng.exponential(3, n),
    0.0
)

weather_df = pd.DataFrame({
    "timestamp": idx,
    "temperature_c": np.round(temperature, 2),
    "cloud_cover_pct": np.round(cloud_cover * 100, 1),
    "precipitation_mm": np.round(precipitation, 2),
    "wind_speed_ms": np.round(wind_speed, 2),
    "wind_direction_deg": np.round(rng.uniform(0, 360, n), 1),
    "relative_humidity_pct": np.round(humidity, 1),
    "shortwave_radiation_wm2": np.round(ghi, 2),
    "direct_radiation_wm2": np.round(dni, 2),
    "diffuse_radiation_wm2": np.round(dhi, 2),
    "location_id": "pune_india",
})

# ── Build simplified demand CSV ───────────────────────────────────────────────
# Illustrative regional demand proxy — NOT real grid data.
# Daily shape: morning peak (8-10), evening peak (18-21).
demand_base = 500  # kWh/hour (small distribution feeder scale)
morning_peak = 1.5 * np.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
evening_peak = 1.8 * np.exp(-0.5 * ((hour - 19) / 2.0) ** 2)
night_dip = 0.6 + 0.1 * np.sin(2 * np.pi * hour / 24)
demand_shape = night_dip + morning_peak + evening_peak
seasonal_demand = 1 + 0.2 * np.sin(2 * np.pi * (doy - 200) / 365)
demand = demand_base * demand_shape * seasonal_demand
demand = np.clip(demand + rng.normal(0, 15, n), 200, 1500)

demand_df = pd.DataFrame({
    "timestamp": idx,
    "demand_kwh": np.round(demand, 2),
    "region_id": "pune_feeder_illustrative",
})

# ── Save files ────────────────────────────────────────────────────────────────
out_dir = Path(__file__).resolve().parent.parent / "data" / "samples"
out_dir.mkdir(parents=True, exist_ok=True)

solar_path = out_dir / "solar_generation_sample.csv"
weather_path = out_dir / "weather_sample.csv"
demand_path = out_dir / "demand_sample.csv"

solar_df.to_csv(solar_path, index=False)
weather_df.to_csv(weather_path, index=False)
demand_df.to_csv(demand_path, index=False)

print(f"[OK] Solar generation:  {solar_path}  ({len(solar_df):,} rows)")
print(f"[OK] Weather:           {weather_path}  ({len(weather_df):,} rows)")
print(f"[OK] Demand (proxy):    {demand_path}  ({len(demand_df):,} rows)")
print()
print("NOTE: These files contain SYNTHETIC data for development/testing only.")
print("      Do not present as real measured generation, weather, or demand.")
