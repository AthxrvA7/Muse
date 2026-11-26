"""Rate limiting: per IP, per minute, stricter on expensive routes."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import FixedWindowRateLimiter
from app.main import create_app


class FakeClock:
    def __init__(self, now: float = 1_000_040.0) -> None:  # 20 s into a minute
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_requests_within_the_limit_are_allowed() -> None:
    limiter = FixedWindowRateLimiter(clock=FakeClock())

    assert [limiter.hit("ip-1", limit=3) for _ in range(3)] == [None, None, None]


def test_the_request_over_the_limit_gets_a_wait_time() -> None:
    limiter = FixedWindowRateLimiter(clock=FakeClock())
    for _ in range(3):
        limiter.hit("ip-1", limit=3)

    assert limiter.hit("ip-1", limit=3) == 40  # the window ends 40 s later


def test_a_new_minute_starts_from_zero() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(clock=clock)
    for _ in range(3):
        limiter.hit("ip-1", limit=3)

    clock.now += 60

    assert limiter.hit("ip-1", limit=3) is None


def test_each_client_has_its_own_budget() -> None:
    limiter = FixedWindowRateLimiter(clock=FakeClock())
    for _ in range(3):
        limiter.hit("ip-1", limit=3)

    assert limiter.hit("ip-2", limit=3) is None


def test_old_windows_are_cleared_when_the_table_is_full() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(clock=clock)
    limiter._MAX_KEYS = 3  # noqa: SLF001 - shrink the table for the test
    for ip in ("a", "b", "c"):
        limiter.hit(ip, limit=5)

    clock.now += 60
    limiter.hit("d", limit=5)

    assert set(limiter._counts) == {"d"}  # noqa: SLF001


def _client(**limits: int) -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, app_env="test", **limits)))


def test_api_answers_429_with_retry_after_when_over_the_limit() -> None:
    client = _client(rate_limit_per_minute=2)

    statuses = [client.get("/").status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
    response = client.get("/")
    assert response.json() == {"detail": {"message": "Too many requests; try again shortly"}}
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_curate_has_its_own_stricter_budget() -> None:
    client = _client(rate_limit_per_minute=100, rate_limit_curate_per_minute=1)

    client.get("/api/v1/curate/options")
    assert client.get("/api/v1/curate/options").status_code == 429
    assert client.get("/api/v1/catalog/search?q=x").status_code != 429


def test_health_checks_are_never_limited() -> None:
    client = _client(rate_limit_per_minute=1)

    statuses = {client.get(path).status_code for path in ("/health", "/ready") * 5}

    assert 429 not in statuses


def test_website_files_are_never_limited() -> None:
    # A whole class opening the site on one Wi-Fi shares one IP address
    client = _client(rate_limit_per_minute=1)

    statuses = {client.get(path).status_code for path in ("/app/", "/app/assets/x.js") * 5}

    assert 429 not in statuses
    client.get("/")
    assert client.get("/").status_code == 429  # the API itself still is


def test_cover_art_has_its_own_budget() -> None:
    client = _client(rate_limit_per_minute=100, rate_limit_covers_per_minute=1)
    url = "/api/v1/covers?valence=0.5&energy=0.5&title=Hi"
    assert client.get(url).status_code == 200
    assert client.get(url).status_code == 429
    assert client.get("/").status_code == 200
