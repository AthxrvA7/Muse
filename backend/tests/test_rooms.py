"""Room mode: votes, the live summary, limits, and holding up under a busy room."""

import time

import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user
from app.core.config import Settings
from app.main import create_app
from app.services import rooms as rooms_module
from app.services.mood import get_mood_analyzer
from app.services.rooms import (
    MAX_ROOMS,
    MAX_VOTERS,
    NEW_VOTERS_PER_MINUTE,
    ROOM_SECONDS,
    NotHostError,
    RoomFullError,
    RoomLockedError,
    RoomNotFoundError,
    RoomStore,
    TooManyRoomsError,
    get_room_store,
)
from tests.test_preferences import USER


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def store(clock: Clock | None = None) -> RoomStore:
    return RoomStore(get_mood_analyzer(), clock or Clock())


def test_one_vote_per_phone_and_it_can_change() -> None:
    rooms = store()
    code = rooms.create("host")
    rooms.vote(code, "phone-0001", ["happy"])
    rooms.vote(code, "phone-0002", ["calm", "tired"])
    rooms.vote(code, "phone-0001", ["hyped"])  # changed their mind

    summary = rooms.summary(code.lower())  # codes work in any case
    assert summary.voters == 2
    assert [p.labels for p in summary.points] == [["calm", "tired"], ["hyped"]]
    assert {c.label: c.count for c in summary.chips} == {"calm": 1, "tired": 1, "hyped": 1}
    assert summary.average is not None and summary.personality is not None


def test_an_empty_room_has_no_average_or_personality() -> None:
    rooms = store()
    summary = rooms.summary(rooms.create("host"))
    assert summary.voters == 0 and summary.average is None and summary.personality is None


def test_codes_are_short_and_easy_to_read() -> None:
    rooms = store()
    codes = {rooms.create("host") for _ in range(40)}
    assert len(codes) == 40
    assert all(len(c) == 4 and not set(c) & set("01ILO") for c in codes)


def test_rooms_expire_and_unknown_rooms_are_not_found() -> None:
    clock = Clock()
    rooms = store(clock)
    code = rooms.create("host")
    clock.now += ROOM_SECONDS + 1
    with pytest.raises(RoomNotFoundError):
        rooms.summary(code)
    with pytest.raises(RoomNotFoundError):
        rooms.vote("ZZZZ", "phone-0001", ["happy"])


def test_limits_protect_live_rooms() -> None:
    rooms = store()
    first = rooms.create("host")
    for _ in range(MAX_ROOMS - 1):
        rooms.create("host")
    with pytest.raises(TooManyRoomsError):
        rooms.create("host")
    rooms.summary(first)  # the live room was never dropped

    clock = Clock()
    full = store(clock)
    code = full.create("host")
    for i in range(MAX_VOTERS):
        if i and i % NEW_VOTERS_PER_MINUTE == 0:
            clock.now += 61  # a real class joins slower than the pace limit
        full.vote(code, f"phone-{i:05d}", ["calm"])
    clock.now += 61
    with pytest.raises(RoomFullError):
        full.vote(code, "phone-new-one", ["calm"])
    full.vote(code, "phone-00001", ["happy"])  # people already in can still change


def test_a_script_adding_fake_voters_is_slowed_down() -> None:
    rooms = store()
    code = rooms.create("host")
    for i in range(NEW_VOTERS_PER_MINUTE):
        rooms.vote(code, f"bot-{i:06d}", ["angry"])
    with pytest.raises(RoomFullError):
        rooms.vote(code, "bot-one-more", ["angry"])


def test_the_host_can_lock_and_reset_but_nobody_else() -> None:
    rooms = store()
    code = rooms.create("host")
    rooms.vote(code, "phone-0001", ["happy"])
    with pytest.raises(NotHostError):
        rooms.lock(code, "someone-else", True)
    with pytest.raises(NotHostError):
        rooms.reset(code, "someone-else")

    rooms.lock(code, "host", True)
    assert rooms.summary(code).locked
    with pytest.raises(RoomLockedError):
        rooms.vote(code, "phone-late", ["calm"])
    rooms.vote(code, "phone-0001", ["calm"])  # already in: can still change

    rooms.reset(code, "host")
    assert rooms.summary(code).voters == 0


def test_a_busy_room_stays_fast() -> None:
    rooms = store()
    code = rooms.create("host")
    chips = [["happy"], ["calm", "tired"], ["anxious", "stressed", "low"], ["hyped"]]
    started = time.perf_counter()
    for i in range(3000):  # 150 phones, each changing its vote 20 times
        rooms.vote(code, f"phone-{i % NEW_VOTERS_PER_MINUTE:05d}", chips[i % len(chips)])
    for _ in range(50):  # the screen polling
        summary = rooms.summary(code)
    assert summary.voters == NEW_VOTERS_PER_MINUTE
    assert time.perf_counter() - started < 5


