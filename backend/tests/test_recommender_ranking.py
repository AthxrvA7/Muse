"""Diversity re-ranking and explanations."""

from app.schemas.curate import Taste
from app.services.recommender.candidates import Candidate
from app.services.recommender.explain import explain, mood_phrase
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.recommender.planner import Reason, SearchPlan
from app.services.recommender.ranking import pick_diverse, song_key
from app.services.recommender.scoring import ScoredTrack
from tests.recommender_fixtures import mood, track

KB = load_genre_knowledge()


def scored(
    track_id: str,
    score: float,
    artist: str = "A",
    name: str | None = None,
    *,
    mood_fit: float = 0.5,
    mood_source: str | None = None,
    favourite_artist: str | None = None,
    taste_reason: Reason | None = None,
    sources: list[SearchPlan] | None = None,
) -> ScoredTrack:
    return ScoredTrack(
        candidate=Candidate(track(track_id, artist, name), sources or []),
        mood_fit=mood_fit,
        taste_fit=0.5,
        score=score,
        mood_source=mood_source,
        favourite_artist=favourite_artist,
        taste_reason=taste_reason,
    )


def test_highest_scores_come_first() -> None:
    picked = pick_diverse([scored("b", 0.5, "B"), scored("a", 0.9, "A"), scored("c", 0.7, "C")], 3)

    assert [p.candidate.track.id for p in picked] == ["a", "c", "b"]


def test_at_most_two_songs_per_artist_when_there_is_choice() -> None:
    items = [scored(f"x{i}", 0.9 - i / 100, "Same") for i in range(5)] + [
        scored("o1", 0.5, "Other1"),
        scored("o2", 0.4, "Other2"),
    ]

    picked = pick_diverse(items, 4)

    artists = [p.candidate.track.artists[0].name for p in picked]
    assert artists.count("Same") == 2
    assert len(picked) == 4


def test_artist_limit_relaxes_when_candidates_are_scarce() -> None:
    picked = pick_diverse([scored(f"x{i}", 0.9, "Same") for i in range(5)], 4)

    assert len(picked) == 4


def test_no_single_search_supplies_more_than_40_percent() -> None:
    def from_search(genre: str, score: float) -> list[ScoredTrack]:
        plan = SearchPlan("genre", genre, "favourite_genre", "q")
        return [
            scored(
                f"{genre}{i}",
                score,
                f"{genre}-artist{i}",
                taste_reason="favourite_genre",
                sources=[plan],
            )
            for i in range(10)
        ]

    items = from_search("folk", 0.9) + from_search("lofi", 0.8) + from_search("jazz", 0.7)

    picked = pick_diverse(items, 10)

    ids = [p.candidate.track.id for p in picked]
    assert sum(i.startswith("folk") for i in ids) == 4
    assert sum(i.startswith("lofi") for i in ids) == 4
    assert sum(i.startswith("jazz") for i in ids) == 2


def test_search_limit_relaxes_when_there_are_too_few_searches() -> None:
    plan = SearchPlan("genre", "folk", "favourite_genre", "q")
    items = [
        scored(f"f{i}", 0.9, f"A{i}", taste_reason="favourite_genre", sources=[plan])
        for i in range(10)
    ]

    assert len(pick_diverse(items, 10)) == 10


def test_versions_of_the_same_song_count_once() -> None:
    items = [
        scored("1", 0.9, name="Kasoor"),
        scored("2", 0.8, name="Kasoor - Acoustic"),
        scored("3", 0.7, name="Kasoor (Live)"),
        scored("4", 0.6, name="cold/mess"),
    ]

    picked = pick_diverse(items, 4)

    assert [p.candidate.track.id for p in picked] == ["1", "4"]


def test_song_key_ignores_version_labels() -> None:
    assert song_key(track("1", "X", "Song [Remastered]")) == song_key(track("2", "X", "song"))
    assert song_key(track("1", "X", "Song")) != song_key(track("2", "Y", "Song"))


def test_mood_phrase_turns_labels_into_words() -> None:
    assert mood_phrase(mood(0.3, 0.2, labels=["tired", "low"])) == "tired and low"
    assert mood_phrase(mood(0.2, 0.7, labels=["fear"])) == "anxious"
    assert mood_phrase(mood(0.5, 0.5, labels=["neutral"])) == "current"


def test_explanation_names_the_favourite_artist_and_the_mood_match() -> None:
    item = scored(
        "t", 0.9, mood_fit=0.9, mood_source="indie folk", favourite_artist="Prateek Kuhad"
    )

    text = explain(item, mood(0.3, 0.2, labels=["tired", "low"]), Taste(), KB)

    assert text == (
        "Picked because you like Prateek Kuhad, "
        "and its indie folk feel fits your tired and low mood."
    )


def test_explanation_for_a_language_genre_names_the_language() -> None:
    plan = SearchPlan("genre", "marathi", "language", "q")
    item = scored("t", 0.6, taste_reason="language", sources=[plan], mood_fit=0.6)

    text = explain(item, mood(0.6, 0.5), Taste(languages=["mr"]), KB)

    assert text == "Picked because it's Marathi music in Marathi."


def test_weak_mood_match_is_not_claimed() -> None:
    item = scored("t", 0.6, mood_fit=0.55, mood_source="metal", favourite_artist="X")

    assert "mood" not in explain(item, mood(0.3, 0.2), Taste(), KB)


def test_track_with_no_strong_reason_gets_an_honest_explanation() -> None:
    text = explain(scored("t", 0.3), mood(0.5, 0.5), Taste(), KB)

    assert text.startswith("Included to round out")
