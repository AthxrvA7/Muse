"""Spotify client: token handling and failure handling (no real network)."""

from collections.abc import Callable

import httpx2
import pytest

from app.clients.spotify import (
    TOKEN_URL,
    SpotifyAuthError,
    SpotifyClient,
    SpotifyRateLimitError,
    SpotifyUnavailableError,
    TokenCache,
)

Handler = Callable[[httpx2.Request], httpx2.Response]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeSpotify:
    """Records requests and answers them like Spotify would."""

    def __init__(self, api_responses: list[httpx2.Response] | None = None) -> None:
        self.token_calls = 0
        self.api_calls: list[httpx2.Request] = []
        self.api_responses = api_responses or []
        self.token_status = 200

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            self.token_calls += 1
            if self.token_status != 200:
                return httpx2.Response(self.token_status, json={"error": "invalid_client"})
            return httpx2.Response(
                200, json={"access_token": f"token-{self.token_calls}", "expires_in": 3600}
            )
        self.api_calls.append(request)
        if self.api_responses:
            return self.api_responses.pop(0)
        return httpx2.Response(200, json={"ok": True})


def make_client(handler: Handler, cache: TokenCache | None = None) -> SpotifyClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return SpotifyClient(http, "client-id", "client-secret", "IN", cache or TokenCache())


@pytest.mark.anyio
async def test_token_is_fetched_once_and_reused() -> None:
    spotify = FakeSpotify()
    client = make_client(spotify)

    await client.get("/search", {})
    await client.get("/search", {})

    assert spotify.token_calls == 1
    assert spotify.api_calls[0].headers["Authorization"] == "Bearer token-1"


@pytest.mark.anyio
async def test_token_request_uses_basic_auth_and_client_credentials() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"access_token": "t", "expires_in": 3600})

    await make_client(handler)._token()

    assert seen[0].headers["Authorization"].startswith("Basic ")
    assert seen[0].content == b"grant_type=client_credentials"


@pytest.mark.anyio
async def test_expired_token_is_refreshed_once_on_401() -> None:
    spotify = FakeSpotify([httpx2.Response(401), httpx2.Response(200, json={"ok": 1})])

    assert await make_client(spotify).get("/search", {}) == {"ok": 1}
    assert spotify.token_calls == 2
    assert spotify.api_calls[1].headers["Authorization"] == "Bearer token-2"


@pytest.mark.anyio
async def test_rejected_credentials_raise_auth_error() -> None:
    spotify = FakeSpotify()
    spotify.token_status = 400

    with pytest.raises(SpotifyAuthError):
        await make_client(spotify).get("/search", {})


@pytest.mark.anyio
async def test_rate_limit_waits_retry_after_then_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("app.clients.spotify.asyncio.sleep", fake_sleep)
    spotify = FakeSpotify(
        [httpx2.Response(429, headers={"Retry-After": "2"}), httpx2.Response(200, json={"ok": 1})]
    )

    assert await make_client(spotify).get("/search", {}) == {"ok": 1}
    assert waits == [2]


@pytest.mark.anyio
async def test_long_rate_limit_is_reported_not_waited_out() -> None:
    spotify = FakeSpotify([httpx2.Response(429, headers={"Retry-After": "30"})])

    with pytest.raises(SpotifyRateLimitError) as error:
        await make_client(spotify).get("/search", {})
    assert error.value.retry_after == 30


@pytest.mark.anyio
async def test_one_server_error_is_retried() -> None:
    spotify = FakeSpotify([httpx2.Response(502), httpx2.Response(200, json={"ok": 1})])

    assert await make_client(spotify).get("/search", {}) == {"ok": 1}


@pytest.mark.anyio
async def test_repeated_server_errors_mean_unavailable() -> None:
    spotify = FakeSpotify([httpx2.Response(503), httpx2.Response(503)])

    with pytest.raises(SpotifyUnavailableError):
        await make_client(spotify).get("/search", {})


@pytest.mark.anyio
async def test_timeouts_mean_unavailable() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "t", "expires_in": 3600})
        raise httpx2.ReadTimeout("too slow", request=request)

    with pytest.raises(SpotifyUnavailableError):
        await make_client(handler).get("/search", {})
