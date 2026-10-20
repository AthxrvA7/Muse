"""Query planning: which searches Muse runs for a mood + taste."""

from app.schemas.curate import Taste
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.recommender.planner import plan_searches
from tests.recommender_fixtures import mood

KB = load_genre_knowledge()
CALM_LOW = mood(0.30, 0.20)  # tired, low
HYPED = mood(0.85, 0.90)


def test_favourite_artists_are_searched_first() -> None:
    plans = plan_searches(CALM_LOW, Taste(artists=["Prateek Kuhad", "Arijit Singh"]), KB)

    assert [(p.kind, p.value, p.reason) for p in plans[:2]] == [
        ("artist", "Prateek Kuhad", "favourite_artist"),
        ("artist", "Arijit Singh", "favourite_artist"),
    ]
    assert plans[0].query == 'artist:"Prateek Kuhad"'


def test_favourite_genres_closest_to_the_mood_are_chosen() -> None:
    taste = Taste(genres=["metal", "lo-fi", "edm", "ghazal"])

    calm = [p.value for p in plan_searches(CALM_LOW, taste, KB)]
    hyped = [p.value for p in plan_searches(HYPED, taste, KB)]

    assert calm[:2] == ["ghazal", "lo-fi"]  # quiet genres first when tired
    assert hyped[0] == "edm"  # loud genre first when hyped
    assert len(calm) == 3  # at most 3 favourite genres


def test_genre_searches_carry_a_keyword_fallback() -> None:
    plan = plan_searches(CALM_LOW, Taste(genres=["lo-fi"]), KB)[0]

    assert plan.query == 'genre:"lo-fi"'
    assert plan.fallback_query == "lofi chill beats"


def test_languages_add_genres_in_that_language() -> None:
    plans = plan_searches(CALM_LOW, Taste(languages=["hi"]), KB)

    language_plans = [p for p in plans if p.reason == "language"]
    assert len(language_plans) == 2
    assert all("hi" in KB.genres[p.value].langs for p in language_plans)


def test_no_taste_lets_the_mood_choose_four_genres() -> None:
    plans = plan_searches(CALM_LOW, Taste(), KB)

    assert len(plans) == 4
    assert {p.reason for p in plans} == {"mood"}
    assert all(KB.genres[p.value].energy <= 0.4 for p in plans)


def test_discovery_mode_adds_new_genres_in_the_users_languages() -> None:
    taste = Taste(artists=["Arijit Singh"], languages=["hi"])

    plans = plan_searches(mood(0.5, 0.4, mode="discovery"), taste, KB)

    discovery = [p for p in plans if p.reason == "discovery"]
    assert len(discovery) == 2
    for p in discovery:
        langs = KB.genres[p.value].langs
        assert not langs or "hi" in langs  # never a language the user didn't ask for


def test_comfort_mode_adds_no_discovery_genres() -> None:
    plans = plan_searches(CALM_LOW, Taste(artists=["Arijit Singh"]), KB)

    assert all(p.reason != "discovery" for p in plans)


def test_unknown_genres_are_ignored_by_the_planner() -> None:
    assert plan_searches(CALM_LOW, Taste(genres=["not-a-genre"]), KB) != []
