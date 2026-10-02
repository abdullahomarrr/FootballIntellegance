"""HTTP routes for the current Premier League stats tier (public FPL feed)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx
import psycopg
from fastapi import APIRouter, HTTPException

from football_intelligence import fpl
from football_intelligence.name_search import name_score
from football_intelligence.repository import _query_all, database_url, person_member_ids

router = APIRouter()
_state: dict[str, Any] = {"built_at": 0.0, "snapshot": None, "links": {}}

SOURCE_NOTE = (
    "Unofficial public Fantasy Premier League feed (undocumented, no stated licence), cached for "
    "an hour. Totals, expected stats and availability only, no event locations. The FPL price is "
    "a game price, not a market value."
)


def current_snapshot() -> tuple[fpl.Snapshot, dict[int, tuple[int, str]]]:
    now = time.monotonic()
    if _state["snapshot"] is None or now - float(_state["built_at"]) > fpl.CACHE_SECONDS:
        snapshot = fpl.build_snapshot(fpl.fetch_bootstrap())
        links: dict[int, tuple[int, str]] = {}
        try:
            with psycopg.connect(database_url()) as connection:
                links = fpl.link_players(connection, snapshot.players)
                fpl.persist_links(connection, links)
        except psycopg.Error:
            links = {}
        _state.update(built_at=now, snapshot=snapshot, links=links)
    snapshot_value: fpl.Snapshot = _state["snapshot"]
    return snapshot_value, _state["links"]


def _feed_down() -> HTTPException:
    return HTTPException(status_code=503, detail="The Premier League feed is unavailable")


def reset_state() -> None:
    _state.update(built_at=0.0, snapshot=None, links={})


def _lite(player: dict[str, Any], links: dict[int, tuple[int, str]]) -> dict[str, Any]:
    linked = links.get(player["code"])
    return {
        "code": player["code"],
        "name": player["name"],
        "team": player["team"],
        "position_group": player["position_group"],
        "age": player["age"],
        "minutes": player["minutes"],
        "goals": player["goals"],
        "assists": player["assists"],
        "expected_goals": player["expected_goals"],
        "expected_assists": player["expected_assists"],
        "status": player["status"],
        "status_label": player["status_label"],
        "news": player["news"],
        "event_profile_player_id": linked[0] if linked else None,
    }


def _meta(snapshot: fpl.Snapshot, **extra: Any) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC),
        "source": "fpl_public_feed",
        "source_note": SOURCE_NOTE,
        "gameweek": snapshot.gameweek,
        "minimum_minutes_for_rankings": snapshot.minimum_minutes,
        **extra,
    }


@router.get("/fpl/players")
def list_fpl_players(search: str = "", limit: int = 20) -> dict[str, object]:
    try:
        snapshot, links = current_snapshot()
    except httpx.HTTPError as error:
        raise _feed_down() from error
    scored = [
        (name_score(search, f"{player['name']} {player['web_name']}"), player)
        for player in snapshot.players
    ]
    scored = [(score, player) for score, player in scored if score > 0]
    scored.sort(key=lambda item: (-item[0], -item[1]["minutes"], item[1]["name"]))
    matches = [player for _, player in scored]
    rows = [_lite(player, links) for player in matches[: max(1, min(limit, 50))]]
    return {"data": rows, "meta": _meta(snapshot, sample_size=len(rows))}


@router.get("/fpl/players/{code}")
def get_fpl_player(code: int) -> dict[str, object]:
    try:
        snapshot, links = current_snapshot()
    except httpx.HTTPError as error:
        raise _feed_down() from error
    player = next((p for p in snapshot.players if p["code"] == code), None)
    if player is None:
        raise HTTPException(status_code=404, detail="Not in the current Premier League feed")
    try:
        summary = fpl.fetch_summary(player["element_id"])
    except httpx.HTTPError:
        summary = {}
    return {
        "data": {
            **_lite(player, links),
            "legal_birth_date": player["birth_date"],
            "starts": player["starts"],
            "yellow_cards": player["yellow_cards"],
            "red_cards": player["red_cards"],
            "clean_sheets": player["clean_sheets"],
            "saves": player["saves"],
            "game_price": player["game_price"],
            "selected_by_percent": player["selected_by_percent"],
            "form": player["form"],
            "news_added": player["news_added"],
            "chance_of_playing": player["chance_of_playing"],
            "rankings": player.get("rankings", {}),
            "seasons": fpl.season_table(summary),
            "gameweeks": fpl.gameweek_table(summary),
            "link_basis": links[code][1] if code in links else None,
        },
        "meta": _meta(snapshot, summary_available=bool(summary)),
    }


@router.get("/players/{player_id}/availability")
def get_player_availability(player_id: int) -> dict[str, object]:
    ids = person_member_ids(player_id)
    rows = _query_all("SELECT fpl_code FROM bridge_player_fpl WHERE player_id = ANY(%s)", (ids,))
    if not rows:
        return {"data": None, "meta": {"status": "NOT_IN_CURRENT_PREMIER_LEAGUE_FEED"}}
    try:
        snapshot, _ = current_snapshot()
    except httpx.HTTPError:
        return {"data": None, "meta": {"status": "FEED_UNAVAILABLE"}}
    codes = {int(row["fpl_code"]) for row in rows}
    player = next((p for p in snapshot.players if p["code"] in codes), None)
    if player is None:
        return {"data": None, "meta": {"status": "NOT_IN_CURRENT_PREMIER_LEAGUE_FEED"}}
    return {
        "data": {
            "code": player["code"],
            "team": player["team"],
            "status": player["status"],
            "status_label": player["status_label"],
            "news": player["news"],
            "news_added": player["news_added"],
            "chance_of_playing": player["chance_of_playing"],
            "minutes": player["minutes"],
            "goals": player["goals"],
            "assists": player["assists"],
        },
        "meta": _meta(snapshot, status="AVAILABLE"),
    }
