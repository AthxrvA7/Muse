"""Application settings, read from environment variables (12-factor style).

Values come from, in order of priority:
1. real environment variables (Render, GitHub Actions, Docker),
2. a ``.env`` file in the repository root (local development only, git-ignored),
3. the defaults below.

Invalid values stop the app at startup instead of failing later at runtime.
Secrets are added here only when a feature needs them, and never get defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the repository root
_REPO_ROOT = Path(__file__).resolve().parents[3]

Environment = Literal["local", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Environment = "local"
    log_level: LogLevel = "INFO"
    docs_enabled: bool = True
    api_v1_prefix: str = "/api/v1"

    # Spotify developer app (client-credentials flow). Optional, so the app and CI run
    # without them; Spotify-backed endpoints answer 503 until they are set.
    spotify_client_id: str | None = None
    spotify_client_secret: SecretStr | None = None  # SecretStr: never printed in logs or reprs
    spotify_market: str = Field(default="IN", pattern=r"^[A-Z]{2}$")  # country for search
    spotify_timeout_seconds: float = Field(default=10.0, gt=0, le=30)

    @field_validator("spotify_client_id", "spotify_client_secret", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # "SPOTIFY_CLIENT_ID=" in .env means "not configured", not an empty ID
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @model_validator(mode="after")
    def _check_production_rules(self) -> "Settings":
        if self.app_env == "production" and self.log_level == "DEBUG":
            raise ValueError("LOG_LEVEL=DEBUG is not allowed when APP_ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the settings, loaded once per process."""
    return Settings()
