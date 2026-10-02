from __future__ import annotations

import re
from dataclasses import dataclass

POSITION_ALIASES = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "centre back": "CB",
    "center back": "CB",
    "left back": "LB",
    "right back": "RB",
    "defensive midfielder": "DM",
    "central midfielder": "CM",
    "attacking midfielder": "AM",
    "winger": "WM",
    "striker": "ST",
    "forward": "FW",
}


@dataclass(frozen=True)
class ParsedScoutQuery:
    position: str | None
    maximum_age: int | None
    maximum_value_millions: float | None
    minimum_minutes: int | None
    traits: tuple[str, ...]
    unparsed_terms: tuple[str, ...]


def parse_scout_query(query: str) -> ParsedScoutQuery:
    normalized = " ".join(query.casefold().split())
    positions = [code for phrase, code in POSITION_ALIASES.items() if phrase in normalized]
    position = positions[0] if positions else None
    age_match = re.search(r"(?:under|younger than|max(?:imum)? age)\s+(\d{1,2})", normalized)
    value_match = re.search(
        r"(?:under|below|max(?:imum)?(?: value| fee| budget)?)"
        r"\s*[€£$]?\s*(\d+(?:\.\d+)?)\s*m(?:illion)?",
        normalized,
    )
    minutes_match = re.search(r"(?:at least|min(?:imum)?)\s+(\d{2,5})\s+minutes", normalized)
    known_traits = ("pressing", "passing", "dribbling", "carrying", "finishing", "aerial")
    traits = tuple(trait for trait in known_traits if trait in normalized)
    recognized = bool(position or age_match or value_match or minutes_match or traits)
    return ParsedScoutQuery(
        position=position,
        maximum_age=int(age_match.group(1)) if age_match else None,
        maximum_value_millions=float(value_match.group(1)) if value_match else None,
        minimum_minutes=int(minutes_match.group(1)) if minutes_match else None,
        traits=traits,
        unparsed_terms=() if recognized else (query.strip(),),
    )
