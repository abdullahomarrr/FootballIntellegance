"""Current-season FotMob data for a player's main profile page (personal use, see
docs/data_sources/fotmob-pages.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter

from football_intelligence import fotmob
from football_intelligence.repository import _query_all, person_member_ids

router = APIRouter()

NOTE = (
    "Current-season numbers, heat map and shot map read from FotMob's public pages for local "
    "personal use, cached for a day. Player and club are linked by birth date or exact name plus "
    "club. These are not the open event data the rest of this profile is built on."
)


def _meta(**extra: Any) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC),
        "source": "fotmob_public_pages",
        "source_note": NOTE,
        **extra,
    }


@router.get("/players/{player_id}/current-season")
def get_current_season(player_id: int) -> dict[str, object]:
    ids = person_member_ids(player_id)
    linked = _query_all(
        """
        SELECT b.fotmob_id, b.link_basis, m.team_id, t.name AS team_name, t.league_name,
               t.season, m.position_group, m.role, m.injured, m.injury_return,
               m.market_value_eur
        FROM bridge_player_fotmob b
        JOIN fotmob_squad_member m ON m.player_id = b.fotmob_id
        JOIN fotmob_team t ON t.team_id = m.team_id
        WHERE b.player_id = ANY(%s)
        ORDER BY (b.link_basis LIKE 'BIRTH_DATE%%') DESC, b.fotmob_id
        LIMIT 1
        """,
        (ids,),
    )
    if not linked:
        return {"data": None, "meta": _meta(status="NOT_IN_CURRENT_TOP_FIVE_SQUADS")}
    link = linked[0]
    try:
        profile = fotmob.fetch_player(int(link["fotmob_id"]))
    except (httpx.HTTPError, fotmob.FotmobError):
        return {"data": None, "meta": _meta(status="FOTMOB_UNAVAILABLE")}
    return {
        "data": {**profile, "squad": link},
        "meta": _meta(status="AVAILABLE", link_basis=link["link_basis"]),
    }
