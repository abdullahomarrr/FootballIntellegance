from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import BaseModel

BASE_URL = "https://www.thesportsdb.com/api/v1/json"


class SportsDBEvent(BaseModel):
    event_id: str
    name: str
    league_id: str | None
    league_name: str | None
    season: str | None
    home_team: str | None
    away_team: str | None
    date: str | None
    time: str | None
    status: str | None
    home_score: int | None
    away_score: int | None
    checked_at: datetime
    raw: dict[str, Any]


class SportsDBPlayer(BaseModel):
    player_id: str
    name: str
    team_name: str | None
    nationality: str | None
    birth_date: date | None
    status: str | None
    position: str | None
    checked_at: datetime
    raw_without_artwork: dict[str, Any]


class TheSportsDBAdapter:
    """Restricted secondary source using only documented v1 endpoints.

    The public key is intended for development/free-tier use. Do not ingest artwork here:
    its license and third-party rights must be verified per asset.
    """

    provider = "thesportsdb"

    def __init__(self, api_key: str = "123", client: httpx.Client | None = None) -> None:
        if not api_key.strip():
            raise ValueError("TheSportsDB API key cannot be empty")
        self.client = client or httpx.Client(
            base_url=f"{BASE_URL}/{api_key}", timeout=30, follow_redirects=True
        )

    def events_by_day(self, day: str, sport: str = "Soccer") -> list[SportsDBEvent]:
        response = self.client.get("/eventsday.php", params={"d": day, "s": sport})
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("events") if isinstance(payload, dict) else None
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise ValueError("TheSportsDB events payload must be a list or null")
        checked_at = datetime.now(UTC)
        return [self._normalize_event(row, checked_at) for row in rows]

    def search_players(self, name: str) -> list[SportsDBPlayer]:
        if not name.strip():
            raise ValueError("TheSportsDB player name cannot be empty")
        response = self.client.get("/searchplayers.php", params={"p": name})
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("player") if isinstance(payload, dict) else None
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise ValueError("TheSportsDB player payload must be a list or null")
        checked_at = datetime.now(UTC)
        results: list[SportsDBPlayer] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("idPlayer") or not row.get("strPlayer"):
                raise ValueError("TheSportsDB player requires idPlayer and strPlayer")
            safe_raw = {
                key: value
                for key, value in row.items()
                if key not in {"strThumb", "strCutout", "strFanart1", "strFanart2", "strFanart3"}
            }
            results.append(
                SportsDBPlayer(
                    player_id=str(row["idPlayer"]),
                    name=str(row["strPlayer"]),
                    team_name=row.get("strTeam"),
                    nationality=row.get("strNationality"),
                    birth_date=(
                        date.fromisoformat(str(row["dateBorn"])) if row.get("dateBorn") else None
                    ),
                    status=row.get("strStatus"),
                    position=row.get("strPosition"),
                    checked_at=checked_at,
                    raw_without_artwork=safe_raw,
                )
            )
        return results

    @staticmethod
    def _normalize_event(row: Any, checked_at: datetime) -> SportsDBEvent:
        if not isinstance(row, dict) or not row.get("idEvent"):
            raise ValueError("TheSportsDB event requires idEvent")

        def score(name: str) -> int | None:
            value = row.get(name)
            return int(str(value)) if value not in (None, "") else None

        return SportsDBEvent(
            event_id=str(row["idEvent"]),
            name=str(row.get("strEvent") or "Unknown event"),
            league_id=str(row["idLeague"]) if row.get("idLeague") else None,
            league_name=row.get("strLeague"),
            season=row.get("strSeason"),
            home_team=row.get("strHomeTeam"),
            away_team=row.get("strAwayTeam"),
            date=row.get("dateEvent"),
            time=row.get("strTime"),
            status=row.get("strStatus"),
            home_score=score("intHomeScore"),
            away_score=score("intAwayScore"),
            checked_at=checked_at,
            raw=dict(row),
        )
