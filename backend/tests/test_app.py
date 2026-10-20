"""Startup and wiring tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings
from app.main import create_app


def test_root_returns_service_information(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Muse API",
        "version": __version__,
        "environment": "test",
    }


def test_openapi_schema_is_served_when_docs_enabled(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Muse API"
    assert "ServiceInfo" in schema["components"]["schemas"]


def test_docs_are_hidden_when_disabled() -> None:
    settings = Settings(_env_file=None, app_env="test", docs_enabled=False)
    client = TestClient(create_app(settings))

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_unknown_route_returns_404(client: TestClient) -> None:
    assert client.get("/does-not-exist").status_code == 404
