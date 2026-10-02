from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from football_intelligence.wyscout_ingestion import read_json_member


@dataclass(frozen=True, slots=True)
class WyscoutPlayerMatchResult:
    country: str
    matches_read: int
    participant_rows: int
    rows_upserted: int
    unresolved_participants: int


def _integer(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _minutes_by_player(team_data: dict[str, Any], duration: int) -> dict[str, tuple[bool, int]]:
    formation = team_data.get("formation") or {}
    lineup = formation.get("lineup")
    starters = {
        str(item["playerId"])
        for item in (lineup if isinstance(lineup, list) else [])
        if isinstance(item, dict) and item.get("playerId") is not None
    }
    entered: dict[str, int] = {}
    exited: dict[str, int] = {}
    substitutions = formation.get("substitutions")
    for substitution in substitutions if isinstance(substitutions, list) else []:
        if not isinstance(substitution, dict):
            continue
        minute = min(max(_integer(substitution.get("minute")), 0), duration)
        if substitution.get("playerIn") is not None:
            entered[str(substitution["playerIn"])] = minute
        if substitution.get("playerOut") is not None:
            exited[str(substitution["playerOut"])] = minute
    participants = starters | set(entered)
    result: dict[str, tuple[bool, int]] = {}
    for player_id in participants:
        start = 0 if player_id in starters else entered[player_id]
        end = exited.get(player_id, duration)
        result[player_id] = (player_id in starters, max(0, end - start))
    return result


def load_wyscout_player_matches(
    connection: Any,
    *,
    country: str,
    events_archive: Path,
    matches_archive: Path,
    players_path: Path,
) -> WyscoutPlayerMatchResult:
    events_payload = read_json_member(events_archive, f"events_{country}.json")
    matches_payload = read_json_member(matches_archive, f"matches_{country}.json")
    players_payload = json.loads(players_path.read_text(encoding="utf-8"))
    if not all(
        isinstance(item, list) for item in (events_payload, matches_payload, players_payload)
    ):
        raise ValueError("Wyscout player-match inputs must contain lists")
    events = cast(list[dict[str, Any]], events_payload)
    matches = cast(list[dict[str, Any]], matches_payload)
    players = cast(list[dict[str, Any]], players_payload)
    positions = {
        str(player["wyId"]): str((player.get("role") or {}).get("code2") or "")
        for player in players
    }

    metrics: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for event in events:
        player_id = str(event.get("playerId") or "")
        if not player_id:
            continue
        counter = metrics[(str(event["matchId"]), player_id)]
        event_name = event.get("eventName")
        tag_ids = {int(tag["id"]) for tag in event.get("tags") or []}
        if event_name == "Shot":
            counter["shots"] += 1
            if 1801 in tag_ids or 101 in tag_ids:
                counter["shots_on_target"] += 1
        if event_name == "Pass":
            counter["passes"] += 1
        if 301 in tag_ids:
            counter["assists"] += 1
        if 302 in tag_ids:
            counter["key_passes"] += 1
        if 1601 in tag_ids:
            counter["tackles"] += 1
        if 1401 in tag_ids:
            counter["interceptions"] += 1

    data_as_of = datetime.now(UTC)
    rows: list[tuple[Any, ...]] = []
    participant_rows = unresolved = 0
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT provider_player_id,player_id FROM bridge_player_provider
               WHERE provider='wyscout_open' AND valid_to IS NULL"""
        )
        player_map = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute(
            """SELECT provider_team_id,team_id FROM bridge_team_provider
               WHERE provider='wyscout_open' AND valid_to IS NULL"""
        )
        team_map = {str(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute(
            """SELECT bridge.provider_match_id,bridge.match_id,match.competition_id,
                      match.season_id
               FROM bridge_match_provider bridge
               JOIN dim_match match USING(match_id)
               WHERE bridge.provider='wyscout_open'"""
        )
        match_map = {
            str(row[0]): (int(row[1]), int(row[2]), int(row[3])) for row in cursor.fetchall()
        }

        for match in matches:
            provider_match_id = str(match["wyId"])
            match_id, competition_id, season_id = match_map[provider_match_id]
            duration = 120 if str(match.get("duration")).casefold() != "regular" else 90
            for provider_team_id, team_data in match["teamsData"].items():
                formation = team_data.get("formation") or {}
                lineup = formation.get("lineup")
                bench = formation.get("bench")
                player_cards = {
                    str(item["playerId"]): item
                    for item in (
                        (lineup if isinstance(lineup, list) else [])
                        + (bench if isinstance(bench, list) else [])
                    )
                    if isinstance(item, dict) and item.get("playerId") is not None
                }
                for provider_player_id, (started, minutes) in _minutes_by_player(
                    team_data, duration
                ).items():
                    participant_rows += 1
                    canonical_player_id = player_map.get(provider_player_id)
                    if canonical_player_id is None:
                        unresolved += 1
                        continue
                    event_metrics = metrics[(provider_match_id, provider_player_id)]
                    card = player_cards.get(provider_player_id, {})
                    rows.append(
                        (
                            canonical_player_id,
                            match_id,
                            team_map[str(provider_team_id)],
                            competition_id,
                            season_id,
                            started,
                            minutes,
                            positions.get(provider_player_id) or None,
                            _integer(card.get("goals")),
                            event_metrics["assists"],
                            event_metrics["shots"],
                            event_metrics["shots_on_target"],
                            event_metrics["passes"],
                            event_metrics["key_passes"],
                            event_metrics["tackles"],
                            event_metrics["interceptions"],
                            "wyscout_open",
                            data_as_of,
                        )
                    )
        cursor.executemany(
            """
            INSERT INTO fact_player_match (
                player_id,match_id,team_id,competition_id,season_id,started,minutes,
                position,goals,assists,shots,shots_on_target,passes,key_passes,
                tackles,interceptions,provider,data_as_of
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (player_id,match_id,team_id,provider) DO UPDATE SET
                started=EXCLUDED.started,minutes=EXCLUDED.minutes,position=EXCLUDED.position,
                goals=EXCLUDED.goals,assists=EXCLUDED.assists,shots=EXCLUDED.shots,
                shots_on_target=EXCLUDED.shots_on_target,passes=EXCLUDED.passes,
                key_passes=EXCLUDED.key_passes,tackles=EXCLUDED.tackles,
                interceptions=EXCLUDED.interceptions,data_as_of=EXCLUDED.data_as_of
            """,
            rows,
        )
    return WyscoutPlayerMatchResult(
        country=country,
        matches_read=len(matches),
        participant_rows=participant_rows,
        rows_upserted=len(rows),
        unresolved_participants=unresolved,
    )
