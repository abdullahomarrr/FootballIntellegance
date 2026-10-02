from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class WyscoutMetadataResult:
    provider_match_id: str
    match_id: int
    teams_upserted: int
    events_match_linked: int
    events_team_linked: int


def _season_label(kickoff: datetime) -> str:
    start_year = kickoff.year if kickoff.month >= 7 else kickoff.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def load_wyscout_match_metadata(
    cursor: Any,
    *,
    match: dict[str, Any],
    teams: list[dict[str, Any]],
    competitions: list[dict[str, Any]],
) -> WyscoutMetadataResult:
    provider = "wyscout_open"
    team_payload = {str(team["wyId"]): team for team in teams}
    team_ids: dict[str, int] = {}
    for provider_team_id in match["teamsData"]:
        team = team_payload[provider_team_id]
        cursor.execute(
            """SELECT team_id FROM bridge_team_provider
               WHERE provider=%s AND provider_team_id=%s AND valid_to IS NULL""",
            (provider, provider_team_id),
        )
        row = cursor.fetchone()
        if row:
            team_ids[provider_team_id] = row[0]
            continue
        area = team.get("area") or {}
        cursor.execute(
            """INSERT INTO dim_team (canonical_name, country_code, team_type)
               VALUES (%s,%s,%s) RETURNING team_id""",
            (team["name"], area.get("alpha3code"), str(team.get("type", "club")).upper()),
        )
        team_id = cursor.fetchone()[0]
        team_ids[provider_team_id] = team_id
        cursor.execute(
            """INSERT INTO bridge_team_provider (
                   team_id,provider,provider_team_id,provider_name,confidence,match_method
               ) VALUES (%s,%s,%s,%s,1,'provider_seed')""",
            (team_id, provider, provider_team_id, team["name"]),
        )

    provider_competition_id = str(match["competitionId"])
    competition = next(
        item for item in competitions if str(item["wyId"]) == provider_competition_id
    )
    cursor.execute(
        """SELECT competition_id FROM bridge_competition_provider
           WHERE provider=%s AND provider_competition_id=%s""",
        (provider, provider_competition_id),
    )
    row = cursor.fetchone()
    if row:
        competition_id = row[0]
    else:
        area = competition.get("area") or {}
        cursor.execute(
            """INSERT INTO dim_competition (
                   canonical_name,country_code,competition_type
               ) VALUES (%s,%s,%s) RETURNING competition_id""",
            (competition["name"], area.get("alpha3code"), competition.get("format")),
        )
        competition_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO bridge_competition_provider VALUES (%s,%s,%s,%s)",
            (competition_id, provider, provider_competition_id, competition["name"]),
        )

    kickoff = datetime.strptime(match["dateutc"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    provider_season_id = str(match["seasonId"])
    cursor.execute(
        "SELECT season_id FROM bridge_season_provider WHERE provider=%s AND provider_season_id=%s",
        (provider, provider_season_id),
    )
    row = cursor.fetchone()
    if row:
        season_id = row[0]
    else:
        label = _season_label(kickoff)
        cursor.execute(
            """INSERT INTO dim_season (label,status,data_as_of)
               VALUES (%s,'FINAL',now())
               ON CONFLICT (label) DO UPDATE SET data_as_of=EXCLUDED.data_as_of
               RETURNING season_id""",
            (label,),
        )
        season_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO bridge_season_provider VALUES (%s,%s,%s)",
            (season_id, provider, provider_season_id),
        )

    sides = {data["side"]: str(data["teamId"]) for data in match["teamsData"].values()}
    home_data = match["teamsData"][sides["home"]]
    away_data = match["teamsData"][sides["away"]]
    provider_match_id = str(match["wyId"])
    cursor.execute(
        "SELECT match_id FROM bridge_match_provider WHERE provider=%s AND provider_match_id=%s",
        (provider, provider_match_id),
    )
    row = cursor.fetchone()
    if row:
        match_id = row[0]
    else:
        cursor.execute(
            """
            INSERT INTO dim_match (
                competition_id,season_id,home_team_id,away_team_id,kickoff_at,status,
                home_score,away_score,data_as_of
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now()) RETURNING match_id
            """,
            (
                competition_id,
                season_id,
                team_ids[sides["home"]],
                team_ids[sides["away"]],
                kickoff,
                str(match["status"]).upper(),
                home_data["score"],
                away_data["score"],
            ),
        )
        match_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO bridge_match_provider VALUES (%s,%s,%s,%s)",
            (match_id, provider, provider_match_id, match.get("label")),
        )

    cursor.execute(
        """UPDATE fact_event SET match_id=%s
           WHERE provider=%s AND provider_match_id=%s AND match_id IS NULL""",
        (match_id, provider, provider_match_id),
    )
    events_match_linked = cursor.rowcount
    cursor.execute(
        """
        UPDATE fact_event event SET team_id=bridge.team_id
        FROM bridge_team_provider bridge
        WHERE event.provider=bridge.provider
          AND event.provider_team_id=bridge.provider_team_id
          AND event.provider=%s AND event.provider_match_id=%s
          AND bridge.valid_to IS NULL AND event.team_id IS NULL
        """,
        (provider, provider_match_id),
    )
    return WyscoutMetadataResult(
        provider_match_id=provider_match_id,
        match_id=match_id,
        teams_upserted=len(team_ids),
        events_match_linked=events_match_linked,
        events_team_linked=cursor.rowcount,
    )
