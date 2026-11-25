"""The logged-in user's taste profile and Music DNA (Classics: "Know your music")."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, PreferencesRepo
from app.schemas.preferences import MusicDNA, PreferencesIn, PreferencesOut
from app.services.curate import UnknownTasteError
from app.services.preferences import check_known, music_dna, to_document
from app.services.recommender.knowledge import get_genre_knowledge

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", summary="Your saved taste profile")
async def get_preferences(user: CurrentUser, repo: PreferencesRepo) -> PreferencesOut:
    saved = await repo.get(user.id)
    return PreferencesOut(**saved.model_dump(exclude={"user_id"})) if saved else PreferencesOut()


@router.put("", summary="Save your taste profile (replaces the previous one)")
async def save_preferences(
    body: PreferencesIn, user: CurrentUser, repo: PreferencesRepo
) -> PreferencesOut:
    try:
        check_known(body, get_genre_knowledge())
    except UnknownTasteError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "hint": "See GET /api/v1/curate/options"},
        ) from error
    document = to_document(user.id, body)
    await repo.save(document)
    return PreferencesOut(**document.model_dump(exclude={"user_id"}))


@router.get("/dna", summary="Music DNA: a summary of your stated taste")
async def get_music_dna(user: CurrentUser, repo: PreferencesRepo) -> MusicDNA:
    return music_dna(await repo.get(user.id), get_genre_knowledge())
