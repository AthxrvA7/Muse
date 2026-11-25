"""MongoDB connection lifecycle and readiness, without a real database.

A fake database stands in for MongoDB: only ``command("ping")`` is needed here.
Repository tests against a real MongoDB come with the repositories.
"""

import json

import pytest
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import Settings
from app.db.mongo import create_client
from app.main import create_app

FAKE_URI = "mongodb://muse:not-a-real-password@localhost:27017"


class FakeDatabase:
    def __init__(self, *, reachable: bool) -> None:
        self.reachable = reachable
        self.commands: list[str] = []

    async def command(self, name: str) -> dict[str, float]:
        self.commands.append(name)
        if not self.reachable:
            raise ServerSelectionTimeoutError("no servers found")
        return {"ok": 1.0}


def _client_with(database: FakeDatabase, settings: Settings) -> TestClient:
    app = create_app(settings)
    app.state.db = database
    return TestClient(app)


def test_ready_when_database_answers(settings: Settings) -> None:
    database = FakeDatabase(reachable=True)

    response = _client_with(database, settings).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"app": "ok", "database": "ok"}}
    assert database.commands == ["ping"]


def test_not_ready_when_database_is_down(settings: Settings) -> None:
    response = _client_with(FakeDatabase(reachable=False), settings).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"app": "ok", "database": "unavailable"},
    }


def test_failed_ping_is_logged_without_details(
    settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    _client_with(FakeDatabase(reachable=False), settings).get("/ready")

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    warning = next(line for line in lines if line["message"] == "MongoDB ping failed")
    assert warning["level"] == "WARNING"
    assert warning["error_type"] == "ServerSelectionTimeoutError"
    assert all("no servers found" not in json.dumps(line) for line in lines)


def test_client_is_built_from_settings_without_connecting() -> None:
    settings = Settings(_env_file=None, mongodb_uri=FAKE_URI, mongodb_timeout_ms=1500)

    client = create_client(settings)

    assert isinstance(client, AsyncMongoClient)
    assert client.options.server_selection_timeout == 1.5
    assert client.codec_options.tz_aware is True


def test_create_client_requires_a_uri(settings: Settings) -> None:
    with pytest.raises(RuntimeError):
        create_client(settings)


def test_lifespan_opens_and_closes_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None, app_env="test", mongodb_uri=FAKE_URI, mongodb_db="muse_test"
    )
    app = create_app(settings)
    ensured: list[str] = []

    async def fake_ensure_indexes(database: object) -> None:
        ensured.append(database.name)  # type: ignore[attr-defined]

    monkeypatch.setattr("app.main.ensure_indexes", fake_ensure_indexes)

    with TestClient(app):
        assert app.state.db is not None
        assert app.state.db.name == "muse_test"
        assert ensured == ["muse_test"]

    assert app.state.db is None


def test_no_database_is_opened_when_not_configured(settings: Settings) -> None:
    app = create_app(settings)

    with TestClient(app):
        assert app.state.db is None


def test_app_starts_even_if_indexes_cannot_be_created(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = Settings(_env_file=None, app_env="test", mongodb_uri=FAKE_URI)
    app = create_app(settings)

    async def failing_ensure_indexes(database: object) -> None:
        raise ServerSelectionTimeoutError("no servers found")

    monkeypatch.setattr("app.main.ensure_indexes", failing_ensure_indexes)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    warning = next(line for line in lines if line["message"] == "Could not ensure MongoDB indexes")
    assert warning["error_type"] == "ServerSelectionTimeoutError"


def test_database_errors_in_a_request_become_a_clean_503(settings: Settings) -> None:
    from app.api.deps import current_user, get_preferences_repository
    from tests.test_preferences import USER

    class BrokenPreferences:
        async def get(self, user_id: str) -> None:
            raise ServerSelectionTimeoutError("SSL handshake failed: secret-host:27017")

    app = create_app(settings)
    app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_preferences_repository] = lambda: BrokenPreferences()

    response = TestClient(app).get("/api/v1/preferences")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"message": "The database is unavailable right now; try again shortly"}
    }
    assert "secret-host" not in response.text
