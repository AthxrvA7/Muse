"""Wellbeing safeguard for free-text mood input.

Muse is not a health tool, but people type real feelings into a mood box.
If the text contains a phrase suggesting crisis or self-harm, the response
carries a short, kind notice with a helpline. The music is still returned:
Muse never blocks, diagnoses or lectures, and never stores or logs the text.

Known limits: phrase matching misses indirect wording and can trigger on song
lyrics or jokes. It is a safety net, not detection (docs/SECURITY_PRIVACY.md section 5).
"""

import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.schemas.mood import SupportNotice
from app.services.mood.vocabulary import KNOWLEDGE_DIR

SUPPORT_PATH = KNOWLEDGE_DIR / "support_phrases.json"


class SupportConfig(BaseModel):
    version: int
    about: str
    phrases: list[str]
    message: str
    resources: list[dict[str, str]]


def _normalise(text: str) -> str:
    text = text.lower().replace("’", "'")  # curly apostrophe -> straight
    return re.sub(r"\s+", " ", text)


class WellbeingCheck:
    def __init__(self, config: SupportConfig) -> None:
        self._notice = SupportNotice(message=config.message, resources=config.resources)
        alternatives = "|".join(re.escape(_normalise(p)) for p in config.phrases)
        self._pattern = re.compile(rf"\b(?:{alternatives})\b")

    def check(self, text: str | None) -> SupportNotice | None:
        if text and self._pattern.search(_normalise(text)):
            return self._notice
        return None


def load_wellbeing_check(path: Path = SUPPORT_PATH) -> WellbeingCheck:
    return WellbeingCheck(SupportConfig.model_validate_json(path.read_text(encoding="utf-8")))


@lru_cache
def get_wellbeing_check() -> WellbeingCheck:
    return load_wellbeing_check()
