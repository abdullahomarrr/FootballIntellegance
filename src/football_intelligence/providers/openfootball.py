from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"


class OpenFootballScore(BaseModel):
    full_time: tuple[int, int] | None = None
    half_time: tuple[int, int] | None = None


class OpenFootballFixture(BaseModel):
    provider_match_key: str
    competition_code: str
    season: str
    round_name: str | None = None
    match_date: date
    kickoff_time: str | None = None
    home_team: str
    away_team: str
    score: OpenFootballScore
    status: str
    source_url: str
    data_as_of: datetime


class OpenFootballDataset(BaseModel):
    provider: str = "openfootball"
    name: str
    competition_code: str
    season: str
    license: str = "CC0-1.0"
    source_url: str
    checked_at: datetime
    fixtures: list[OpenFootballFixture] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)


class OpenFootballAdapter:
    """Read the credential-free OpenFootball JSON exports.

    Competition codes are filenames from the upstream season directory (for example
    ``en.1``). They are configuration, not guessed league-name mappings.
    """

    provider = "openfootball"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30, follow_redirects=True)

    def fetch_competition(self, season: str, competition_code: str) -> OpenFootballDataset:
        if not season or "/" in season or ".." in season:
            raise ValueError("season must be an OpenFootball season directory such as 2026-27")
        if not competition_code or "/" in competition_code or ".." in competition_code:
            raise ValueError("competition_code must be an OpenFootball JSON filename stem")
        source_url = f"{BASE_URL}/{season}/{competition_code}.json"
        response = self.client.get(source_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
            raise ValueError("OpenFootball payload must contain a matches list")

        checked_at = datetime.now(UTC)
        fixtures = [
            self._normalize_match(item, season, competition_code, source_url, checked_at)
            for item in payload["matches"]
        ]
        return OpenFootballDataset(
            name=str(payload.get("name") or competition_code),
            competition_code=competition_code,
            season=season,
            source_url=source_url,
            checked_at=checked_at,
            fixtures=fixtures,
            raw_payload=payload,
        )

    @staticmethod
    def _normalize_match(
        item: Any,
        season: str,
        competition_code: str,
        source_url: str,
        checked_at: datetime,
    ) -> OpenFootballFixture:
        if not isinstance(item, dict):
            raise ValueError("OpenFootball match entries must be objects")
        match_date = date.fromisoformat(str(item["date"]))
        home = str(item["team1"]).strip()
        away = str(item["team2"]).strip()
        if not home or not away:
            raise ValueError("OpenFootball teams must be non-empty")
        raw_score = item.get("score")
        full_time = OpenFootballAdapter._score_pair(raw_score, "ft")
        half_time = OpenFootballAdapter._score_pair(raw_score, "ht")
        return OpenFootballFixture(
            provider_match_key=f"{season}:{competition_code}:{match_date}:{home}:{away}",
            competition_code=competition_code,
            season=season,
            round_name=str(item["round"]) if item.get("round") is not None else None,
            match_date=match_date,
            kickoff_time=str(item["time"]) if item.get("time") else None,
            home_team=home,
            away_team=away,
            score=OpenFootballScore(full_time=full_time, half_time=half_time),
            status="FINISHED" if full_time is not None else "SCHEDULED",
            source_url=source_url,
            data_as_of=checked_at,
        )

    @staticmethod
    def _score_pair(raw_score: Any, key: str) -> tuple[int, int] | None:
        if not isinstance(raw_score, dict) or raw_score.get(key) is None:
            return None
        value = raw_score[key]
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError(f"OpenFootball score.{key} must be a two-item list")
        return int(value[0]), int(value[1])
