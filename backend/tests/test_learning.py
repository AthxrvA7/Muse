"""Learning from 👍/👎: the rules, the API, and their effect on curation (fakes only)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_feedback_repository
from app.core.config import Settings
from app.main import create_app
from app.schemas.curate import CurateRequest
from app.schemas.feedback import FeedbackIn, FeedbackRecord
from app.services.curate import CurateService, Personal
from app.services.learning import apply_learning, learn, liked_artists_to_search, summarise
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.candidates import Candidate
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.recommender.scoring import ScoredTrack
from tests.recommender_fixtures import mood, track
from tests.test_preferences import USER

pytestmark = pytest.mark.anyio
KB = load_genre_knowledge()
T = "a" * 22  # Spotify-shaped IDs
NOW = datetime(2026, 11, 26, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def rating(
    track_id: str, value: int, artist: str, genre: str | None = None, **mood_at: float
) -> FeedbackRecord:
    # model_construct: these rule tests use short, readable IDs
    return FeedbackRecord.model_construct(
        track_id=track_id,
        value=value,
        artist_ids=[artist.lower().replace(" ", "")],
        artist_names=[artist],
        genre=genre,
        user_id="u",
        updated_at=NOW,
        **mood_at,
    )


def scored(track_id: str, artist: str, score: float = 0.5, genre: str | None = None) -> ScoredTrack:
    item = ScoredTrack(
        candidate=Candidate(track(track_id, artist)),
        mood_fit=0.5,
        taste_fit=0.5,
        score=score,
        mood_source=None,
        favourite_artist=None,
        taste_reason=None,
        genre=genre,
    )
    item.candidate.track.artists[0].id = artist.lower().replace(" ", "")
    return item


# ---------------------------------------------------------------- the rules


def test_disliked_songs_and_avoided_artists_are_left_out() -> None:
    learned = learn(
        [
            rating("bad", -1, "Someone"),
            rating("x1", -1, "Avoided"),
            rating("x2", -1, "Avoided"),
        ]
    )
    items = [scored("bad", "Someone"), scored("new", "Avoided"), scored("ok", "Fine")]

    kept = apply_learning(items, learned, mood(0.5, 0.5))

    assert [i.candidate.track.id for i in kept] == ["ok"]


def test_liked_songs_rise_more_when_the_mood_is_similar() -> None:
    learned = learn([rating("song", 1, "Arijit Singh", valence=0.3, energy=0.3)])

    similar = apply_learning([scored("song", "Arijit Singh")], learned, mood(0.35, 0.3))[0]
    different = apply_learning([scored("song", "Arijit Singh")], learned, mood(0.9, 0.9))[0]

    assert similar.score > different.score > 0.5
    assert similar.learned == "liked"


def test_liked_artists_and_genres_get_a_small_capped_lift() -> None:
    learned = learn([rating(f"s{i}", 1, "Prateek Kuhad", "hindi indie") for i in range(10)])

    item = apply_learning(
        [scored("other", "Prateek Kuhad", genre="hindi indie")], learned, mood(0.5, 0.5)
    )[0]

    assert item.learned == "liked_artist:Prateek Kuhad"
    assert item.score == pytest.approx(0.5 + 0.12 + 0.06)  # both nudges capped


def test_liked_artists_are_searched_unless_already_favourites() -> None:
    learned = learn(
        [rating("a", 1, "Anuv Jain"), rating("b", 1, "Anuv Jain"), rating("c", 1, "JV")]
    )

    assert liked_artists_to_search(learned, ["Arijit Singh"]) == ["Anuv Jain", "JV"]
    assert liked_artists_to_search(learned, ["anuv jain"]) == ["JV"]


def test_nothing_learned_changes_nothing() -> None:
    items = [scored("x", "A", 0.42)]
    assert apply_learning(items, learn([]), mood(0.5, 0.5))[0].score == 0.42


def test_summary_counts_and_ratings() -> None:
    summary = summarise([rating("a", 1, "A"), rating("b", 1, "A"), rating("c", -1, "B")])

    assert (summary.likes, summary.dislikes) == (2, 1)
    assert [(a.name, a.count) for a in summary.liked_artists] == [("A", 2)]
    assert [(a.name, a.count) for a in summary.avoided_artists] == [("B", 1)]
    assert summary.ratings == {"a": 1, "b": 1, "c": -1}


# ---------------------------------------------------------------- the API


class FakeRatings:
    def __init__(self) -> None:
        self.items: dict[str, FeedbackRecord] = {}

    async def rate(self, user_id: str, body: FeedbackIn) -> None:
        if body.value == 0:
            self.items.pop(body.track_id, None)
        else:
            self.items[body.track_id] = FeedbackRecord(
                **body.model_dump(), user_id=user_id, updated_at=NOW
            )

    async def list_for_user(self, user_id: str) -> list[FeedbackRecord]:
        return list(self.items.values())

    async def delete_all(self, user_id: str) -> int:
        count = len(self.items)
        self.items.clear()
        return count


def api(repo: FakeRatings, logged_in: bool = True) -> TestClient:
    app = create_app(Settings(_env_file=None, app_env="test"))
    if logged_in:
        app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_feedback_repository] = lambda: repo
    return TestClient(app)


def test_rate_then_see_what_muse_learned_then_forget() -> None:
    repo = FakeRatings()
    client = api(repo)
    body = {"track_id": T, "value": 1, "artist_ids": ["abc"], "artist_names": ["Arijit Singh"]}

    assert client.put("/api/v1/feedback", json=body).status_code == 204
    learned = client.get("/api/v1/feedback").json()
    assert learned["likes"] == 1 and learned["ratings"] == {T: 1}
    assert learned["liked_artists"] == [{"name": "Arijit Singh", "count": 1}]

    assert client.put("/api/v1/feedback", json={**body, "value": 0}).status_code == 204
    assert client.get("/api/v1/feedback").json()["likes"] == 0

    client.put("/api/v1/feedback", json=body)
    assert client.delete("/api/v1/feedback").status_code == 204
    assert repo.items == {}


def test_ratings_are_checked_and_need_a_login() -> None:
    client = api(FakeRatings())
    for bad in (
        {"track_id": "short", "value": 1},
        {"track_id": T, "value": 5},
        {"track_id": T, "value": 1, "artist_ids": ["no spaces!"]},
    ):
        assert client.put("/api/v1/feedback", json=bad).status_code == 422
    anonymous = api(FakeRatings(), logged_in=False)
    assert anonymous.put("/api/v1/feedback", json={"track_id": T, "value": 1}).status_code in (
        401,
        503,
    )


# ---------------------------------------------------------------- effect on curation


class Catalogue:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search_tracks(self, query: str, total: int = 10) -> list:  # type: ignore[type-arg]
        self.queries.append(query)
        for name in ("Taylor Swift", "Liked Artist"):
            if f'artist:"{name}"' in query:
                key = name.split()[0]
                return [
                    track(f"{key}{i}".ljust(22, "x"), name, f"{name} song {i}") for i in range(6)
                ]
        return []


async def test_ratings_shape_the_next_playlist() -> None:
    catalogue = Catalogue()
    repo = FakeRatings()
    disliked = "Taylor0".ljust(22, "x")
    liked_song = "Taylor1".ljust(22, "x")
    await repo.rate(
        "u",
        FeedbackIn(
            track_id=disliked, value=-1, artist_ids=["taylorswift"], artist_names=["Taylor Swift"]
        ),
    )
    await repo.rate(
        "u",
        FeedbackIn(
            track_id=liked_song, value=1, artist_ids=["taylorswift"], artist_names=["Taylor Swift"]
        ),
    )
    await repo.rate(
        "u",
        FeedbackIn(
            track_id="z" * 22, value=1, artist_ids=["likedartist"], artist_names=["Liked Artist"]
        ),
    )
    service = CurateService(catalogue, MoodAnalyzer(load_vocabulary()), KB)
    request = CurateRequest.model_validate(
        {
            "mood": {"chips": ["calm"]},
            "taste": {"artists": ["Taylor Swift"]},
            "size": 10,
            "language": "mix",
        }
    )

    preview = await service.preview(request, Personal("u", feedback=repo))

    ids = [t.track.id for t in preview.tracks]
    assert disliked not in ids  # 👎 never comes back
    assert 'artist:"Liked Artist"' in catalogue.queries  # 👍 artists are looked for
    assert preview.learned_from == 3
    liked = next(t for t in preview.tracks if t.track.id == liked_song)
    assert "you gave it a 👍 before" in liked.reason
