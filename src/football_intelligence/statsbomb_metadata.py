from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

COMPETITION_ALIASES = {
    "1. Bundesliga": "German first division",
    "La Liga": "Spanish first division",
    "Ligue 1": "French first division",
    "Premier League": "English first division",
    "Serie A": "Italian first division",
}


def normalize_statsbomb_season_label(label: str) -> str:
    parts = label.split("/")
    if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 4:
        return f"{parts[0]}/{parts[1][-2:]}"
    return label


def load_statsbomb_match_metadata(cursor: Any, match: dict[str, Any]) -> int:
    provider = "statsbomb_open"
    provider_match_id = str(match["match_id"])
    cursor.execute(
        "SELECT match_id FROM bridge_match_provider WHERE provider=%s AND provider_match_id=%s",
        (provider, provider_match_id),
    )
    existing = cursor.fetchone()
    if existing:
        return int(existing[0])

    team_ids: dict[str, int] = {}
    for side in ("home_team", "away_team"):
        team = match[side]
        provider_team_id = str(team[f"{side.removesuffix('_team')}_team_id"])
        provider_name = str(team[f"{side.removesuffix('_team')}_team_name"])
        cursor.execute(
            """SELECT team_id FROM bridge_team_provider
               WHERE provider=%s AND provider_team_id=%s AND valid_to IS NULL""",
            (provider, provider_team_id),
        )
        row = cursor.fetchone()
        if row:
            team_ids[side] = int(row[0])
            continue
        cursor.execute(
            "SELECT team_id FROM dim_team WHERE lower(canonical_name)=lower(%s) ORDER BY team_id",
            (provider_name,),
        )
        exact = cursor.fetchall()
        if len(exact) == 1:
            team_id = int(exact[0][0])
            confidence, method = 0.95, "exact_name_cross_provider"
        else:
            cursor.execute(
                """INSERT INTO dim_team (canonical_name,country_code,team_type)
                   VALUES (%s,%s,'CLUB') RETURNING team_id""",
                (provider_name, (team.get("country") or {}).get("name")),
            )
            team_id = int(cursor.fetchone()[0])
            confidence, method = 1.0, "provider_seed"
        cursor.execute(
            """INSERT INTO bridge_team_provider
               (team_id,provider,provider_team_id,provider_name,confidence,match_method)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (team_id, provider, provider_team_id, provider_name, confidence, method),
        )
        team_ids[side] = team_id

    competition = match["competition"]
    provider_competition_id = str(competition["competition_id"])
    cursor.execute(
        """SELECT competition_id FROM bridge_competition_provider
           WHERE provider=%s AND provider_competition_id=%s""",
        (provider, provider_competition_id),
    )
    row = cursor.fetchone()
    if row:
        competition_id = int(row[0])
    else:
        canonical_name = COMPETITION_ALIASES.get(
            str(competition["competition_name"]), str(competition["competition_name"])
        )
        cursor.execute(
            "SELECT competition_id FROM dim_competition WHERE canonical_name=%s",
            (canonical_name,),
        )
        found = cursor.fetchone()
        if found:
            competition_id = int(found[0])
        else:
            cursor.execute(
                """INSERT INTO dim_competition (canonical_name,country_code,competition_type)
                   VALUES (%s,%s,'LEAGUE') RETURNING competition_id""",
                (canonical_name, competition.get("country_name")),
            )
            competition_id = int(cursor.fetchone()[0])
        cursor.execute(
            "INSERT INTO bridge_competition_provider VALUES (%s,%s,%s,%s)",
            (
                competition_id,
                provider,
                provider_competition_id,
                competition["competition_name"],
            ),
        )

    season = match["season"]
    provider_season_id = str(season["season_id"])
    cursor.execute(
        "SELECT season_id FROM bridge_season_provider WHERE provider=%s AND provider_season_id=%s",
        (provider, provider_season_id),
    )
    row = cursor.fetchone()
    if row:
        season_id = int(row[0])
    else:
        label = normalize_statsbomb_season_label(str(season["season_name"]))
        cursor.execute(
            """INSERT INTO dim_season (label,status,data_as_of)
               VALUES (%s,'FINAL',now())
               ON CONFLICT (label) DO UPDATE SET data_as_of=EXCLUDED.data_as_of
               RETURNING season_id""",
            (label,),
        )
        season_id = int(cursor.fetchone()[0])
        cursor.execute(
            "INSERT INTO bridge_season_provider VALUES (%s,%s,%s)",
            (season_id, provider, provider_season_id),
        )

    kickoff = datetime.fromisoformat(f"{match['match_date']}T{match['kick_off']}").replace(
        tzinfo=UTC
    )
    cursor.execute(
        """INSERT INTO dim_match (
               competition_id,season_id,home_team_id,away_team_id,kickoff_at,status,
               home_score,away_score,data_as_of
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now()) RETURNING match_id""",
        (
            competition_id,
            season_id,
            team_ids["home_team"],
            team_ids["away_team"],
            kickoff,
            str(match.get("match_status") or "available").upper(),
            match.get("home_score"),
            match.get("away_score"),
        ),
    )
    match_id = int(cursor.fetchone()[0])
    cursor.execute(
        "INSERT INTO bridge_match_provider VALUES (%s,%s,%s,%s)",
        (match_id, provider, provider_match_id, f"{match['match_date']}"),
    )
    return match_id


def link_statsbomb_events(cursor: Any, provider_match_id: str) -> tuple[int, int, int]:
    cursor.execute(
        """UPDATE fact_event event SET match_id=bridge.match_id
           FROM bridge_match_provider bridge
           WHERE event.provider=bridge.provider
             AND event.provider_match_id=bridge.provider_match_id
             AND event.provider=%s AND event.provider_match_id=%s""",
        ("statsbomb_open", provider_match_id),
    )
    match_linked = cursor.rowcount
    cursor.execute(
        """UPDATE fact_event event SET team_id=bridge.team_id
           FROM bridge_team_provider bridge
           WHERE event.provider=bridge.provider
             AND event.provider_team_id=bridge.provider_team_id
             AND event.provider=%s AND event.provider_match_id=%s
             AND bridge.valid_to IS NULL""",
        ("statsbomb_open", provider_match_id),
    )
    team_linked = cursor.rowcount
    cursor.execute(
        """UPDATE fact_event event SET player_id=bridge.player_id
           FROM bridge_player_provider bridge
           WHERE event.provider=bridge.provider
             AND event.provider_player_id=bridge.provider_player_id
             AND event.provider=%s AND event.provider_match_id=%s
             AND bridge.valid_to IS NULL""",
        ("statsbomb_open", provider_match_id),
    )
    return match_linked, team_linked, cursor.rowcount
