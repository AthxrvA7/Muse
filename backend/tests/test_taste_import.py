"""Import from Spotify: suggest a taste profile from the user's top artists (fake Spotify)."""

from datetime import UTC, datetime

import httpx2
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_taste_import_service
from app.clients.spotify_user import TopArtist
from app.core.config import Settings
from app.db.models import User
from app.main import create_app
from app.services.auth import NotLoggedInError
from app.services.recommender.knowledge import get_genre_knowledge
from app.services.taste_import import TasteImportService, match_genre, suggest_taste

USER = User(
    id="user-1",
    spotify_id="spotify-ath",
    display_name="Ath",
    created_at=datetime(2026, 11, 25, tzinfo=UTC),
    last_login_at=datetime(2026, 11, 25, tzinfo=UTC),
)
ALL_SCOPES = {"playlist-modify-private", "user-read-private", "user-top-read"}


class FakeTokens:
    def __init__(self, scopes: set[str] = ALL_SCOPES, error: Exception | None = None) -> None:
        self.scopes = scopes
        self.error = error

    async def access_token(self, user_id: str) -> str:
        return "user-token"

    async def granted_scopes(self, user_id: str) -> set[str]:
        if self.error:
            raise self.error
        return self.scopes


class FakeSpotify:
    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.paths: list[str] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.paths.append(request.url.path)
        return httpx2.Response(
            self.status,
            json={
                "items": [
                    {"name": "Arijit Singh", "genres": ["filmi", "modern bollywood"]},
                    {"name": "Prateek Kuhad", "genres": ["hindi indie", "indian indie"]},
                    {"name": "The Weeknd", "genres": ["canadian contemporary r&b", "pop"]},
                    {"name": "Anuv Jain", "genres": []},
                ]
            },
        )


def client_for(tokens: FakeTokens, spotify: FakeSpotify) -> TestClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(spotify))
    service = TasteImportService(tokens, http, get_genre_knowledge())
    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_taste_import_service] = lambda: service
    return TestClient(app)


def test_spotify_genres_map_to_genres_muse_knows() -> None:
    kb = get_genre_knowledge()
    assert match_genre("bollywood", kb) == "bollywood"
    assert match_genre("modern bollywood", kb) == "bollywood"
    assert match_genre("canadian contemporary r&b", kb) == "r&b"
    assert match_genre("dream pop", kb) == "dream pop"  # longest match, not "pop"
    assert match_genre("k-pop boy group", kb) == "k-pop"  # not plain "pop"
    assert match_genre("vaporwave", kb) is None


def test_suggestion_has_artists_and_the_genres_and_languages_they_share() -> None:
    suggestion = suggest_taste(
        [
            TopArtist("Arijit Singh", ["filmi", "modern bollywood"]),
            TopArtist("Shreya Ghoshal", ["filmi", "bollywood"]),
            TopArtist("Arijit Singh", ["filmi"]),  # duplicates are dropped
            TopArtist("Unknown", []),
        ],
        get_genre_knowledge(),
    )

    assert suggestion.artists == ["Arijit Singh", "Shreya Ghoshal", "Unknown"]
    assert suggestion.genres[:2] == ["filmi", "bollywood"]
    assert suggestion.languages == ["hi"]
    assert suggestion.saved is False


def test_endpoint_returns_a_suggestion_and_saves_nothing() -> None:
    spotify = FakeSpotify()

    response = client_for(FakeTokens(), spotify).get("/api/v1/preferences/from-spotify")

    assert response.status_code == 200
    body = response.json()
    assert body["artists"] == ["Arijit Singh", "Prateek Kuhad", "The Weeknd", "Anuv Jain"]
    assert {"bollywood", "hindi indie", "r&b"} <= set(body["genres"])
    assert "hi" in body["languages"]
    assert body["saved"] is False
    assert spotify.paths == ["/v1/me/top/artists"]  # one read-only call, nothing else


def test_old_login_without_the_permission_is_asked_to_log_in_again() -> None:
    spotify = FakeSpotify()

    response = client_for(FakeTokens(scopes={"user-read-private"}), spotify).get(
        "/api/v1/preferences/from-spotify"
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "relogin_needed"
    assert spotify.paths == []  # Spotify is not even asked


def test_expired_login_and_spotify_refusal_are_explained() -> None:
    expired = client_for(FakeTokens(error=NotLoggedInError("x")), FakeSpotify())
    refused = client_for(FakeTokens(), FakeSpotify(status=403))

    assert expired.get("/api/v1/preferences/from-spotify").status_code == 401
    assert refused.get("/api/v1/preferences/from-spotify").status_code == 403


def test_import_needs_a_login() -> None:
    client = TestClient(create_app(Settings(_env_file=None, app_env="test")))

    # 503 when login isn't configured at all (as here), 401 when it is but no one logged in
    assert client.get("/api/v1/preferences/from-spotify").status_code in (401, 503)
