"""Room mode: a class or a group shares its mood live (for presentations and parties)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.api.deps import CurrentUser
from app.schemas.rooms import LockIn, RoomCreated, RoomSummary, VoteIn
from app.services.mood.analyzer import UnknownChipError
from app.services.rooms import (
    NotHostError,
    RoomFullError,
    RoomLockedError,
    RoomNotFoundError,
    RoomStore,
    TooManyRoomsError,
    get_room_store,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])
Store = Annotated[RoomStore, Depends(get_room_store)]
Code = Annotated[str, Path(pattern=r"^[A-Za-z0-9]{4}$", description="The 4-character room code")]

NOT_FOUND = {"message": "No room with that code. Check the code on the screen."}


@router.post(
    "", status_code=status.HTTP_201_CREATED, summary="Open a room (logged in; lasts 4 hours)"
)
def create_room(user: CurrentUser, store: Store) -> RoomCreated:
    """Only logged-in users can open rooms; in Spotify's Development Mode that is the
    handful of allowlisted accounts, so an audience can't flood the server with rooms."""
    try:
        return RoomCreated(code=store.create(user.id))
    except TooManyRoomsError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Too many rooms are open right now; try again later."},
        ) from error


@router.post(
    "/{code}/votes",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add or change your mood in a room (up to 3 chips, no text, no login)",
)
def vote(code: Code, body: VoteIn, store: Store) -> Response:
    try:
        store.vote(code, body.voter, body.chips)
    except RoomNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from error
    except RoomLockedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "This room is closed to new people."},
        ) from error
    except RoomFullError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": "The room is busy or full. Try again in a minute."},
            headers={"Retry-After": "30"},
        ) from error
    except UnknownChipError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "allowed_chips": error.allowed},
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{code}", summary="The room's mood right now")
def room(code: Code, store: Store) -> RoomSummary:
    try:
        return store.summary(code)
    except RoomNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from error


def _host_action(action: Callable[[], None]) -> Response:
    try:
        action()
    except RoomNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from error
    except NotHostError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Only the person who opened the room can do this."},
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{code}/lock",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Host only: stop (or allow) new people joining",
)
def lock_room(code: Code, body: LockIn, user: CurrentUser, store: Store) -> Response:
    return _host_action(lambda: store.lock(code, user.id, body.locked))


@router.delete(
    "/{code}/votes", status_code=status.HTTP_204_NO_CONTENT, summary="Host only: clear the votes"
)
def reset_room(code: Code, user: CurrentUser, store: Store) -> Response:
    return _host_action(lambda: store.reset(code, user.id))
