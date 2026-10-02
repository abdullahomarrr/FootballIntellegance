"""HTTP routes for the current La Liga stats tier (free Big Ball Sports API tier)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx
import psycopg
from fastapi import APIRouter, HTTPException

from football_intelligence import laliga
from football_intelligence.name_search import name_score
from football_intelligence.repository import database_url

router = APIRouter()
_state: dict[str, Any] = {"built_at": 0.0, "snapshot": None, "links": {}}

SOURCE_NOTE = (
    "Free tier of the Big Ball Sports API, current season only. Totals and per-90 rates are summed "
    "from each finished match's player lines. Pass completion divides the feed's completed-pass "
    "count by total passes. There are no event locations and no expected stats, and the feed has "
    "no birth dates, so links to older event profiles rely on exact name plus club."
)


def current_snapshot() -> tuple[laliga.Snapshot, dict[str, tuple[int, str]]]:
    now = time.monotonic()
    if _state["snapshot"] is None or now - float(_state["built_at"]) > laliga.MATCH_LIST_SECONDS:
        snapshot = laliga.load_snapshot()
        links: dict[str, tuple[int, str]] = {}
        try:
            with psycopg.connect(database_url()) as connection:
                links = laliga.link_players(connection, snapshot.players)
        except psycopg.Error:
            links = {}
        _state.update(built_at=now, snapshot=snapshot, links=links)
    snapshot_value: laliga.Snapshot = _state["snapshot"]
    return snapshot_value, _state["links"]


def reset_state() -> None:
    _state.update(built_at=0.0, snapshot=None, links={})


def _unavailable(error: Exception) -> HTTPException:
    if isinstance(error, laliga.MissingApiKey):
        return HTTPException(status_code=503, detail="The La Liga feed is not configured")
    return HTTPException(status_code=503, detail="The La Liga feed is unavailable")


def _lite(player: dict[str, Any], links: dict[str, tuple[int, str]]) -> dict[str, Any]:
    linked = links.get(player["id"])
    return {
        "id": player["id"],
        "name": player["name"],
        "team": player["team"],
        "club_unclear": player["club_unclear"],
        "feed_club": player["feed_club"],
        "position_group": player["position_group"],
        "minutes": player["minutes"],
        "appearances": player["appearances"],
        "goals": player["goals"],
        "assists": player["assists"],
        "average_rating": player["average_rating"],
        "event_profile_player_id": linked[0] if linked else None,
    }


def _meta(snapshot: laliga.Snapshot, **extra: Any) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC),
        "source": "bigballsdata_free_tier",
        "source_note": SOURCE_NOTE,
        "season": snapshot.season_label,
        "matches_covered": snapshot.matches,
        "minimum_minutes_for_rankings": snapshot.minimum_minutes,
        **extra,
    }


@router.get("/laliga/players")
def list_laliga_players(search: str = "", limit: int = 20) -> dict[str, object]:
    try:
        snapshot, links = current_snapshot()
    except (httpx.HTTPError, laliga.MissingApiKey) as error:
        raise _unavailable(error) from error
    scored = [(name_score(search, p["name"]), p) for p in snapshot.players]
    scored = [(score, p) for score, p in scored if score > 0]
    scored.sort(key=lambda item: (-item[0], -item[1]["minutes"], item[1]["name"]))
    matches = [p for _, p in scored]
    rows = [_lite(player, links) for player in matches[: max(1, min(limit, 50))]]
    return {"data": rows, "meta": _meta(snapshot, sample_size=len(rows))}


@router.get("/laliga/players/{feed_id}")
def get_laliga_player(feed_id: str) -> dict[str, object]:
    try:
        snapshot, links = current_snapshot()
    except (httpx.HTTPError, laliga.MissingApiKey) as error:
        raise _unavailable(error) from error
    player = next((p for p in snapshot.players if p["id"] == feed_id), None)
    if player is None:
        raise HTTPException(status_code=404, detail="Not in the current La Liga feed")
    return {
        "data": {
            **_lite(player, links),
            "starts": player["starts"],
            "shots": player["shots"],
            "shots_on_target": player["shots_on_target"],
            "key_passes": player["key_passes"],
            "passes": player["passes"],
            "pass_completion": player["pass_completion"],
            "tackles": player["tackles"],
            "interceptions": player["interceptions"],
            "saves": player["saves"],
            "yellow_cards": player["yellow_cards"],
            "red_cards": player["red_cards"],
            "rankings": player["rankings"],
            "link_basis": links[feed_id][1] if feed_id in links else None,
        },
        "meta": _meta(snapshot),
    }
