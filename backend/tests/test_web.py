"""Serving the built website at /app/ from the same server."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client(tmp_path: Path, with_index: bool = True) -> TestClient:
    if with_index:
        (tmp_path / "index.html").write_text("<!doctype html><title>Muse</title>")
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "app.js").write_text("console.log('muse')")
    settings = Settings(_env_file=None, app_env="test", frontend_dist=str(tmp_path))
    return TestClient(create_app(settings))


def test_website_is_served_at_app(tmp_path: Path) -> None:
    client = _client(tmp_path)

    page = client.get("/app/")
    script = client.get("/app/assets/app.js")

    assert page.status_code == 200
    assert "<title>Muse</title>" in page.text
    assert script.status_code == 200


def test_website_gets_its_own_content_security_policy(tmp_path: Path) -> None:
    client = _client(tmp_path)

    web = client.get("/app/").headers["Content-Security-Policy"]
    api = client.get("/api/v1/curate/options").headers["Content-Security-Policy"]

    assert "script-src 'self'" in web
    assert "connect-src 'self'" in web
    assert "frame-ancestors 'none'" in web
    assert api == "default-src 'none'; frame-ancestors 'none'"


def test_api_and_service_info_still_work_next_to_the_website(tmp_path: Path) -> None:
    client = _client(tmp_path)

    assert client.get("/").json()["name"] == "Muse API"
    assert client.get("/health").status_code == 200


def test_no_website_without_a_built_folder(tmp_path: Path) -> None:
    client = _client(tmp_path, with_index=False)

    assert client.get("/app/").status_code == 404
