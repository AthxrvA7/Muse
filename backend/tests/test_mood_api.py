"""HTTP tests for POST /api/v1/mood/analyze."""

from fastapi.testclient import TestClient

URL = "/api/v1/mood/analyze"


def test_analyze_returns_a_mood_profile(client: TestClient) -> None:
    response = client.post(URL, json={"chips": ["tired", "low"], "text": "long day"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "valence",
        "energy",
        "tempo",
        "mode",
        "labels",
        "confidence",
        "text_analysis",
    }
    assert body["tempo"] == "slow"


def test_empty_request_is_rejected(client: TestClient) -> None:
    assert client.post(URL, json={}).status_code == 422
    assert client.post(URL, json={"chips": [], "text": "   "}).status_code == 422


def test_unknown_chip_returns_422_with_allowed_chips(client: TestClient) -> None:
    response = client.post(URL, json={"chips": ["hangry"]})

    assert response.status_code == 422
    assert "calm" in response.json()["detail"]["allowed_chips"]


def test_too_many_chips_are_rejected(client: TestClient) -> None:
    chips = ["happy", "calm", "tired", "low", "angry", "focused"]

    assert client.post(URL, json={"chips": chips}).status_code == 422


def test_text_longer_than_500_characters_is_rejected(client: TestClient) -> None:
    assert client.post(URL, json={"text": "a" * 501}).status_code == 422


def test_unexpected_fields_are_rejected(client: TestClient) -> None:
    assert client.post(URL, json={"chips": ["calm"], "user_id": "x"}).status_code == 422


def test_chips_are_case_insensitive_and_deduplicated(client: TestClient) -> None:
    response = client.post(URL, json={"chips": ["Calm", "calm "]})

    assert response.status_code == 200
    assert response.json()["labels"] == ["calm"]
