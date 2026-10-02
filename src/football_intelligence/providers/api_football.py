from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel

BASE_URL = "https://v3.football.api-sports.io"


class APIFootballSeasonCoverage(BaseModel):
    league_id: int
    league_name: str
    country: str
    season: int
    current: bool
    coverage: dict[str, Any]
    checked_at: datetime
    quota_headers: dict[str, str]


class APIFootballAdapter:
    provider = "api_football"

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        if not api_key.strip():
            raise ValueError("API_FOOTBALL_KEY is required for authenticated discovery")
        self.client = client or httpx.Client(
            base_url=BASE_URL,
            headers={"x-apisports-key": api_key},
            timeout=30,
        )

    def discover_league(self, league_id: int) -> list[APIFootballSeasonCoverage]:
        response = self.client.get("/leagues", params={"id": league_id})
        response.raise_for_status()
        payload = response.json()
        quota_headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower().startswith("x-ratelimit-")
        }
        errors = payload.get("errors")
        if errors:
            raise RuntimeError(f"API-Football discovery failed: {errors}")
        rows = payload.get("response")
        if not isinstance(rows, list):
            raise ValueError("API-Football response must contain a response list")
        checked_at = datetime.now(UTC)
        results: list[APIFootballSeasonCoverage] = []
        for row in rows:
            league = row.get("league") or {}
            country = row.get("country") or {}
            for season in row.get("seasons") or []:
                results.append(
                    APIFootballSeasonCoverage(
                        league_id=int(league["id"]),
                        league_name=str(league["name"]),
                        country=str(country.get("name", "")),
                        season=int(season["year"]),
                        current=bool(season.get("current", False)),
                        coverage=dict(season.get("coverage") or {}),
                        checked_at=checked_at,
                        quota_headers=quota_headers,
                    )
                )
        return results
