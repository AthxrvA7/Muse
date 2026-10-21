"""Response models for health and readiness checks."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Liveness: the process is running and can answer requests."""

    status: Literal["ok"] = "ok"


class ReadinessStatus(BaseModel):
    """Readiness: the app and everything it depends on can serve traffic."""

    status: Literal["ready", "degraded", "not_ready"]
    checks: dict[str, str] = Field(examples=[{"app": "ok"}])
