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
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.docs_enabled is False


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")


def test_debug_logging_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="DEBUG is not allowed"):
        Settings(_env_file=None, app_env="production", log_level="DEBUG")


def test_spotify_is_optional_and_empty_values_mean_unset() -> None:
    settings = Settings(_env_file=None, spotify_client_id="", spotify_client_secret="  ")

    assert settings.spotify_configured is False


def test_spotify_secret_is_never_shown_in_repr() -> None:
    settings = Settings(_env_file=None, spotify_client_id="id", spotify_client_secret="s3cret")

    assert settings.spotify_configured is True
    assert "s3cret" not in repr(settings)


def test_market_must_be_a_two_letter_country_code() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, spotify_market="India")


def test_mongodb_is_optional_outside_production() -> None:
    settings = Settings(_env_file=None, mongodb_uri="")

    assert settings.mongodb_uri is None
    assert settings.mongodb_configured is False
    assert settings.mongodb_db == "muse"


def test_production_requires_mongodb() -> None:
    with pytest.raises(ValidationError, match="MONGODB_URI is required"):
        Settings(_env_file=None, app_env="production")


def test_mongodb_uri_is_hidden_and_checked() -> None:
    uri = "mongodb+srv://muse:s3cret-pass@cluster0.example.mongodb.net"
    settings = Settings(_env_file=None, mongodb_uri=uri)

    assert settings.mongodb_configured is True
    assert "s3cret-pass" not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, mongodb_uri="https://muse:s3cret-pass@example.com")
    assert "s3cret-pass" not in str(error.value)


def test_invalid_database_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mongodb_db="muse prod")


def test_encryption_key_must_be_a_valid_fernet_key() -> None:
    from app.core.crypto import generate_key

    key = generate_key()
    assert Settings(_env_file=None, token_encryption_key=key).token_encryption_key is not None
    with pytest.raises(ValidationError, match="TOKEN_ENCRYPTION_KEY") as error:
        Settings(_env_file=None, token_encryption_key="not-a-key-but-a-secret")
    assert "not-a-key-but-a-secret" not in str(error.value)


def test_login_needs_spotify_database_and_key() -> None:
    from app.core.crypto import generate_key

    partial = Settings(_env_file=None, spotify_client_id="id", spotify_client_secret="secret")
    full = partial.model_copy(
        update={
            "mongodb_uri": Settings(_env_file=None, mongodb_uri="mongodb://h").mongodb_uri,
            "token_encryption_key": Settings(
                _env_file=None, token_encryption_key=generate_key()
            ).token_encryption_key,
        }
    )

    assert partial.login_configured is False
    assert full.login_configured is True


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "docs"])
def test_post_login_redirect_must_stay_on_this_server(target: str) -> None:
    with pytest.raises(ValidationError, match="POST_LOGIN_REDIRECT"):
        Settings(_env_file=None, post_login_redirect=target)
