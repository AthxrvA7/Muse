"""Tests for request IDs and the access log."""

import logging
import re

import pytest
from fastapi.testclient import TestClient

HEX_ID = re.compile(r"^[0-9a-f]{32}$")


def test_every_response_gets_a_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert HEX_ID.match(response.headers["X-Request-ID"])


def test_each_request_gets_a_different_id(client: TestClient) -> None:
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]

    assert first != second


def test_valid_incoming_request_id_is_reused(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "trace-123.abc"})

    assert response.headers["X-Request-ID"] == "trace-123.abc"


@pytest.mark.parametrize(
    "bad_id",
    ["a" * 65, "id with spaces", 'evil"},{"level":"ERROR', "<script>"],
)
def test_unsafe_incoming_request_id_is_replaced(client: TestClient, bad_id: str) -> None:
    response = client.get("/health", headers={"X-Request-ID": bad_id})

    assert response.headers["X-Request-ID"] != bad_id
    assert HEX_ID.match(response.headers["X-Request-ID"])


def test_access_log_records_request_without_query_string(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="muse.access"):
        response = client.get("/health?code=secret-oauth-code")

    record = next(r for r in caplog.records if r.name == "muse.access")
    assert record.method == "GET"  # type: ignore[attr-defined]
    assert record.path == "/health"  # type: ignore[attr-defined]
    assert record.status_code == 200  # type: ignore[attr-defined]
    assert "secret-oauth-code" not in caplog.text
    assert response.headers["X-Request-ID"]
