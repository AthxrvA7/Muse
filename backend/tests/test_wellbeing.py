"""Wellbeing notice: shown for crisis language, never for everyday phrases."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.services.mood.wellbeing import load_wellbeing_check

URL = "/api/v1/mood/analyze"


@pytest.mark.parametrize(
    "text",
    [
        "I just want to die",
        "honestly thinking about suicide",
        "Everyone would be better off without me",
        "I don’t want to be here anymore",  # curly apostrophe, as phones type it
        "been  hurting   myself again",
    ],
)
def test_crisis_language_adds_a_support_notice(text: str) -> None:
    notice = load_wellbeing_check().check(text)

    assert notice is not None
    assert "14416" in notice.resources[0]["phone"]


@pytest.mark.parametrize(
    "text",
    [
        "this song kills it",
        "I'm dying to hear the new album",
        "killing it at the gym today",
        "a bit sad and tired",
        "I could just disappear into this playlist",
    ],
)
def test_everyday_phrases_do_not_trigger_it(text: str) -> None:
    assert load_wellbeing_check().check(text) is None


def test_api_still_returns_music_characteristics_with_the_notice(client: TestClient) -> None:
    response = client.post(URL, json={"text": "I want to end my life"})

    assert response.status_code == 200
    body = response.json()
    assert body["support"]["resources"][0]["name"].startswith("Tele-MANAS")
    assert 0 <= body["valence"] <= 1  # the mood profile is still there


def test_the_text_is_never_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        client.post(URL, json={"text": "I want to end my life"})

    assert "end my life" not in caplog.text
