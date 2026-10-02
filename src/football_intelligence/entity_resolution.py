from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).split())


@dataclass(frozen=True, slots=True)
class PlayerIdentity:
    provider: str
    provider_player_id: str
    name: str
    birth_date: date | None = None
    nationality: str | None = None
    team: str | None = None
    position: str | None = None
    height_cm: int | None = None


@dataclass(frozen=True, slots=True)
class MatchDecision:
    score: float
    method: str
    auto_link: bool
    signals: tuple[str, ...]


def compare_players(left: PlayerIdentity, right: PlayerIdentity) -> MatchDecision:
    left_name = normalize_name(left.name)
    right_name = normalize_name(right.name)
    name_similarity = SequenceMatcher(None, left_name, right_name).ratio()
    signals: list[str] = []
    score = name_similarity * 0.35

    exact_dob = left.birth_date is not None and left.birth_date == right.birth_date
    conflicting_dob = (
        left.birth_date is not None
        and right.birth_date is not None
        and left.birth_date != right.birth_date
    )
    if exact_dob:
        score += 0.45
        signals.append("exact_birth_date")
    if conflicting_dob:
        return MatchDecision(0.0, "conflicting_birth_date", False, ("conflicting_birth_date",))
    if left_name == right_name:
        signals.append("exact_normalized_name")
    elif name_similarity >= 0.9:
        signals.append("fuzzy_name")

    for attribute, weight in (("nationality", 0.08), ("team", 0.07), ("position", 0.03)):
        left_value = getattr(left, attribute)
        right_value = getattr(right, attribute)
        if left_value and right_value and normalize_name(left_value) == normalize_name(right_value):
            score += weight
            signals.append(f"same_{attribute}")
    if left.height_cm and right.height_cm and abs(left.height_cm - right.height_cm) <= 1:
        score += 0.02
        signals.append("compatible_height")

    score = min(round(score, 4), 1.0)
    auto_link = exact_dob and name_similarity >= 0.9 and score >= 0.82
    method = "deterministic_dob_name" if auto_link else "review_required"
    return MatchDecision(score, method, auto_link, tuple(signals))
