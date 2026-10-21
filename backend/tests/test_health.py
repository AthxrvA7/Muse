"""Tests for the liveness and readiness endpoints."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_each_check(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"app": "ok"}}


def test_health_endpoints_are_not_under_versioned_api(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 404
