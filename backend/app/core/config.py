"""Configuration for Realtime Earth backend.

All settings are loaded from environment variables (12-factor). Defaults are
sane for a local docker-compose run. Override via `.env` (compose) or your
deployment platform.
"""

from __future__ import annotations

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="REALTIME_EARTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Logging
    log_level: str = "INFO"

    # HTTP client
    http_timeout_seconds: float = 30.0
    http_user_agent: str = "RealtimeEarth/0.1 (+https://github.com/realtime-earth)"

    # Per-source toggles
    enable_satellites: bool = True
    enable_lightning: bool = True
    enable_earthquakes: bool = True
    enable_wildfires: bool = True
    enable_volcanoes: bool = True
    enable_solar: bool = True

    # NASA FIRMS optional key
    firms_map_key: str = ""

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:8080",
            "http://localhost:5173",
        ]
    )

    # Cache directory (for TLE files, etc.)
    cache_dir: str = ".cache"

    # Polling cadences (seconds)
    satellite_poll_seconds: int = 1800  # TLE changes slowly
    lightning_poll_seconds: int = 10
    earthquake_poll_seconds: int = 60
    wildfire_poll_seconds: int = 1800  # NASA updates ~every 3-6h but feed is daily
    volcano_poll_seconds: int = 86400  # weekly
    solar_poll_seconds: int = 60

    # Data retention / limits
    max_lightning_strikes: int = 5000  # keep last N in memory
    max_earthquakes: int = 2000
    max_wildfires: int = 10000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
