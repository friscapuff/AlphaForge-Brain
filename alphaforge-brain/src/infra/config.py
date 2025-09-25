from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment (.env optional).

    Add new configuration here; keep names stable for hashing reproducibility where relevant.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", case_sensitive=False
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # Paths
    data_dir: Path = Path("data")
    runs_dir: Path = Path("runs")
    cache_dir: Path = Path("cache")

    # Database
    sqlite_path: Path = Path("studio.db")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_root_path: str = ""

    # Security
    auth_token: str | None = None  # Static bearer token when set

    # SSE / streaming
    sse_heartbeat_interval_sec: float = 2.0
    sse_buffer_size: int = 256

    # Retention
    retention_max_completed: int = 100

    # Determinism
    canonical_float_precision: int = 12

    # Feature flags (future toggles)
    enable_validation: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
