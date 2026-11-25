"""Spotify login, sessions and the logged-in user (fake Spotify, in-memory storage)."""

import time
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.clients.spotify import TOKEN_URL
from app.clients.spotify_user import SpotifyUserAuth, SpotifyUserClient
from app.core.config import Settings
from app.core.crypto import TokenCipher, generate_key
from app.main import create_app
from app.services.auth import SESSION_COOKIE, AuthService, NotLoggedInError, hash_session_id
from tests.fakes import FakeSessions, FakeStates, FakeUsers


class FakeSpotifyAccounts:
    """Answers the token endpoint and /me like Spotify."""

    def __init__(self) -> None:
        self.me_status = 200
        self.token_requests: list[dict[str, list[str]]] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            form = parse_qs(request.content.decode())
            self.token_requests.append(form)
            if form.get("code") == ["bad-code"]:
                return httpx2.Response(400, json={"error": "invalid_grant"})
            number = len(self.token_requests)
            return httpx2.Response(
                200,
                json={
                    "access_token": f"access-{number}",
                    "refresh_token": "refresh-1",
                    "expires_in": 3600,
                    "scope": "playlist-modify-private",
                },
            )
        if request.url.path == "/v1/me":
            if self.me_status != 200:
                return httpx2.Response(self.me_status, json={})
            return httpx2.Response(200, json={"id": "spotify-ath", "display_name": "Ath"})
        return httpx2.Response(404, json={})


class World:
    def __init__(self) -> None:
        self.users, self.sessions, self.states = FakeUsers(), FakeSessions(), FakeStates()
        self.spotify = FakeSpotifyAccounts()
        http = httpx2.AsyncClient(transport=httpx2.MockTransport(self.spotify))
        self.cipher = TokenCipher(generate_key())
        self.service = AuthService(
            users=self.users,  # type: ignore[arg-type]
            sessions=self.sessions,  # type: ignore[arg-type]
            states=self.states,  # type: ignore[arg-type]
            cipher=self.cipher,
            spotify_auth=SpotifyUserAuth(http, "client-id", "client-secret"),
            profile_reader=lambda token: SpotifyUserClient(http, token),
            client_id="client-id",
            redirect_uri="http://testserver/api/v1/auth/callback",
        )
        app = create_app(Settings(_env_file=None, app_env="test"))
        app.dependency_overrides[get_auth_service] = lambda: self.service
        self.client = TestClient(app, follow_redirects=False)

    def start_login(self) -> str:
        response = self.client.get("/api/v1/auth/login")
        assert response.status_code == 302
        return parse_qs(urlparse(response.headers["location"]).query)["state"][0]

    def log_in(self) -> httpx2.Response:
        state = self.start_login()
        return self.client.get(f"/api/v1/auth/callback?code=good-code&state={state}")


@pytest.fixture
def world() -> World:
    return World()


def test_login_sends_the_browser_to_spotify_with_a_stored_state(world: World) -> None:
    state = world.start_login()

    assert state in world.states.created
    assert len(state) >= 40


def test_successful_login_sets_a_safe_session_cookie_and_redirects(world: World) -> None:
    response = world.log_in()

    assert response.status_code == 302
    assert response.headers["location"] == "/docs"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    assert "Max-Age=604800" in cookie


def test_only_the_hash_of_the_session_id_is_stored(world: World) -> None:
    world.log_in()
    session_id = world.client.cookies[SESSION_COOKIE]

    assert session_id not in world.sessions.by_hash
    assert hash_session_id(session_id) in world.sessions.by_hash


def test_tokens_are_stored_encrypted(world: World) -> None:
    world.log_in()
    stored = world.users.tokens["user-1"]

    assert "access-1" not in str(stored)
    assert "refresh-1" not in str(stored)
    assert world.cipher.decrypt(stored["refresh_token"]) == "refresh-1"


def test_me_returns_the_logged_in_user(world: World) -> None:
    world.log_in()

    response = world.client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json()["spotify_id"] == "spotify-ath"
    assert response.json()["display_name"] == "Ath"
    assert "tokens" not in response.json()


def test_me_without_a_session_is_401(world: World) -> None:
    response = world.client.get("/api/v1/me")

    assert response.status_code == 401
    assert "/api/v1/auth/login" in response.json()["detail"]["message"]


def test_logout_ends_the_session_immediately(world: World) -> None:
    world.log_in()

    assert world.client.post("/api/v1/auth/logout").status_code == 204
    assert world.sessions.by_hash == {}
    assert world.client.get("/api/v1/me").status_code == 401


def test_a_state_can_be_used_only_once(world: World) -> None:
    state = world.start_login()
    world.client.get(f"/api/v1/auth/callback?code=good-code&state={state}")

    replay = world.client.get(f"/api/v1/auth/callback?code=good-code&state={state}")

    assert replay.status_code == 400


def test_unknown_or_expired_states_are_rejected(world: World) -> None:
    world.states.created["old"] = datetime.now(UTC) - timedelta(minutes=11)

    for state in ("never-issued", "old"):
        response = world.client.get(f"/api/v1/auth/callback?code=good-code&state={state}")
        assert response.status_code == 400
    assert world.users.by_id == {}


def test_cancelled_login_is_400(world: World) -> None:
    state = world.start_login()

    response = world.client.get(f"/api/v1/auth/callback?error=access_denied&state={state}")

    assert response.status_code == 400


def test_rejected_code_is_401(world: World) -> None:
    state = world.start_login()

    response = world.client.get(f"/api/v1/auth/callback?code=bad-code&state={state}")

    assert response.status_code == 401


def test_account_not_on_the_development_list_gets_a_clear_403(world: World) -> None:
    world.spotify.me_status = 403

    response = world.log_in()

    assert response.status_code == 403
    assert "Users Management" in response.json()["detail"]["message"]


def test_logging_in_again_replaces_the_old_session(world: World) -> None:
    world.log_in()
    first = world.client.cookies[SESSION_COOKIE]

    world.log_in()

    assert world.client.cookies[SESSION_COOKIE] != first
    assert list(world.sessions.by_hash) == [hash_session_id(world.client.cookies[SESSION_COOKIE])]
    assert len(world.users.by_id) == 1


@pytest.mark.anyio
async def test_access_token_is_refreshed_when_it_is_about_to_expire(world: World) -> None:
    world.log_in()
    world.users.tokens["user-1"]["expires_at"] = time.time() + 10  # expires in 10 s

    token = await world.service.access_token("user-1")

    assert token == "access-2"
    assert world.spotify.token_requests[-1]["grant_type"] == ["refresh_token"]
    assert world.cipher.decrypt(world.users.tokens["user-1"]["access_token"]) == "access-2"


@pytest.mark.anyio
async def test_fresh_access_token_is_used_as_is(world: World) -> None:
    world.log_in()

    assert await world.service.access_token("user-1") == "access-1"
    assert len(world.spotify.token_requests) == 1


@pytest.mark.anyio
async def test_unreadable_tokens_mean_log_in_again(world: World) -> None:
    world.log_in()
    world.users.tokens["user-1"]["refresh_token"] = "garbage"

    with pytest.raises(NotLoggedInError):
        await world.service.access_token("user-1")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_login_answers_503_when_not_configured(client: TestClient) -> None:
    response = client.get("/api/v1/auth/login", follow_redirects=False)

    assert response.status_code == 503
    assert "TOKEN_ENCRYPTION_KEY" in response.json()["detail"]["message"]
