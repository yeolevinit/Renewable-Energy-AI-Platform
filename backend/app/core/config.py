"""Central application configuration — loaded from environment variables / .env file."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    app_name: str = "Renewable Energy AI Platform"
    app_version: str = "1.0.0"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql://reai_user:reai_password@localhost:5432/renewable_energy_ai"
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Paths ─────────────────────────────────────────────────────────────────
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    model_artifact_dir: str = "./backend/app/ml/artifacts"

    @property
    def raw_data_path(self) -> Path:
        return Path(self.raw_data_dir)

    @property
    def processed_data_path(self) -> Path:
        return Path(self.processed_data_dir)

    @property
    def model_artifact_path(self) -> Path:
        p = Path(self.model_artifact_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── External APIs ─────────────────────────────────────────────────────────
    open_meteo_base_url: str = "https://archive-api.open-meteo.com/v1/archive"
    nrel_api_key: str = ""

    # ── ML defaults ──────────────────────────────────────────────────────────
    # Chronological split ratios (must sum to 1.0)
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    # remainder is test (0.15)

    random_seed: int = 42


@lru_cache()
def get_settings() -> Settings:
    return Settings()
