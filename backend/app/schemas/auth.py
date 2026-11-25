"""Responses for login and the current user."""

from datetime import datetime

from pydantic import BaseModel


class Me(BaseModel):
    id: str
    spotify_id: str
    display_name: str | None
    created_at: datetime
    last_login_at: datetime
