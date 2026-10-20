"""Settings validation tests: bad configuration must fail fast."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.api_v1_prefix == "/api/v1"


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DOCS_ENABLED", "false")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.docs_enabled is False


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")


def test_debug_logging_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="DEBUG is not allowed"):
        Settings(_env_file=None, app_env="production", log_level="DEBUG")
