"""Routes for current top-five-league squads, player pages and the alternatives finder."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from football_intelligence import alternatives, fotmob
from football_intelligence.head_to_head import head_to_head
from football_intelligence.lineup import build_lineup
from football_intelligence.name_search import name_score
from football_intelligence.repository import _query_all, similar_players

router = APIRouter()

SOURCE_NOTE = (
    "Squads and player pages are read from FotMob's public web pages for local, personal use "
    "(FotMob has no public API and its terms do not allow scraping), cached for a day. "
    "Remove this source before any public deployment."
)
ALTERNATIVES_NOTE = (
    "Similarity compares this season's per-90 numbers within one role family, re-ranked across "
    "every cached top-five-league player. An upgrade is a similar player who ranks higher overall "
    "on those numbers. This describes measured output, not how a player would perform in another "
    "team or system, and early-season samples are small."
)


def _meta(**extra: Any) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC),
        "source": "fotmob_public_pages",
        "source_note": SOURCE_NOTE,
        **extra,
    }


@router.get("/squads/leagues")
def list_squad_leagues() -> dict[str, object]:
    rows = _query_all(
        """
        SELECT t.league_id, t.league_name, t.season, t.team_id, t.name AS team_name,
               count(m.player_id) AS players
        FROM fotmob_team t
        LEFT JOIN fotmob_squad_member m ON m.team_id = t.team_id
        GROUP BY t.league_id, t.league_name, t.season, t.team_id, t.name
        ORDER BY t.league_name, t.name
        """,
        (),
    )
    leagues: dict[int, dict[str, Any]] = {}
    for row in rows:
        league = leagues.setdefault(
            int(row["league_id"]),
            {
                "league_id": int(row["league_id"]),
                "league_name": row["league_name"],
                "season": row["season"],
                "teams": [],
            },
        )
        league["teams"].append(
            {
                "team_id": int(row["team_id"]),
                "name": row["team_name"],
                "players": int(row["players"]),
            }
        )
    order = {name: i for i, (name, _slug) in enumerate(fotmob.LEAGUES.values())}
    data = sorted(leagues.values(), key=lambda league: order.get(league["league_name"], 99))
    return {"data": data, "meta": _meta(teams=len(rows))}


@router.get("/squads/teams/{team_id}")
def get_squad(team_id: int) -> dict[str, object]:
    teams = _query_all(
        "SELECT team_id, name, league_id, league_name, season FROM fotmob_team WHERE team_id = %s",
        (team_id,),
    )
    if not teams:
        raise HTTPException(status_code=404, detail="Unknown club")
    members = _query_all(
        """
        SELECT m.player_id, m.name, m.position_group, m.role, m.position_codes, m.shirt_number,
               m.nationality, m.birth_date, m.age, m.height_cm, m.market_value_eur, m.injured,
               m.injury_return, m.rating, m.goals, m.assists,
               b.player_id AS event_profile_player_id
        FROM fotmob_squad_member m
        LEFT JOIN bridge_player_fotmob b ON b.fotmob_id = m.player_id
        WHERE m.team_id = %s
        ORDER BY CASE m.position_group WHEN 'GK' THEN 1 WHEN 'DF' THEN 2 WHEN 'MD' THEN 3
                 ELSE 4 END, m.shirt_number NULLS LAST, m.name
        """,
        (team_id,),
    )
    pool = alternatives.load_pool()
    for member in members:
        entry = pool.entries.get(int(member["player_id"]))
        member["minutes"] = int(entry.minutes) if entry is not None else None
        member["current_stats_cached"] = (
            entry is not None and entry.minutes >= alternatives.MIN_MINUTES
        )
    return {
        "data": {**teams[0], "players": members, "lineup": build_lineup(members)},
        "meta": _meta(
            sample_size=len(members),
            lineup_note=(
                "Estimated from minutes played this season and listed positions. It shows who has "
                "played most, not an official team sheet."
            ),
        ),
    }


@router.get("/squads/players/{player_id}")
def get_squad_player(player_id: int) -> dict[str, object]:
    try:
        profile = fotmob.fetch_player(player_id)
    except (httpx.HTTPError, fotmob.FotmobError) as error:
        raise HTTPException(status_code=503, detail="The FotMob page is unavailable") from error
    squad = _query_all(
        """
        SELECT m.team_id, t.name AS team_name, t.league_name, m.position_group, m.role,
               m.nationality, m.age, m.market_value_eur, m.injured, m.injury_return,
               b.player_id AS event_profile_player_id, b.link_basis
        FROM fotmob_squad_member m
        JOIN fotmob_team t ON t.team_id = m.team_id
        LEFT JOIN bridge_player_fotmob b ON b.fotmob_id = m.player_id
        WHERE m.player_id = %s
        """,
        (player_id,),
    )
    return {
        "data": {**profile, "squad": squad[0] if squad else None},
        "meta": _meta(),
    }


@router.get("/squads/players/{player_id}/alternatives")
def get_alternatives(
    player_id: int, limit: int = 8, max_value_eur: float | None = None
) -> dict[str, object]:
    try:
        fotmob.fetch_player(player_id)  # the clicked player is always read, however the pool is
    except (httpx.HTTPError, fotmob.FotmobError) as error:
        raise HTTPException(status_code=503, detail="The FotMob page is unavailable") from error
    pool = alternatives.load_pool()
    result = alternatives.alternatives(pool, player_id, max(1, min(limit, 20)), max_value_eur)
    linked = _query_all(
        "SELECT player_id FROM bridge_player_fotmob WHERE fotmob_id = %s", (player_id,)
    )
    event_similar: list[dict[str, Any]] = []
    if linked:
        event_similar = similar_players(int(linked[0]["player_id"]), limit=6)
    return {
        "data": {**result, "event_similar": event_similar},
        "meta": _meta(
            alternatives_note=ALTERNATIVES_NOTE,
            profiles_in_pool=len(pool.entries),
        ),
    }


@router.get("/squads/search")
def search_current_players(q: str = "", limit: int = 8) -> dict[str, object]:
    """Typo-tolerant name search across every cached top-five-league squad."""
    if len(q.strip()) < 2:
        return {"data": [], "meta": _meta(sample_size=0)}
    members = _query_all(
        """
        SELECT m.player_id, m.name, m.position_group, m.role, m.age, m.market_value_eur,
               m.team_id, t.name AS team, t.league_name
        FROM fotmob_squad_member m
        JOIN fotmob_team t ON t.team_id = m.team_id
        """,
        (),
    )
    scored = [(name_score(q, str(m["name"])), m) for m in members]
    pool = alternatives.load_pool()
    ranked = sorted(
        ((score, m) for score, m in scored if score > 0),
        key=lambda item: (
            -item[0],
            -(
                pool.entries[int(item[1]["player_id"])].minutes
                if int(item[1]["player_id"]) in pool.entries
                else 0
            ),
        ),
    )
    rows = [m for _, m in ranked[: max(1, min(limit, 20))]]
    return {"data": rows, "meta": _meta(sample_size=len(rows))}


@router.get("/compare/current")
def compare_current(a: int, b: int) -> dict[str, object]:
    """Head-to-head of two current players, each ranked within their own role family."""
    if a == b:
        raise HTTPException(status_code=422, detail="Choose two different players")
    try:
        profile_a = fotmob.fetch_player(a)
        profile_b = fotmob.fetch_player(b)
    except (httpx.HTTPError, fotmob.FotmobError) as error:
        raise HTTPException(status_code=503, detail="The FotMob page is unavailable") from error
    pool = alternatives.load_pool()
    return {
        "data": head_to_head(pool, profile_a, profile_b),
        "meta": _meta(
            method_note=(
                "Per-90 numbers this season. Each stat is ranked against every cached "
                "top-five-league player in the same role family, so percentiles are comparable "
                "across leagues. A stat is called even when the rankings are within 5 points."
            ),
            profiles_in_pool=len(pool.entries),
        ),
    }
