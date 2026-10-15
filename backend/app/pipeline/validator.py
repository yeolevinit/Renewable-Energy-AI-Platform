"""
Data validation engine.

Validates incoming DataFrames for:
- Required columns
- Timestamp parsing and timezone normalization
- Duplicate detection
- Numeric range checks
- Missing value analysis
- Time-series interval regularity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Collects issues found during validation of one DataFrame."""

    is_valid: bool = True
    total_rows: int = 0
    duplicate_rows: int = 0
    timestamp_errors: int = 0
    missing_by_column: Dict[str, int] = field(default_factory=dict)
    out_of_range_rows: int = 0
    time_gap_count: int = 0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_issue(self, msg: str) -> None:
        self.issues.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def total_missing(self) -> int:
        return sum(self.missing_by_column.values())


# ─── Range rules for common columns ─────────────────────────────────────────

RANGE_RULES: Dict[str, Tuple[float, float]] = {
    "generation_kwh": (0.0, 1_000_000.0),
    "power_kw": (0.0, 1_000_000.0),
    "dni": (0.0, 1500.0),      # W/m² — theoretical max ~1361
    "ghi": (0.0, 1500.0),
    "dhi": (0.0, 1500.0),
    "temperature_c": (-90.0, 60.0),
    "cloud_cover_pct": (0.0, 100.0),
    "precipitation_mm": (0.0, 2000.0),
    "wind_speed_ms": (0.0, 120.0),
    "wind_direction_deg": (0.0, 360.0),
    "relative_humidity_pct": (0.0, 100.0),
    "shortwave_radiation_wm2": (0.0, 1500.0),
    "direct_radiation_wm2": (0.0, 1500.0),
    "diffuse_radiation_wm2": (0.0, 1500.0),
    "demand_kwh": (0.0, 1_000_000_000.0),
    "demand_kw": (0.0, 1_000_000_000.0),
}

# Expected hourly intervals in minutes
EXPECTED_INTERVAL_MINUTES = {
    "hourly": 60,
    "30min": 30,
    "15min": 15,
    "daily": 1440,
}


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: List[str],
    timestamp_col: str = "timestamp",
    expected_interval: Optional[str] = "hourly",
    allow_duplicates: bool = False,
    source_name: str = "unknown",
) -> Tuple[pd.DataFrame, ValidationResult]:
    """
    Validate and normalize a raw DataFrame.

    Returns (cleaned_df, result).  The cleaned_df has:
    - timestamp_col parsed and renamed to 'observed_at' (UTC)
    - duplicate rows removed
    - rows with unparsable timestamps removed
    """
    result = ValidationResult()
    result.total_rows = len(df)

    logger.info(
        "validation_start",
        source=source_name,
        rows=result.total_rows,
    )

    # ── 1. Required columns ───────────────────────────────────────────────
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        result.add_issue(f"Missing required columns: {missing_cols}")
        return df, result

    # ── 2. Timestamp parsing ──────────────────────────────────────────────
    try:
        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
        bad_ts = df[timestamp_col].isna().sum()
        if bad_ts > 0:
            result.timestamp_errors = int(bad_ts)
            result.add_warning(f"{bad_ts} rows have unparsable timestamps and will be dropped.")
            df = df.dropna(subset=[timestamp_col])

        # Rename to canonical column name
        if timestamp_col != "observed_at":
            df = df.rename(columns={timestamp_col: "observed_at"})

        df = df.sort_values("observed_at").reset_index(drop=True)
    except Exception as exc:
        result.add_issue(f"Timestamp parsing failed: {exc}")
        return df, result

    # ── 3. Duplicate detection ────────────────────────────────────────────
    dup_mask = df.duplicated(subset=["observed_at"], keep="first")
    dup_count = int(dup_mask.sum())
    result.duplicate_rows = dup_count
    if dup_count > 0:
        msg = f"{dup_count} duplicate timestamps found."
        if allow_duplicates:
            result.add_warning(msg + " Keeping first occurrence.")
        else:
            result.add_warning(msg + " Removing duplicates.")
        df = df[~dup_mask].reset_index(drop=True)

    # ── 4. Missing value analysis ─────────────────────────────────────────
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing > 0:
            result.missing_by_column[col] = missing
            pct = missing / len(df) * 100
            if pct > 50:
                result.add_warning(
                    f"Column '{col}' is {pct:.1f}% missing — consider excluding."
                )

    # ── 5. Numeric range checks ───────────────────────────────────────────
    out_of_range_total = 0
    for col, (lo, hi) in RANGE_RULES.items():
        if col not in df.columns:
            continue
        mask = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        n = int(mask.sum())
        if n > 0:
            out_of_range_total += n
            result.add_warning(
                f"Column '{col}': {n} values outside [{lo}, {hi}]. "
                "These are flagged but NOT removed automatically."
            )
    result.out_of_range_rows = out_of_range_total

    # ── 6. Time-gap detection ─────────────────────────────────────────────
    if expected_interval and len(df) > 1:
        expected_min = EXPECTED_INTERVAL_MINUTES.get(expected_interval, 60)
        expected_delta = pd.Timedelta(minutes=expected_min)
        diffs = df["observed_at"].diff().dropna()
        gaps = diffs[diffs > expected_delta * 1.5]
        result.time_gap_count = len(gaps)
        if len(gaps) > 0:
            result.add_warning(
                f"{len(gaps)} time gaps larger than 1.5× expected interval detected."
            )

    logger.info(
        "validation_complete",
        source=source_name,
        rows_after=len(df),
        issues=len(result.issues),
        warnings=len(result.warnings),
    )

    return df, result
