"""Scoring: mood fit, taste fit, filters and speed."""

import time
from typing import Literal

from app.schemas.curate import Taste
from app.schemas.mood import MoodProfile
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.candidates import Candidate
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.recommender.planner import Reason, SearchPlan
from app.services.recommender.scoring import ScoredTrack, keep_allowed, score_candidates
from tests.recommender_fixtures import mood, track

KB = load_genre_knowledge()
ANALYZER = MoodAnalyzer(load_vocabulary())
CALM_LOW = mood(0.30, 0.20)


def found_by(reason: Reason, value: str, kind: Literal["artist", "genre"] = "genre") -> SearchPlan:
    return SearchPlan(kind, value, reason, "q")


def score(
    candidates: list[Candidate], taste: Taste | None = None, m: MoodProfile = CALM_LOW
) -> list[ScoredTrack]:
    return score_candidates(candidates, m, taste or Taste(), KB, ANALYZER)


def test_track_from_a_quiet_genre_fits_a_tired_mood_better_than_metal() -> None:
    quiet = Candidate(track("q"), [found_by("mood", "ghazal")])
    loud = Candidate(track("l"), [found_by("mood", "metal")])

    by_id = {s.candidate.track.id: s for s in score([quiet, loud])}

    assert by_id["q"].mood_fit > 0.8
    assert by_id["l"].mood_fit < 0.6
    assert by_id["q"].mood_source == "ghazal"


def test_title_mood_words_are_used_when_no_genre_is_known() -> None:
    sad_title = Candidate(
        track("s", name="Sad Song"), [found_by("favourite_artist", "X", "artist")]
    )

    scored = score([sad_title])[0]

    assert scored.mood_source == "low"
    assert scored.mood_fit > 0.8


def test_unknown_feel_counts_as_neutral() -> None:
    plain = Candidate(track("p", name="Tum Hi Ho"), [found_by("favourite_artist", "X", "artist")])

    assert score([plain])[0].mood_fit == 0.5
    assert score([plain])[0].mood_source is None


def test_favourite_artist_gives_full_taste_fit_even_via_a_genre_search() -> None:
    candidate = Candidate(track("t", artist="Prateek Kuhad"), [found_by("mood", "indie folk")])

    scored = score([candidate], Taste(artists=["prateek kuhad"]))[0]

    assert scored.taste_fit == 1.0
    assert scored.favourite_artist == "prateek kuhad"
    assert scored.taste_reason == "favourite_artist"


def test_taste_reasons_rank_artist_over_genre_over_language() -> None:
    reasons: list[Reason] = ["favourite_genre", "language", "discovery"]
    fits = [score([Candidate(track(r), [found_by(r, "pop")])])[0].taste_fit for r in reasons]

    assert fits == [0.75, 0.5, 0.25]


def test_discovery_mode_weighs_mood_more_than_comfort_mode() -> None:
    candidate = Candidate(track("t"), [found_by("discovery", "ghazal")])

    comfort = score([candidate], m=mood(0.3, 0.2, mode="comfort"))[0].score
    discovery = score([candidate], m=mood(0.3, 0.2, mode="discovery"))[0].score

    assert discovery > comfort


def test_excluded_artists_and_explicit_tracks_are_filtered() -> None:
    candidates = [
        Candidate(track("a", artist="Honey Singh")),
        Candidate(track("b", explicit=True)),
        Candidate(track("c")),
    ]

    kept = keep_allowed(candidates, Taste(exclude_artists=["honey singh"], allow_explicit=False))

    assert [c.track.id for c in kept] == ["c"]


def test_scoring_300_candidates_takes_under_200_ms() -> None:  # NFR1
    genres = list(KB.genres)
    candidates = [
        Candidate(track(str(i), name=f"Track {i}"), [found_by("mood", genres[i % len(genres)])])
        for i in range(300)
    ]

    start = time.perf_counter()
    scored = score(candidates)
    elapsed = time.perf_counter() - start

    assert len(scored) == 300
    assert elapsed < 0.2
