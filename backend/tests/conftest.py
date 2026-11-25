"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--db",
        action="store_true",
        default=False,
        help="also run the repository tests against the real MongoDB in MONGODB_URI (.env)",
    )


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: tests never read a developer's local .env
    return Settings(_env_file=None, app_env="test")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
