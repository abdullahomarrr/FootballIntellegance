from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from football_intelligence.providers.statsbomb_open import StatsBombOpenAdapter


@dataclass(frozen=True, slots=True)
class StatsBombPlayerMatchResult:
    competition_id: int
    season_id: int
    matches_read: int
    participant_rows: int
    rows_upserted: int
    unresolved_participants: int


def _clock_seconds(value: object, default: int) -> int:
    if not isinstance(value, str) or ":" not in value:
        return default
    minutes, seconds = value.split(":", 1)
    try:
        return int(minutes) * 60 + int(float(seconds))
    except ValueError:
        return default


def _position_group(positions: list[dict[str, Any]]) -> str | None:
    names = " ".join(str(item.get("position") or "") for item in positions)
    if "Goalkeeper" in names:
        return "GK"
    if "Back" in names:
        return "DF"
    if "Forward" in names or "Wing" in names:
        return "FW"
    return "MD" if names else None


def _participation(
    lineups: list[dict[str, Any]], duration_minutes: int
) -> list[tuple[str, str, bool, int, str | None]]:
    duration_seconds = duration_minutes * 60
    rows = []
    for team in lineups:
        team_id = str(team["team_id"])
        for player in team.get("lineup") or []:
            positions = player.get("positions") or []
            if not positions:
                continue
            start = min(_clock_seconds(item.get("from"), 0) for item in positions)
            end = max(_clock_seconds(item.get("to"), duration_seconds) for item in positions)
            end = min(max(end, start), duration_seconds)
            started = any(item.get("start_reason") == "Starting XI" for item in positions)
            minutes = min(130, max(0, math.ceil((end - start) / 60)))
            rows.append(
                (
                    str(player["player_id"]),
                    team_id,
                    started,
                    minutes,
                    _position_group(positions),
                )
            )
    return rows


def _event_metrics(events: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    metrics: dict[str, Counter[str]] = {}
    for event in events:
        player = event.get("player") or {}
        player_id = player.get("id")
        if player_id is None:
            continue
        counter = metrics.setdefault(str(player_id), Counter())
        event_name = str((event.get("type") or {}).get("name") or "")
        if event_name == "Shot":
            counter["shots"] += 1
            outcome = str(((event.get("shot") or {}).get("outcome") or {}).get("name") or "")
            if outcome in {"Goal", "Saved", "Saved to Post"}:
                counter["shots_on_target"] += 1
            if outcome == "Goal":
                counter["goals"] += 1
        if event_name == "Pass":
            counter["passes"] += 1
            detail = event.get("pass") or {}
            if detail.get("goal_assist"):
                counter["assists"] += 1
            if detail.get("shot_assist") or detail.get("goal_assist"):
                counter["key_passes"] += 1
        if (
            event_name == "Duel"
            and (event.get("duel") or {}).get("type", {}).get("name") == "Tackle"
        ):
            counter["tackles"] += 1
        if event_name == "Interception":
            counter["interceptions"] += 1
    return metrics


def load_statsbomb_player_matches(
    connection: Any,
    *,
    competition_id: int,
    season_id: int,
    adapter: StatsBombOpenAdapter | None = None,
) -> StatsBombPlayerMatchResult:
    source = adapter or StatsBombOpenAdapter()
    matches = source.fetch_matches(competition_id, season_id)
    rows: list[tuple[Any, ...]] = []
    participant_rows = unresolved = 0
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT provider_player_id,player_id FROM bridge_player_provider
               WHERE provider='statsbomb_open' AND valid_to IS NULL"""
        )
        player_map = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute(
            """SELECT provider_team_id,team_id FROM bridge_team_provider
               WHERE provider='statsbomb_open' AND valid_to IS NULL"""
        )
        team_map = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute(
            """SELECT bridge.provider_match_id,bridge.match_id,match.competition_id,
                      match.season_id
               FROM bridge_match_provider bridge JOIN dim_match match USING(match_id)
               WHERE bridge.provider='statsbomb_open'"""
        )
        match_map = {
            str(row[0]): (int(row[1]), int(row[2]), int(row[3])) for row in cursor.fetchall()
        }
        data_as_of = datetime.now(UTC)
        for match in matches:
            provider_match_id = str(match["match_id"])
            if provider_match_id not in match_map:
                continue
            canonical_match_id, canonical_competition_id, canonical_season_id = match_map[
                provider_match_id
            ]
            events = source.fetch_events(int(provider_match_id))
            lineups = source.fetch_lineups(int(provider_match_id))
            duration = min(
                130,
                max(90, max((int(event.get("minute") or 0) for event in events), default=89) + 1),
            )
            metrics = _event_metrics(events)
            for provider_player_id, provider_team_id, started, minutes, position in _participation(
                lineups, duration
            ):
                participant_rows += 1
                player_id = player_map.get(provider_player_id)
                team_id = team_map.get(provider_team_id)
                if player_id is None or team_id is None:
                    unresolved += 1
                    continue
                values = metrics.get(provider_player_id, Counter())
                rows.append(
                    (
                        player_id,
                        canonical_match_id,
                        team_id,
                        canonical_competition_id,
                        canonical_season_id,
                        started,
                        minutes,
                        position,
                        values["goals"],
                        values["assists"],
                        values["shots"],
                        values["shots_on_target"],
                        values["passes"],
                        values["key_passes"],
                        values["tackles"],
                        values["interceptions"],
                        "statsbomb_open",
                        data_as_of,
                    )
                )
        cursor.executemany(
            """INSERT INTO fact_player_match (
                   player_id,match_id,team_id,competition_id,season_id,started,minutes,
                   position,goals,assists,shots,shots_on_target,passes,key_passes,
                   tackles,interceptions,provider,data_as_of
               ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (player_id,match_id,team_id,provider) DO UPDATE SET
                 started=EXCLUDED.started,minutes=EXCLUDED.minutes,position=EXCLUDED.position,
                 goals=EXCLUDED.goals,assists=EXCLUDED.assists,shots=EXCLUDED.shots,
                 shots_on_target=EXCLUDED.shots_on_target,passes=EXCLUDED.passes,
                 key_passes=EXCLUDED.key_passes,tackles=EXCLUDED.tackles,
                 interceptions=EXCLUDED.interceptions,data_as_of=EXCLUDED.data_as_of""",
            rows,
        )
    return StatsBombPlayerMatchResult(
        competition_id,
        season_id,
        len(matches),
        participant_rows,
        len(rows),
        unresolved,
    )
