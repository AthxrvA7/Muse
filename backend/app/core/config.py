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

from pydantic import model_validator
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

    @model_validator(mode="after")
    def _check_production_rules(self) -> "Settings":
        if self.app_env == "production" and self.log_level == "DEBUG":
            raise ValueError("LOG_LEVEL=DEBUG is not allowed when APP_ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the settings, loaded once per process."""
    return Settings()
