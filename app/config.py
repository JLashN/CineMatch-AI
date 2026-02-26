"""
CineMatch AI — Application Settings

Design patterns:
  - Singleton: single Settings instance shared everywhere
  - Configuration Object: centralizes all env-based config
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── vLLM ──────────────────────────────────────────────
    vllm_base_url: str = "http://10.253.23.14:443/v1"
    vllm_model: str = "Qwen3-30B-A3B-Instruct"

    # ── TMDB ──────────────────────────────────────────────
    tmdb_api_read_token: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base: str = "https://image.tmdb.org/t/p/w500"

    # ── App ───────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    # ── External APIs (optional, free tiers) ──────────────
    omdb_api_key: Optional[str] = None       # https://www.omdbapi.com/apikey.aspx
    youtube_api_key: Optional[str] = None    # https://console.cloud.google.com/apis

    # ── Redis (optional) ──────────────────────────────────
    redis_url: Optional[str] = None

    # ── Derived helpers ───────────────────────────────────
    @property
    def tmdb_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.tmdb_api_read_token}",
            "Accept": "application/json",
        }


# Singleton – import this everywhere
settings = Settings()
