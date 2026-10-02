from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


def normalize_team_name(value: str) -> str:
    value = re.sub(
        r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match.group(1), 16)), value
    )
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    words = re.sub(r"[^a-z0-9]+", " ", normalized).split()
    # The current StatsBomb catalogue contains replacement-character mojibake for a few
    # Spanish accents. Keep the repair list explicit rather than applying fuzzy matching.
    mojibake_repairs = {
        "alavs": "alaves",
        "atltico": "atletico",
        "corua": "coruna",
        "legans": "leganes",
        "mlaga": "malaga",
    }
    words = [mojibake_repairs.get(word, word) for word in words]
    removable = {"cf", "fc", "rc", "ud"}
    words = [word for word in words if word not in removable]
    if words == ["celta", "de", "vigo"]:
        words = ["celta", "vigo"]
    if words == ["deportivo", "la", "coruna"]:
        words = ["deportivo", "coruna"]
    return " ".join(words)


@dataclass(frozen=True, slots=True)
class MatchFact:
    provider_match_id: str
    match_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int

    @property
    def match_key(self) -> tuple[str, str, str]:
        return (
            self.match_date,
            normalize_team_name(self.home_team),
            normalize_team_name(self.away_team),
        )


def statsbomb_match_facts(matches: list[dict[str, Any]]) -> list[MatchFact]:
    return [
        MatchFact(
            provider_match_id=str(match["match_id"]),
            match_date=str(match["match_date"]),
            home_team=str(match["home_team"]["home_team_name"]),
            away_team=str(match["away_team"]["away_team_name"]),
            home_score=int(match["home_score"]),
            away_score=int(match["away_score"]),
        )
        for match in matches
    ]


def wyscout_match_facts(
    matches: list[dict[str, Any]], teams: list[dict[str, Any]]
) -> list[MatchFact]:
    names = {str(team["wyId"]): str(team["name"]) for team in teams}
    facts: list[MatchFact] = []
    for match in matches:
        by_side = {str(data["side"]): data for data in match["teamsData"].values()}
        home, away = by_side["home"], by_side["away"]
        facts.append(
            MatchFact(
                provider_match_id=str(match["wyId"]),
                match_date=datetime.fromisoformat(str(match["dateutc"])).date().isoformat(),
                home_team=names[str(home["teamId"])],
                away_team=names[str(away["teamId"])],
                home_score=int(home["score"]),
                away_score=int(away["score"]),
            )
        )
    return facts


def compare_match_facts(
    left_provider: str,
    left: list[MatchFact],
    right_provider: str,
    right: list[MatchFact],
) -> dict[str, Any]:
    right_by_key = {fact.match_key: fact for fact in right}
    overlaps: list[dict[str, Any]] = []
    score_mismatches: list[dict[str, Any]] = []
    for left_fact in left:
        right_fact = right_by_key.get(left_fact.match_key)
        if right_fact is None:
            continue
        score_matches = (left_fact.home_score, left_fact.away_score) == (
            right_fact.home_score,
            right_fact.away_score,
        )
        row = {
            left_provider: asdict(left_fact),
            right_provider: asdict(right_fact),
            "match_date_matches": left_fact.match_date == right_fact.match_date,
            "clubs_match_after_normalization": True,
            "score_matches": score_matches,
        }
        overlaps.append(row)
        if not score_matches:
            score_mismatches.append(row)
    return {
        "left_provider": left_provider,
        "right_provider": right_provider,
        "left_matches": len(left),
        "right_matches": len(right),
        "overlapping_matches": len(overlaps),
        "match_date_agreements": sum(row["match_date_matches"] for row in overlaps),
        "club_agreements": sum(row["clubs_match_after_normalization"] for row in overlaps),
        "score_agreements": sum(row["score_matches"] for row in overlaps),
        "score_mismatches": score_mismatches,
        "overlaps": overlaps,
        "method": (
            "Match on calendar date plus normalized ordered home/away clubs; compare final scores. "
            "Neither source is designated authoritative when values differ."
        ),
    }
