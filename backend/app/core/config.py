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

from cryptography.fernet import Fernet
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

    # Spotify login (Authorization Code flow). The redirect URI must also be listed in the
    # Spotify dashboard, character for character. Spotify rejects "localhost": use 127.0.0.1.
    spotify_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/callback"
    # Where the browser goes after logging in (no frontend yet, so Swagger)
    post_login_redirect: str = "/docs"
    # Fernet key that encrypts stored Spotify tokens; generate one (see README). Never commit.
    token_encryption_key: SecretStr | None = None

    # Last.fm API key (free: https://www.last.fm/api/account/create). Gives each song a
    # mood from listener tags, and similar artists. Optional: without it Muse estimates.
    lastfm_api_key: SecretStr | None = None

    # Folder with the built website (frontend/dist). When set, it is served at /app/ from
    # this same server, so the browser talks to one origin and the login cookie just works.
    frontend_dist: str | None = None

    # Browser origins allowed to call the API (the React frontend), comma-separated,
    # e.g. "http://localhost:5173". Empty = no cross-origin browser access at all.
    cors_origins: str = ""

    # Requests per minute from one IP address. Curate is stricter because each call makes
    # about 20 Spotify requests; auth is stricter to slow down abuse of the login flow.
    rate_limit_per_minute: int = Field(default=120, ge=1)
    rate_limit_curate_per_minute: int = Field(default=10, ge=1)
    rate_limit_auth_per_minute: int = Field(default=10, ge=1)

    @field_validator(
        "spotify_client_id",
        "spotify_client_secret",
        "mongodb_uri",
        "token_encryption_key",
        "frontend_dist",
        "lastfm_api_key",
        mode="before",
    )
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # "SPOTIFY_CLIENT_ID=" in .env means "not configured", not an empty ID
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def lastfm_configured(self) -> bool:
        return self.lastfm_api_key is not None

    @property
    def login_configured(self) -> bool:
        """Login needs Spotify credentials, a database and an encryption key."""
        return (
            self.spotify_configured
            and self.mongodb_configured
            and self.token_encryption_key is not None
        )

    @field_validator("token_encryption_key")
    @classmethod
    def _check_encryption_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            try:
                Fernet(value.get_secret_value().encode())
            except ValueError:
                raise ValueError(
                    "TOKEN_ENCRYPTION_KEY must be a Fernet key (see README: Spotify login)"
                ) from None
        return value

    @field_validator("post_login_redirect")
    @classmethod
    def _check_post_login_redirect(cls, value: str) -> str:
        # Only a path on this server: an absolute URL here would be an open redirect
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("POST_LOGIN_REDIRECT must be a path such as /docs")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @field_validator("cors_origins")
    @classmethod
    def _check_origins(cls, value: str) -> str:
        for origin in (part.strip() for part in value.split(",") if part.strip()):
            if origin == "*" or not origin.startswith(("http://", "https://")):
                # A wildcard would let any website call the API from a user's browser
                raise ValueError("CORS_ORIGINS must list full origins like https://app.example.com")
        return value

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
