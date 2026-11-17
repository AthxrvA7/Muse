"""Health endpoints used by Docker, the hosting platform and monitoring.

They live outside /api/v1 because they describe the running service,
not the versioned API, and they never require a login.

- /health  (liveness)  -> "is the process alive?"  If not, restart it.
- /ready   (readiness) -> "can it serve users?"     If not, stop sending traffic.
"""

from fastapi import APIRouter, Request, Response, status

from app.schemas.health import HealthStatus, ReadinessStatus
from app.services.readiness import check_readiness

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health() -> HealthStatus:
    return HealthStatus()


@router.get("/ready", summary="Readiness check")
async def ready(request: Request, response: Response) -> ReadinessStatus:
    overall, checks = await check_readiness(request.app.state.db)
    if overall == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(status=overall, checks=checks)