# ---------------------------------------------------------------- API


def make_client(logged_in: bool = True) -> tuple[TestClient, RoomStore]:
    app = create_app(Settings(_env_file=None))
    fresh = store()
    app.dependency_overrides[get_room_store] = lambda: fresh
    if logged_in:
        app.dependency_overrides[current_user] = lambda: USER
    return TestClient(app), fresh


@pytest.fixture
def client() -> TestClient:
    return make_client()[0]


def test_open_a_room_vote_and_watch_it(client: TestClient) -> None:
    code = client.post("/api/v1/rooms").json()["code"]
    vote = {"voter": "phone-abc123", "chips": ["Happy", "happy", "calm"]}
    assert client.post(f"/api/v1/rooms/{code}/votes", json=vote).status_code == 204

    body = client.get(f"/api/v1/rooms/{code}").json()
    assert body["voters"] == 1
    assert body["points"][0]["labels"] == ["happy", "calm"]  # tidied and de-duplicated


@pytest.mark.parametrize(
    "vote",
    [
        {"voter": "phone-abc123", "chips": []},
        {"voter": "phone-abc123", "chips": ["a", "b", "c", "d"]},
        {"voter": "short", "chips": ["happy"]},
        {"voter": "<script>alert(1)</script>", "chips": ["happy"]},
        {"voter": "phone-abc123", "chips": ["happy"], "text": "anything"},
        {"voter": "phone-abc123", "chips": ["not-a-mood"]},
    ],
)
def test_only_mood_chips_from_the_list_are_accepted(client: TestClient, vote: dict) -> None:  # type: ignore[type-arg]
    code = client.post("/api/v1/rooms").json()["code"]
    assert client.post(f"/api/v1/rooms/{code}/votes", json=vote).status_code == 422


def test_wrong_codes(client: TestClient) -> None:
    assert client.get("/api/v1/rooms/ZZZZ").status_code == 404
    assert client.get("/api/v1/rooms/TOOLONG").status_code == 422
    vote = {"voter": "phone-abc123", "chips": ["happy"]}
    assert client.post("/api/v1/rooms/ZZZZ/votes", json=vote).status_code == 404


def test_a_class_on_one_wifi_is_not_rate_limited(client: TestClient) -> None:
    code = client.post("/api/v1/rooms").json()["code"]
    statuses = {
        client.post(
            f"/api/v1/rooms/{code}/votes", json={"voter": f"phone-{i:05d}", "chips": ["calm"]}
        ).status_code
        for i in range(NEW_VOTERS_PER_MINUTE)  # a big class, all on one Wi-Fi IP
    }
    assert statuses == {204}


def test_the_store_is_one_per_process() -> None:
    assert rooms_module.get_room_store() is rooms_module.get_room_store()


def test_only_logged_in_people_open_rooms_and_only_the_host_controls_them() -> None:
    anonymous, rooms = make_client(logged_in=False)
    assert anonymous.post("/api/v1/rooms").status_code in (401, 503)

    host, rooms = make_client()
    code = host.post("/api/v1/rooms").json()["code"]
    assert host.put(f"/api/v1/rooms/{code}/lock", json={"locked": True}).status_code == 204
    late = {"voter": "phone-late01", "chips": ["calm"]}
    assert host.post(f"/api/v1/rooms/{code}/votes", json=late).status_code == 409
    assert host.get(f"/api/v1/rooms/{code}").json()["locked"] is True
    assert host.delete(f"/api/v1/rooms/{code}/votes").status_code == 204
    assert host.put("/api/v1/rooms/ZZZZ/lock", json={"locked": False}).status_code == 404

    other = rooms.create("someone-else")
    assert host.delete(f"/api/v1/rooms/{other}/votes").status_code == 403
    assert anonymous.put(f"/api/v1/rooms/{code}/lock", json={"locked": False}).status_code in (
        401,
        503,
    )


def test_a_flood_of_fake_voters_gets_429_not_a_crash(client: TestClient) -> None:
    code = client.post("/api/v1/rooms").json()["code"]
    statuses = [
        client.post(
            f"/api/v1/rooms/{code}/votes", json={"voter": f"bot-{i:06d}", "chips": ["angry"]}
        ).status_code
        for i in range(NEW_VOTERS_PER_MINUTE + 20)
    ]
    assert statuses.count(204) == NEW_VOTERS_PER_MINUTE
    assert set(statuses[NEW_VOTERS_PER_MINUTE:]) == {429}
    assert client.get(f"/api/v1/rooms/{code}").status_code == 200
