from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel

COMPETITIONS_URL = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json"
)
MATCHES_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/{competition_id}/{season_id}.json"
EVENTS_URL = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json"
)
LINEUPS_URL = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{match_id}.json"
)


class StatsBombCompetitionSeason(BaseModel):
    competition_id: int
    season_id: int
    country_name: str
    competition_name: str
    season_name: str
    match_updated: datetime
    match_available_360: datetime | None = None


class StatsBombCoverage(BaseModel):
    competition: StatsBombCompetitionSeason
    match_count: int
    checked_at: datetime


class StatsBombOpenAdapter:
    provider = "statsbomb_open"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30, follow_redirects=True)

    def fetch_catalogue(self) -> list[dict[str, Any]]:
        response = self.client.get(COMPETITIONS_URL)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("StatsBomb competition catalogue must be a list")
        return payload

    def discover_big_five(self) -> list[StatsBombCoverage]:
        names = {"Premier League", "La Liga", "1. Bundesliga", "Serie A", "Ligue 1"}
        results: list[StatsBombCoverage] = []
        checked_at = datetime.now(UTC)
        for item in self.fetch_catalogue():
            competition = StatsBombCompetitionSeason.model_validate(item)
            if competition.competition_name not in names:
                continue
            response = self.client.get(
                MATCHES_URL.format(
                    competition_id=competition.competition_id,
                    season_id=competition.season_id,
                )
            )
            response.raise_for_status()
            matches = response.json()
            if not isinstance(matches, list):
                raise ValueError("StatsBomb matches payload must be a list")
            results.append(
                StatsBombCoverage(
                    competition=competition,
                    match_count=len(matches),
                    checked_at=checked_at,
                )
            )
        return results

    def fetch_matches(self, competition_id: int, season_id: int) -> list[dict[str, Any]]:
        response = self.client.get(
            MATCHES_URL.format(competition_id=competition_id, season_id=season_id)
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("StatsBomb matches payload must be a list")
        return payload

    def fetch_events(self, match_id: int) -> list[dict[str, Any]]:
        response = self.client.get(EVENTS_URL.format(match_id=match_id))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("StatsBomb events payload must be a list")
        for event in payload:
            event.setdefault("match_id", match_id)
        return payload

    def fetch_lineups(self, match_id: int) -> list[dict[str, Any]]:
        response = self.client.get(LINEUPS_URL.format(match_id=match_id))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("StatsBomb lineups payload must be a list")
        return payload
