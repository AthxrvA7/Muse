"""Readiness checks: can this instance serve users right now?

Each dependency reports one of:
- "ok"              it works
- "not_configured"  it is optional here and not set up (local development, CI)
- "unavailable"     it is set up but not answering

Overall: any "unavailable" -> not_ready (HTTP 503, the platform stops sending traffic);
any "not_configured" -> degraded (HTTP 200, the app runs with fewer features);
otherwise ready.
"""

from typing import Literal

from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import ping

Overall = Literal["ready", "degraded", "not_ready"]


async def check_readiness(database: AsyncDatabase | None) -> tuple[Overall, dict[str, str]]:
    checks = {"app": "ok"}
    if database is None:
        checks["database"] = "not_configured"
    else:
        checks["database"] = "ok" if await ping(database) else "unavailable"

    if "unavailable" in checks.values():
        return "not_ready", checks
    if "not_configured" in checks.values():
        return "degraded", checks
    return "ready", checks
