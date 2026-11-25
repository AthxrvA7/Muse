"""Origin check: other websites cannot make state-changing requests (CSRF)."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

FRONTEND = "http://localhost:5173"
MOOD = {"chips": ["calm"]}


def _client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, app_env="test", cors_origins=FRONTEND)))


def test_post_from_another_website_is_blocked() -> None:
    response = _client().post(
        "/api/v1/mood/analyze", json=MOOD, headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": {"message": "Requests from this website are not allowed"}}


def test_post_from_the_listed_frontend_is_allowed() -> None:
    response = _client().post("/api/v1/mood/analyze", json=MOOD, headers={"Origin": FRONTEND})

    assert response.status_code == 200


def test_post_from_muse_itself_is_allowed() -> None:
    # Swagger UI at /docs runs on the API's own origin (TestClient uses http://testserver)
    response = _client().post(
        "/api/v1/mood/analyze", json=MOOD, headers={"Origin": "http://testserver"}
    )

    assert response.status_code == 200


def test_requests_without_an_origin_are_allowed() -> None:
    # curl, Postman and tests send no Origin and carry no browser cookies
    assert _client().post("/api/v1/mood/analyze", json=MOOD).status_code == 200


def test_reads_are_never_blocked() -> None:
    response = _client().get("/api/v1/curate/options", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


def test_lookalike_origins_are_blocked() -> None:
    for origin in ("http://localhost:5173.evil.example", "https://localhost:5173", "null"):
        response = _client().post("/api/v1/mood/analyze", json=MOOD, headers={"Origin": origin})
        assert response.status_code == 403, origin
