"""Mood trajectory: the summary rules, the API, and logging from curate (fakes only)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_mood_log_repository
from app.core.config import Settings
from app.main import create_app
from app.schemas.curate import CurateRequest
from app.schemas.moods import MoodEntry
from app.services.curate import CurateService, Personal
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.trajectory import summarise
from tests.recommender_fixtures import track
from tests.test_preferences import USER

pytestmark = pytest.mark.anyio
START = datetime(2026, 11, 1, 9, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def entry(day: int, valence: float, energy: float, *labels: str) -> MoodEntry:
    return MoodEntry(
        at=START + timedelta(days=day),
        valence=valence,
        energy=energy,
        labels=list(labels) or ["calm"],
        mode="comfort",
    )


# ---------------------------------------------------------------- summary rules


def test_no_points_means_no_summary() -> None:
    result = summarise([], 30)
    assert result.points == [] and result.average is None
    assert result.brightness is None and result.energy is None


def test_averages_and_most_frequent_mood_words() -> None:
    points = [entry(0, 0.2, 0.4, "low"), entry(1, 0.4, 0.6, "low", "tired"), entry(2, 0.6, 0.2)]
    result = summarise(points, 7)
    assert result.average is not None
    assert result.average.valence == pytest.approx(0.4)
    assert result.average.energy == pytest.approx(0.4)
    assert [(c.label, c.count) for c in result.top_labels] == [
        ("low", 2),
        ("tired", 1),
        ("calm", 1),
    ]
    assert result.brightness is None  # too few points to call a direction


def test_recent_half_is_compared_with_the_earlier_half() -> None:
    getting_lighter = [entry(i, v, 0.5) for i, v in enumerate([0.2, 0.3, 0.6, 0.7])]
    result = summarise(getting_lighter, 30)
    assert result.brightness == "lighter" and result.energy == "steady"

    winding_down = [entry(i, 0.5, e) for i, e in enumerate([0.9, 0.8, 0.4, 0.3, 0.2])]
    result = summarise(winding_down, 30)
    assert result.brightness == "steady" and result.energy == "calmer"

    heavier = [entry(i, v, 0.5) for i, v in enumerate([0.8, 0.7, 0.3, 0.2])]
    assert summarise(heavier, 30).brightness == "heavier"


# ---------------------------------------------------------------- API


class FakeMoodLog:
    def __init__(self, *enabled_for: str) -> None:
        self.entries: dict[str, list[MoodEntry]] = {}
        self.enabled: dict[str, bool] = dict.fromkeys(enabled_for, True)

    async def is_enabled(self, user_id: str) -> bool:
        return self.enabled.get(user_id, False)

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        self.enabled[user_id] = enabled

    async def record(self, user_id: str, item: MoodEntry) -> None:
        if self.enabled.get(user_id):
            self.entries.setdefault(user_id, []).append(item)

    async def list_for_user(self, user_id: str, days: int) -> list[MoodEntry]:
        return list(self.entries.get(user_id, []))

    async def delete_all(self, user_id: str) -> int:
        return len(self.entries.pop(user_id, []))

    async def forget_user(self, user_id: str) -> int:
        self.enabled.pop(user_id, None)
        return await self.delete_all(user_id)


def api(repo: FakeMoodLog, logged_in: bool = True) -> TestClient:
    app = create_app(Settings(_env_file=None))
    if logged_in:
        app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_mood_log_repository] = lambda: repo
    return TestClient(app)


def test_off_by_default_then_turned_on_and_off() -> None:
    repo = FakeMoodLog()
    client = api(repo)
    assert client.get("/api/v1/moods/trajectory").json()["enabled"] is False

    assert client.put("/api/v1/moods/settings", json={"enabled": True}).status_code == 204
    assert client.get("/api/v1/moods/trajectory").json()["enabled"] is True
    assert client.put("/api/v1/moods/settings", json={"enabled": False}).status_code == 204
    assert repo.enabled[USER.id] is False
    for bad in ({}, {"enabled": "maybe"}, {"enabled": True, "extra": 1}):
        assert client.put("/api/v1/moods/settings", json=bad).status_code == 422


def test_see_then_clear_the_trajectory() -> None:
    repo = FakeMoodLog(USER.id)
    repo.entries[USER.id] = [entry(i, 0.2 + i / 10, 0.5, "low") for i in range(4)]
    client = api(repo)

    body = client.get("/api/v1/moods/trajectory", params={"days": 90}).json()
    assert body["enabled"] is True
    assert body["days"] == 90
    assert len(body["points"]) == 4
    assert body["brightness"] == "lighter"
    assert body["top_labels"][0] == {"label": "low", "count": 4}
    assert "text" not in body["points"][0]  # only numbers and mood words

    assert client.delete("/api/v1/moods").status_code == 204
    after = client.get("/api/v1/moods/trajectory").json()
    assert after["points"] == [] and after["enabled"] is True  # clearing keeps the choice


def test_trajectory_checks_days_and_needs_a_login() -> None:
    client = api(FakeMoodLog())
    for days in (0, 91, "x"):
        assert client.get("/api/v1/moods/trajectory", params={"days": days}).status_code == 422
    anonymous = api(FakeMoodLog(), logged_in=False)
    assert anonymous.get("/api/v1/moods/trajectory").status_code in (401, 503)
    put = anonymous.put("/api/v1/moods/settings", json={"enabled": True})
    assert put.status_code in (401, 503)


# ---------------------------------------------------------------- logged from curate


class Catalogue:
    async def search_tracks(self, query: str, total: int = 10) -> list:  # type: ignore[type-arg]
        return [track(f"t{i}".ljust(22, "x"), "Someone", f"Song {i}") for i in range(12)]


class BrokenMoodLog(FakeMoodLog):
    async def record(self, user_id: str, item: MoodEntry) -> None:
        raise RuntimeError("database down")


def curate_request(text: str | None = None) -> CurateRequest:
    mood: dict[str, object] = {"chips": ["calm"]}
    if text:
        mood["text"] = text
    return CurateRequest.model_validate({"mood": mood, "size": 10, "language": "mix"})


async def test_curating_logs_the_mood_but_never_the_text() -> None:
    repo = FakeMoodLog("u")
    service = CurateService(Catalogue(), MoodAnalyzer(load_vocabulary()), load_genre_knowledge())

    preview = await service.preview(curate_request("my secret sentence"), Personal("u", moods=repo))

    (logged,) = repo.entries["u"]
    assert logged.valence == preview.mood.valence and logged.energy == preview.mood.energy
    assert logged.labels == preview.mood.labels and "calm" in logged.labels
    assert "secret" not in logged.model_dump_json()


async def test_nothing_is_logged_unless_turned_on() -> None:
    repo = FakeMoodLog()
    service = CurateService(Catalogue(), MoodAnalyzer(load_vocabulary()), load_genre_knowledge())
    await service.preview(curate_request(), Personal("u", moods=repo))
    assert repo.entries == {}


async def test_a_broken_mood_log_never_fails_the_playlist() -> None:
    service = CurateService(Catalogue(), MoodAnalyzer(load_vocabulary()), load_genre_knowledge())
    preview = await service.preview(curate_request(), Personal("u", moods=BrokenMoodLog()))
    assert preview.tracks
