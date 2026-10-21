"""Health endpoints used by Docker, the hosting platform and monitoring.

They live outside /api/v1 because they describe the running service,
not the versioned API, and they never require a login.

- /health  (liveness)  -> "is the process alive?"  If not, restart it.
- /ready   (readiness) -> "can it serve users?"     If not, stop sending traffic.
"""

from fastapi import APIRouter, Response, status

from app.schemas.health import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health() -> HealthStatus:
    return HealthStatus()


@router.get("/ready", summary="Readiness check")
def ready(response: Response) -> ReadinessStatus:
    # Each dependency adds its own check here as it is built (MongoDB in feature/database).
    checks = {"app": "ok"}

    if all(result == "ok" for result in checks.values()):
        return ReadinessStatus(status="ready", checks=checks)

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(status="not_ready", checks=checks)
