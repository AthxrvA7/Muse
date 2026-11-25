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
        # Validation errors must never echo a value back: it may be a password or secret
        hide_input_in_errors=True,
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

    # MongoDB (Atlas in deployment). Optional locally and in CI, so the mood and curate
    # endpoints keep working without a database; required when APP_ENV=production.
    mongodb_uri: SecretStr | None = None  # holds the database password: never printed
    mongodb_db: str = Field(default="muse", pattern=r"^[A-Za-z0-9_-]{1,38}$")
    mongodb_timeout_ms: int = Field(default=5000, ge=500, le=30000)

    @field_validator("spotify_client_id", "spotify_client_secret", "mongodb_uri", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # "SPOTIFY_CLIENT_ID=" in .env means "not configured", not an empty ID
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def mongodb_configured(self) -> bool:
        return self.mongodb_uri is not None

    @field_validator("mongodb_uri")
    @classmethod
    def _check_mongodb_scheme(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith(
            ("mongodb://", "mongodb+srv://")
        ):
            # The message must not echo the value: it contains the password
            raise ValueError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        return value

    @model_validator(mode="after")
    def _check_production_rules(self) -> "Settings":
        if self.app_env == "production" and self.log_level == "DEBUG":
            raise ValueError("LOG_LEVEL=DEBUG is not allowed when APP_ENV=production")
        if self.app_env == "production" and not self.mongodb_configured:
            raise ValueError("MONGODB_URI is required when APP_ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the settings, loaded once per process."""
    return Settings()
