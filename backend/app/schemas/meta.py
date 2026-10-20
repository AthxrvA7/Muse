"""Response models for service metadata endpoints."""

from pydantic import BaseModel, Field

from app.core.config import Environment


class ServiceInfo(BaseModel):
    """Basic information about the running Muse API."""

    name: str = Field(examples=["Muse API"])
    version: str = Field(examples=["0.1.0"])
    environment: Environment = Field(examples=["local"])
