"""Tests for JSON log formatting and redaction of sensitive data."""

import json
import logging

from app.core.logging import (
    REDACTED,
    JsonFormatter,
    RedactingFilter,
    redact_text,
    request_id_var,
)


def _record(msg: str, **extra: object) -> logging.LogRecord:
    return logging.makeLogRecord(
        {"name": "muse.test", "levelname": "INFO", "levelno": logging.INFO, "msg": msg, **extra}
    )


def _format(record: logging.LogRecord) -> dict[str, object]:
    RedactingFilter().filter(record)
    result: dict[str, object] = json.loads(JsonFormatter().format(record))
    return result


def test_log_line_is_valid_json_with_standard_fields() -> None:
    line = _format(_record("hello"))

    assert line["message"] == "hello"
    assert line["level"] == "INFO"
    assert line["logger"] == "muse.test"
    assert "time" in line


def test_log_line_includes_current_request_id() -> None:
    token = request_id_var.set("req-42")
    try:
        line = _format(_record("inside a request"))
    finally:
        request_id_var.reset(token)

    assert line["request_id"] == "req-42"


def test_extra_fields_are_included() -> None:
    line = _format(_record("done", path="/health", status_code=200))

    assert line["path"] == "/health"
    assert line["status_code"] == 200


def test_sensitive_extra_fields_are_redacted() -> None:
    # Fake values on purpose: this test checks they are masked
    fake_secrets = {"access_token": "tok_123", "refresh_token": "ref_456"}
    line = _format(_record("login", mood_text="feeling low", **fake_secrets))

    assert line["access_token"] == REDACTED
    assert line["refresh_token"] == REDACTED
    assert line["mood_text"] == REDACTED
    assert "tok_123" not in json.dumps(line)


def test_bearer_tokens_in_messages_are_redacted() -> None:
    assert redact_text("Authorization: Bearer abc.def-ghi") == f"Authorization: Bearer {REDACTED}"


def test_secret_query_parameters_in_messages_are_redacted() -> None:
    text = redact_text("GET /callback?code=abc123&state=xyz")

    assert "abc123" not in text
    assert "state=xyz" in text


def test_message_arguments_are_redacted_after_formatting() -> None:
    record = _record("calling %s", args=("https://x.test/?access_token=secret",))

    assert "secret" not in str(_format(record)["message"])
