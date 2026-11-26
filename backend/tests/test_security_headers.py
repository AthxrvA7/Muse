"""Security headers and CORS."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app

FRONTEND = "http://localhost:5173"


def _client(**overrides: object) -> TestClient:
    settings = Settings(_env_file=None, app_env="test", **overrides)
    return TestClient(create_app(settings))


def test_every_response_has_the_basic_headers(client: TestClient) -> None:
    for path in ("/", "/health", "/api/v1/curate/options", "/does-not-exist"):
        headers = client.get(path).headers

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"


def test_api_responses_forbid_loading_anything_and_caching(client: TestClient) -> None:
    headers = client.get("/api/v1/curate/options").headers

    assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert headers["Cache-Control"] == "no-store"


def test_swagger_docs_still_work_without_the_strict_policy(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_hsts_only_in_production() -> None:
    assert "Strict-Transport-Security" not in _client().get("/health").headers

    production = Settings(
        _env_file=None,
        app_env="production",
        docs_enabled=False,
        mongodb_uri="mongodb://localhost:27017",
    )
    headers = TestClient(create_app(production)).get("/health").headers
    assert headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_no_cross_origin_access_by_default(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": FRONTEND})

    assert "Access-Control-Allow-Origin" not in response.headers


def test_listed_frontend_may_call_the_api_with_cookies() -> None:
    client = _client(cors_origins=FRONTEND)

    response = client.options(
        "/api/v1/curate",
        headers={"Origin": FRONTEND, "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_other_websites_are_not_allowed() -> None:
    client = _client(cors_origins=FRONTEND)

    response = client.options(
        "/api/v1/curate",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize("value", ["*", "localhost:5173", "http://ok.example, *"])
def test_wildcards_and_bare_hosts_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, cors_origins=value)


def test_origins_are_parsed_and_normalised() -> None:
    settings = Settings(
        _env_file=None, cors_origins=" http://localhost:5173/ , https://muse.example "
    )

    assert settings.allowed_origins == ["http://localhost:5173", "https://muse.example"]


def test_huge_request_bodies_are_refused_before_they_are_read() -> None:
    from app.core.security import MAX_BODY_BYTES

    client = TestClient(create_app(Settings(_env_file=None)))
    url = "/api/v1/rooms/ABCD/votes"
    big = b'{"voter": "phone-0001", "chips": ["' + b"a" * (MAX_BODY_BYTES + 10) + b'"]}'
    declared = client.post(url, content=big, headers={"content-type": "application/json"})
    assert declared.status_code == 413
    assert declared.headers["X-Content-Type-Options"] == "nosniff"

    def chunks():  # no Content-Length: counted while it streams in
        for _ in range(100):
            yield b"x" * 1024

    streamed = client.post(url, content=chunks(), headers={"content-type": "application/json"})
    assert streamed.status_code == 413
    assert (
        client.post(url, content=b"{}", headers={"content-type": "application/json"}).status_code
        == 422
    )
