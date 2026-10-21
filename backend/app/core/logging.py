"""Structured JSON logging.

Every log line is one JSON object, so logs can be searched and filtered
(e.g. "all lines for request_id=abc123"). The request ID of the current
request is added automatically to every line.
"""

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Holds the ID of the request currently being handled ("-" outside a request)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Attributes every LogRecord has; anything else was passed via `extra=` and is logged too.
# uvicorn adds "color_message" (terminal colour codes), which is noise in JSON logs.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}


REDACTED = "[REDACTED]"

# Field names whose values must never appear in logs (compared in lowercase)
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "client_secret",
        "code",
        "session_id",
        "mood_text",
    }
)

# Secrets that can hide inside a message string
_SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(access_token|refresh_token|client_secret|code|password|token)=([^&\s]+)"),
]


def redact_text(text: str) -> str:
    """Mask bearer tokens and secret-looking query parameters inside free text."""
    text = _SECRET_PATTERNS[0].sub(rf"\1{REDACTED}", text)
    return _SECRET_PATTERNS[1].sub(rf"\1={REDACTED}", text)


class RedactingFilter(logging.Filter):
    """Removes secrets and private data from a log record before it is written.

    Defence in depth: code should never log secrets in the first place,
    but if someone does by mistake, this filter masks them.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = None
        for key in list(vars(record)):
            if key.lower() in SENSITIVE_KEYS:
                setattr(record, key, REDACTED)
        return True  # never drop the line, only clean it


class JsonFormatter(logging.Formatter):
    """Formats a log record as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Send all logs (ours and uvicorn's) to stdout as redacted JSON. Safe to call repeatedly."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Route uvicorn's own logs through our JSON handler
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    # Our middleware writes the access log, so silence uvicorn's duplicate one
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = []
    access_logger.propagate = False
