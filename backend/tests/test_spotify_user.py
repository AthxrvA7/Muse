"""Spotify calls on behalf of a logged-in user (no real network)."""

import json
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest

from app.clients.spotify import TOKEN_URL, SpotifyRateLimitError
from app.clients.spotify_user import (
    ALLOWED_USER_CALLS,
    SCOPES,
    ForbiddenCallError,
    SpotifyForbiddenError,
    SpotifyLoginError,
    SpotifyUserAuth,
    SpotifyUserClient,
    authorize_url,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class Recorder:
    def __init__(self, *responses: httpx2.Response) -> None:
        self.responses = list(responses)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.responses.pop(0)


def _http(recorder: Recorder) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(recorder))


def test_authorize_url_asks_only_for_the_needed_scopes() -> None:
    url = urlparse(authorize_url("client-id", "http://127.0.0.1:8000/cb", "state-123"))
    query = parse_qs(url.query)

    assert url.netloc == "accounts.spotify.com"
    assert query["response_type"] == ["code"]
    assert query["state"] == ["state-123"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8000/cb"]
    assert query["scope"] == [" ".join(SCOPES)]


async def test_code_is_exchanged_for_tokens() -> None:
    recorder = Recorder(
        httpx2.Response(
            200,
            json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600, "scope": "x"},
        )
    )

    tokens = await SpotifyUserAuth(_http(recorder), "id", "secret").exchange_code("code-1", "cb")

    assert (tokens.access_token, tokens.refresh_token) == ("a1", "r1")
    assert tokens.expires_soon() is False
    sent = parse_qs(recorder.requests[0].content.decode())
    assert str(recorder.requests[0].url) == TOKEN_URL
    assert sent == {
        "grant_type": ["authorization_code"],
        "code": ["code-1"],
        "redirect_uri": ["cb"],
    }


async def test_refresh_keeps_the_old_refresh_token_if_spotify_sends_none() -> None:
    recorder = Recorder(httpx2.Response(200, json={"access_token": "a2", "expires_in": 3600}))

    tokens = await SpotifyUserAuth(_http(recorder), "id", "secret").refresh("r1")

    assert (tokens.access_token, tokens.refresh_token) == ("a2", "r1")


async def test_rejected_code_is_a_login_error() -> None:
    recorder = Recorder(httpx2.Response(400, json={"error": "invalid_grant"}))

    with pytest.raises(SpotifyLoginError):
        await SpotifyUserAuth(_http(recorder), "id", "secret").exchange_code("used", "cb")


async def test_profile_is_read_with_the_users_token() -> None:
    recorder = Recorder(httpx2.Response(200, json={"id": "spotify-1", "display_name": "Ath"}))

    profile = await SpotifyUserClient(_http(recorder), "user-token").me()

    assert (profile.id, profile.display_name) == ("spotify-1", "Ath")
    assert recorder.requests[0].headers["Authorization"] == "Bearer user-token"


async def test_playlist_is_created_private_then_filled_in_batches_of_100() -> None:
    recorder = Recorder(
        httpx2.Response(
            201,
            json={
                "id": "pl1",
                "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"},
            },
        ),
        httpx2.Response(201, json={"snapshot_id": "s1"}),
        httpx2.Response(201, json={"snapshot_id": "s2"}),
    )
    client = SpotifyUserClient(_http(recorder), "user-token")

    playlist = await client.create_playlist("Muse: calm", "Made by Muse")
    await client.add_tracks(playlist.id, [f"t{i}" for i in range(150)])

    create, first, second = recorder.requests
    assert create.url.path == "/v1/me/playlists"
    assert json.loads(create.content) == {
        "name": "Muse: calm",
        "description": "Made by Muse",
        "public": False,
    }
    assert first.url.path == "/v1/playlists/pl1/items"
    assert len(json.loads(first.content)["uris"]) == 100
    assert json.loads(second.content)["uris"][-1] == "spotify:track:t149"
    assert playlist.url == "https://open.spotify.com/playlist/pl1"


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, SpotifyLoginError), (403, SpotifyForbiddenError), (429, SpotifyRateLimitError)],
)
async def test_user_request_errors_are_typed(status: int, error: type[Exception]) -> None:
    recorder = Recorder(httpx2.Response(status, headers={"Retry-After": "30"}, json={}))

    with pytest.raises(error):
        await SpotifyUserClient(_http(recorder), "user-token").me()


async def test_a_failed_write_is_never_repeated() -> None:
    recorder = Recorder(httpx2.Response(502, json={}), httpx2.Response(201, json={"id": "x"}))

    with pytest.raises(Exception, match="502"):
        await SpotifyUserClient(_http(recorder), "user-token").create_playlist("n", "d")
    assert len(recorder.requests) == 1


# ---------------------------------------------------------------- safety guard


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", "/me/library"),
        ("DELETE", "/playlists/pl1/items"),
        ("PUT", "/playlists/pl1/items"),
        ("PUT", "/playlists/pl1"),
        ("GET", "/playlists/pl1/items"),
        ("GET", "/me/playlists"),
        ("GET", "/me/top/tracks"),
        ("GET", "/me/player/recently-played"),
        ("POST", "/me/library"),
    ],
)
async def test_any_call_that_could_change_or_read_existing_music_is_refused(
    method: str, path: str
) -> None:
    recorder = Recorder()

    with pytest.raises(ForbiddenCallError):
        await SpotifyUserClient(_http(recorder), "user-token")._request(method, path)  # noqa: SLF001
    assert recorder.requests == []  # refused before anything was sent


async def test_tracks_can_only_be_added_to_a_playlist_muse_just_created() -> None:
    recorder = Recorder()

    with pytest.raises(ForbiddenCallError):
        await SpotifyUserClient(_http(recorder), "user-token").add_tracks(
            "users-old-playlist", ["t1"]
        )
    assert recorder.requests == []


def test_only_four_kinds_of_user_call_exist() -> None:
    assert [(m, p.pattern) for m, p in ALLOWED_USER_CALLS] == [
        ("GET", "^/me$"),
        ("GET", "^/me/top/artists$"),
        ("POST", "^/me/playlists$"),
        ("POST", "^/playlists/[A-Za-z0-9]+/items$"),
    ]


async def test_top_artists_are_read_with_the_users_token() -> None:
    recorder = Recorder(
        httpx2.Response(
            200,
            json={
                "items": [
                    {"name": "Arijit Singh", "genres": ["filmi", "modern bollywood"]},
                    {"name": "Taylor Swift"},  # Development Mode often omits genres
                ]
            },
        )
    )

    artists = await SpotifyUserClient(_http(recorder), "user-token").top_artists(limit=10)

    assert [(a.name, a.genres) for a in artists] == [
        ("Arijit Singh", ["filmi", "modern bollywood"]),
        ("Taylor Swift", []),
    ]
    (request,) = recorder.requests
    assert request.method == "GET"
    assert request.url.path == "/v1/me/top/artists"
    assert request.url.params["limit"] == "10"
    assert request.url.params["time_range"] == "medium_term"
    assert request.headers["Authorization"] == "Bearer user-token"
