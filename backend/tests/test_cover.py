"""Cover art: painting it, uploading it to Muse's own new playlist, and the preview."""

import base64
import io

import httpx2
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import current_user, get_playlist_service
from app.core.config import Settings
from app.main import create_app
from app.services.cover import MAX_JPEG_BYTES, make_cover, mood_hue
from app.services.playlists import PlaylistService
from tests.fakes import FakePlaylists
from tests.test_playlists import USER

TRACKS = ["4uLU6hMCjMI75M1A2tKUQC", "0VjIjW4GlUZAMYd2vXMi3b"]
COVER = {
    "valence": 0.8,
    "energy": 0.7,
    "title": "Turn it up. You've earned it.",
    "words": ["confident"],
}


class Tokens:
    def __init__(self, scopes: set[str]) -> None:
        self.scopes = scopes

    async def access_token(self, user_id: str) -> str:
        return "user-token"

    async def granted_scopes(self, user_id: str) -> set[str]:
        return self.scopes


class Spotify:
    def __init__(self, image_status: int = 202) -> None:
        self.image_status = image_status
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if request.url.path == "/v1/me/playlists":
            return httpx2.Response(201, json={"id": "3cEYpjA9oz9GiPac4AsH4n"})
        if request.url.path.endswith("/images"):
            return httpx2.Response(self.image_status)
        return httpx2.Response(201, json={"snapshot_id": "s"})


def save(scopes: set[str], spotify: Spotify, body: dict) -> tuple[int, dict]:  # type: ignore[type-arg]
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(spotify))
    service = PlaylistService(Tokens(scopes), http, FakePlaylists())  # type: ignore[arg-type]
    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_playlist_service] = lambda: service
    response = TestClient(app).post("/api/v1/playlists", json=body)
    return response.status_code, response.json()


ALL = {"playlist-modify-private", "ugc-image-upload"}


def test_the_cover_is_a_small_square_jpeg() -> None:
    jpeg = make_cover(0.2, 0.9, "A very long headline that has to wrap onto lines", ["a", "b", "c"])

    image = Image.open(io.BytesIO(jpeg))
    assert image.format == "JPEG" and image.size == (640, 640)
    assert len(jpeg) <= MAX_JPEG_BYTES
    assert len(base64.b64encode(jpeg)) <= 256 * 1024  # Spotify's limit


def test_colour_follows_positivity() -> None:
    assert mood_hue(0.0) == 230  # blue when low
    assert mood_hue(1.0) == 30  # warm orange when bright


def test_the_cover_is_uploaded_to_the_new_playlist_as_base64_jpeg() -> None:
    spotify = Spotify()

    status, body = save(ALL, spotify, {"name": "Muse", "track_ids": TRACKS, "cover": COVER})

    assert status == 201 and body["cover"] == "added"
    upload = spotify.requests[-1]
    assert upload.method == "PUT"
    assert upload.url.path == "/v1/playlists/3cEYpjA9oz9GiPac4AsH4n/images"
    assert upload.headers["content-type"] == "image/jpeg"
    assert base64.b64decode(upload.content)[:2] == b"\xff\xd8"  # a JPEG


def test_an_old_login_saves_the_playlist_and_asks_to_log_in_again_for_covers() -> None:
    spotify = Spotify()

    status, body = save(
        {"playlist-modify-private"}, spotify, {"name": "Muse", "track_ids": TRACKS, "cover": COVER}
    )

    assert status == 201 and body["cover"] == "needs_login"
    assert not any(r.url.path.endswith("/images") for r in spotify.requests)


def test_a_failed_upload_never_fails_the_playlist() -> None:
    status, body = save(
        ALL, Spotify(image_status=500), {"name": "Muse", "track_ids": TRACKS, "cover": COVER}
    )

    assert status == 201 and body["cover"] == "failed"
    assert body["spotify_playlist_id"] == "3cEYpjA9oz9GiPac4AsH4n"


def test_no_cover_asked_means_no_upload() -> None:
    spotify = Spotify()

    status, body = save(ALL, spotify, {"name": "Muse", "track_ids": TRACKS})

    assert status == 201 and body["cover"] == "none"
    assert not any(r.url.path.endswith("/images") for r in spotify.requests)


def test_covers_only_go_on_playlists_muse_just_created() -> None:
    import asyncio

    import pytest

    from app.clients.spotify_user import ForbiddenCallError, SpotifyUserClient

    client = SpotifyUserClient(httpx2.AsyncClient(transport=httpx2.MockTransport(Spotify())), "t")
    with pytest.raises(ForbiddenCallError):
        asyncio.run(client.upload_cover("someoneElsesPlaylist", b"jpeg"))


def test_cover_preview_is_a_jpeg_and_inputs_are_checked() -> None:
    client = TestClient(create_app(Settings(_env_file=None, app_env="test")))

    ok = client.get(
        "/api/v1/covers",
        params={"valence": 0.3, "energy": 0.2, "title": "Soft", "words": ["tired"]},
    )
    bad = client.get("/api/v1/covers", params={"valence": 2, "energy": 0.2, "title": "x"})

    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/jpeg"
    assert bad.status_code == 422
