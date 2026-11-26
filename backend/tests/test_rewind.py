"""Muse Rewind: the analysis rules, the PDF and preview, and the API (fakes only)."""

import re
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.deps import RewindSources, current_user, get_rewind_sources
from app.core.config import Settings
from app.db.models import PlaylistRecord, Preferences
from app.main import create_app
from app.schemas.feedback import FeedbackRecord
from app.schemas.moods import MoodEntry
from app.services.preferences import music_dna
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.rewind import (
    PERSONALITIES,
    build_rewind,
    clean_name,
    golden_hour,
    journey,
    match,
    personality,
)
from app.services.rewind_render import rewind_pdf, rewind_preview, safe
from tests.fakes import FakePlaylists, FakePreferences
from tests.test_preferences import USER
from tests.test_trajectory import FakeMoodLog

KB = load_genre_knowledge()
NOW = datetime(2026, 11, 26, 12, tzinfo=UTC)


def mood(days_ago: float, valence: float, energy: float, *labels: str) -> MoodEntry:
    return MoodEntry(
        at=NOW - timedelta(days=days_ago),
        valence=valence,
        energy=energy,
        labels=list(labels) or ["calm"],
        mode="comfort",
    )


def dna(*genres: str, artists: tuple[str, ...] = ("Prateek Kuhad", "Lauv")):  # type: ignore[no-untyped-def]
    known = [g for g in genres if g in KB.genres] or list(KB.genres)[:2]
    prefs = Preferences(
        user_id=USER.id,
        artists=list(artists),
        genres=known,
        languages=["en"],
        styles=[],
        reference_tracks=[],
        exclusions=[],
        updated_at=NOW,
    )
    return music_dna(prefs, KB)


def rating(days_ago: int, value: int, artist: str) -> FeedbackRecord:
    return FeedbackRecord.model_construct(
        track_id=f"t{days_ago}{artist}",
        value=value,
        artist_ids=[artist.lower()],
        artist_names=[artist],
        genre=None,
        language=None,
        valence=0.5,
        energy=0.5,
        user_id=USER.id,
        updated_at=NOW - timedelta(days=days_ago),
    )


def playlist(days_ago: int, name: str = "Muse: calm") -> PlaylistRecord:
    return PlaylistRecord(
        user_id=USER.id,
        spotify_playlist_id="p" * 22,
        url="https://open.spotify.com/playlist/x",
        name=name,
        track_count=15,
        created_at=NOW - timedelta(days=days_ago),
    )


# ---------------------------------------------------------------- analysis rules


def test_personality_follows_where_the_moods_sat() -> None:
    assert personality([mood(1, 0.8, 0.8)]) == PERSONALITIES["bright"]
    assert personality([mood(1, 0.7, 0.2), mood(2, 0.8, 0.3)]) == PERSONALITIES["calm"]
    assert personality([mood(1, 0.2, 0.8)]) == PERSONALITIES["tense"]
    assert personality([mood(1, 0.2, 0.2)]) == PERSONALITIES["low"]
    all_over = [mood(1, 0.1, 0.1), mood(2, 0.9, 0.9), mood(3, 0.1, 0.9), mood(4, 0.9, 0.1)]
    assert personality(all_over) == PERSONALITIES["shapeshifter"]
    assert personality([]) is None


def test_journey_golden_hour_and_match() -> None:
    assert journey([mood(3, 0.2, 0.8), mood(1, 0.8, 0.2)]) == (
        "You started tense & wired and ended calm & content."
    )
    assert (
        journey([mood(3, 0.7, 0.3), mood(1, 0.8, 0.2)]) == "You kept coming back to calm & content."
    )
    assert journey([mood(1, 0.5, 0.5)]) is None
    assert golden_hour({"morning": 0.7, "night": 0.3}) == "Mornings"
    assert golden_hour({"night": 0.8, "evening": 0.3}) == "Nights"
    assert golden_hour({"morning": 0.7}) is None

    taste = dna("lofi")
    assert taste.mood_centre is not None
    same = mood(1, taste.mood_centre.valence, taste.mood_centre.energy)
    assert match(taste, [same]) == 100
    assert match(taste, []) is None
    assert match(None, [same]) is None


def test_names_are_first_names_the_font_can_draw() -> None:
    assert clean_name("Atharva Ingale") == "Atharva"
    assert clean_name("अथर्व") is None
    assert clean_name(None) is None
    assert safe("Arijit Singh अरिजीत") == "Arijit Singh"
    assert safe("Beyoncé – Live") == "Beyoncé – Live"


