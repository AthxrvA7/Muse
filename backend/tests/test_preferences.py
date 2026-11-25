"""Saved taste profile and Music DNA (logged-in user faked, in-memory storage)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_preferences_repository
from app.core.config import Settings
from app.db.models import User
from app.main import create_app
from tests.fakes import FakePreferences

USER = User(
    id="user-1",
    spotify_id="spotify-ath",
    display_name="Ath",
    created_at=datetime(2026, 11, 25, tzinfo=UTC),
    last_login_at=datetime(2026, 11, 25, tzinfo=UTC),
)
PROFILE = {
    "artists": ["Prateek Kuhad", "Arijit Singh", "prateek kuhad"],
    "genres": ["Indie Folk", "ghazal"],
    "languages": ["hi", "en"],
    "styles": ["acoustic"],
    "reference_tracks": ["4uLU6hMCjMI75M1A2tKUQC"],
    "exclusions": ["Some Artist"],
}


@pytest.fixture
def store() -> FakePreferences:
    return FakePreferences()


@pytest.fixture
def client(store: FakePreferences) -> TestClient:
    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_preferences_repository] = lambda: store
    return TestClient(app)


def test_empty_profile_before_saving(client: TestClient) -> None:
    body = client.get("/api/v1/preferences").json()

    assert body["artists"] == []
    assert body["updated_at"] is None


def test_profile_is_saved_cleaned_and_read_back(client: TestClient, store: FakePreferences) -> None:
    saved = client.put("/api/v1/preferences", json=PROFILE)

    assert saved.status_code == 200
    assert saved.json()["artists"] == ["Prateek Kuhad", "Arijit Singh"]  # duplicate removed
    assert saved.json()["genres"] == ["indie folk", "ghazal"]  # lower-cased
    assert client.get("/api/v1/preferences").json() == saved.json()
    assert store.by_user["user-1"].user_id == "user-1"


def test_saving_again_replaces_the_profile(client: TestClient) -> None:
    client.put("/api/v1/preferences", json=PROFILE)

    client.put("/api/v1/preferences", json={"genres": ["lo-fi"]})

    body = client.get("/api/v1/preferences").json()
    assert body["genres"] == ["lo-fi"]
    assert body["artists"] == []


@pytest.mark.parametrize(
    "bad",
    [
        {"genres": ["vaporwave-polka"]},
        {"languages": ["xx"]},
        {"reference_tracks": ["not-a-track-id"]},
        {"artists": [f"artist {i}" for i in range(11)]},
        {"unknown_field": True},
    ],
)
def test_invalid_profiles_are_rejected(client: TestClient, bad: dict[str, object]) -> None:
    assert client.put("/api/v1/preferences", json=bad).status_code == 422


def test_music_dna_summarises_the_stated_taste(client: TestClient) -> None:
    client.put("/api/v1/preferences", json=PROFILE)

    dna = client.get("/api/v1/preferences/dna").json()

    assert dna["top_artists"] == ["Prateek Kuhad", "Arijit Singh"]
    assert [g["id"] for g in dna["genres"]] == ["indie folk", "ghazal"]
    assert {lang["code"] for lang in dna["languages"]} == {"hi", "en"}
    centre = dna["mood_centre"]
    # indie folk (0.50, 0.30) and ghazal (0.35, 0.20) from genre_kb.json
    assert centre["valence"] == pytest.approx(0.425)
    assert centre["energy"] == pytest.approx(0.25)
    assert centre["label"] == "calm and melancholic"
    assert dna["reference_track_count"] == 1
    assert "2 genre(s)" in dna["summary"]


def test_music_dna_without_a_profile(client: TestClient) -> None:
    dna = client.get("/api/v1/preferences/dna").json()

    assert dna["mood_centre"] is None
    assert "PUT /api/v1/preferences" in dna["summary"]


def test_preferences_need_a_login() -> None:
    client = TestClient(create_app(Settings(_env_file=None, app_env="test")))

    assert client.get("/api/v1/preferences").status_code in (401, 503)
    assert client.put("/api/v1/preferences", json=PROFILE).status_code in (401, 503)
