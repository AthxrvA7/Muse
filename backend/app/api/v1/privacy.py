"""Your data: download everything Muse holds about you, or delete your account (FR11)."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, get_privacy_service
from app.services.auth import SESSION_COOKIE
from app.services.privacy import PrivacyService

router = APIRouter(prefix="/me", tags=["privacy"])
Service = Annotated[PrivacyService, Depends(get_privacy_service)]


@router.get("/data", summary="Download everything Muse holds about you (JSON)")
async def export_my_data(user: CurrentUser, service: Service) -> Response:
    body = json.dumps(await service.export(user), indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="muse-my-data.json"'},
    )


@router.delete("", summary="Delete your Muse account and all your data")
async def delete_my_account(user: CurrentUser, service: Service) -> Response:
    removed: dict[str, Any] = await service.delete_account(user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.headers["X-Deleted"] = ",".join(f"{k}={v}" for k, v in removed.items())
    return response