def test_the_rewind_uses_only_the_period_and_the_parts_asked_for() -> None:
    moods = [mood(40, 0.1, 0.1, "low"), *[mood(d, 0.7, 0.3, "calm") for d in (9, 6, 3, 1)]]
    report = build_rewind(
        name="Atharva Ingale",
        days=30,
        now=NOW,
        offset_minutes=330,
        moods=moods,
        dna=dna("lofi"),
        ratings=[rating(2, 1, "Lauv"), rating(45, -1, "Old")],
        playlists=[playlist(1), playlist(60)],
    )
    assert report.period == "27 Oct - 26 Nov 2026"
    assert len(report.moods) == 4  # the 40-day-old mood is outside the month
    assert report.top_mood == "calm" and report.top_mood_share == 100
    assert report.rated == 1 and len(report.playlists) == 1
    assert report.pages[0] == "cover" and report.pages[-1] == "outro"
    assert {"mood_word", "personality", "journey", "sound", "match", "learned"} <= set(report.pages)

    nothing = build_rewind(
        name=None,
        days=7,
        now=NOW,
        offset_minutes=0,
        moods=None,
        dna=None,
        ratings=None,
        playlists=None,
    )
    assert nothing.pages == ["cover", "outro"]
    assert nothing.title_owner == "Your" and nothing.span == "week"


# ---------------------------------------------------------------- PDF and preview


def full_report():  # type: ignore[no-untyped-def]
    moods = [
        mood(d, v, e, label)
        for d, v, e, label in [
            (20, 0.3, 0.7, "stressed"),
            (15, 0.4, 0.4, "tired"),
            (10, 0.6, 0.3, "calm"),
            (5, 0.7, 0.6, "happy"),
            (1, 0.75, 0.7, "happy"),
        ]
    ]
    return build_rewind(
        name="Ath",
        days=30,
        now=NOW,
        offset_minutes=330,
        moods=moods,
        dna=dna("lofi", "pop", artists=("Prateek Kuhad", "अरिजीत", "Taylor Swift")),
        ratings=[rating(1, 1, "Lauv"), rating(2, 1, "Lauv"), rating(3, -1, "X")],
        playlists=[playlist(d, f"Muse: mix {d}") for d in range(1, 9)],
    )


def test_the_pdf_has_one_page_per_part_and_stays_small() -> None:
    report = full_report()
    pdf = rewind_pdf(report)
    assert pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type /Page\b(?!s)", pdf)) == len(report.pages) >= 8
    assert len(pdf) < 2_500_000


def test_the_preview_is_a_strip_of_all_pages() -> None:
    from io import BytesIO

    from PIL import Image

    report = full_report()
    strip = Image.open(BytesIO(rewind_preview(report, height=320)))
    assert strip.format == "JPEG" and strip.height == 320
    page_width = round(1080 * 320 / 1920)
    assert strip.width == len(report.pages) * (page_width + 24) - 24


# ---------------------------------------------------------------- API


class Ratings:
    def __init__(self, items: list[FeedbackRecord]) -> None:
        self.items = items

    async def list_for_user(self, user_id: str) -> list[FeedbackRecord]:
        return self.items


def api(logged_in: bool = True) -> TestClient:
    moods = FakeMoodLog(USER.id)
    moods.entries[USER.id] = [mood(5, 0.3, 0.6, "low"), mood(1, 0.7, 0.4, "calm")]
    preferences = FakePreferences()
    preferences.by_user[USER.id] = Preferences(
        user_id=USER.id,
        artists=["Lauv"],
        genres=list(KB.genres)[:2],
        languages=["en"],
        styles=[],
        reference_tracks=[],
        exclusions=[],
        updated_at=NOW,
    )
    playlists = FakePlaylists()
    sources = RewindSources(
        moods,  # type: ignore[arg-type]
        preferences,  # type: ignore[arg-type]
        Ratings([rating(1, 1, "Lauv")]),  # type: ignore[arg-type]
        playlists,  # type: ignore[arg-type]
    )
    app = create_app(Settings(_env_file=None))
    if logged_in:
        app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[get_rewind_sources] = lambda: sources
    return TestClient(app)


def test_download_the_rewind_pdf() -> None:
    response = api().get("/api/v1/me/rewind", params={"tz": 330})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith('attachment; filename="muse-rewind-')
    assert response.content.startswith(b"%PDF")
    assert int(response.headers["x-rewind-pages"]) >= 5


def test_parts_can_be_left_out_and_previewed() -> None:
    client = api()
    everything = int(client.get("/api/v1/me/rewind").headers["x-rewind-pages"])
    preview = client.get(
        "/api/v1/me/rewind",
        params={"format": "preview", "moods": False, "learned": False},
    )
    assert preview.headers["content-type"] == "image/jpeg"
    assert int(preview.headers["x-rewind-pages"]) < everything


def test_rewind_checks_its_options_and_needs_a_login() -> None:
    client = api()
    for params in ({"days": 0}, {"days": 91}, {"tz": 900}, {"format": "docx"}):
        assert client.get("/api/v1/me/rewind", params=params).status_code == 422
    assert api(logged_in=False).get("/api/v1/me/rewind").status_code in (401, 503)


def test_the_website_may_show_the_preview_image() -> None:
    from app.core.security import _WEB_CSP

    img_src = next(part for part in _WEB_CSP.split(";") if part.strip().startswith("img-src"))
    assert "blob:" in img_src  # the preview strip is shown from a blob: URL
