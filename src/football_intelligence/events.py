from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from football_intelligence.coordinates import CoordinateSystem, normalize_point


class CanonicalEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    provider_event_id: str
    provider_match_id: str
    provider_player_id: str | None
    provider_team_id: str
    period: int | str | None
    minute: int | None
    second: float | None
    event_type: str
    event_subtype: str | None
    outcome: str | None
    raw_x: float | None
    raw_y: float | None
    raw_end_x: float | None
    raw_end_y: float | None
    coordinate_system: CoordinateSystem
    normalized_x_m: float | None
    normalized_y_m: float | None
    normalized_end_x_m: float | None
    normalized_end_y_m: float | None
    shot_xg: float | None
    qualifiers: dict[str, Any]


def _point(values: object) -> tuple[float | None, float | None]:
    if not isinstance(values, list) or len(values) < 2:
        return None, None
    return float(values[0]), float(values[1])


def normalize_statsbomb_event(raw: dict[str, Any]) -> CanonicalEvent:
    raw_x, raw_y = _point(raw.get("location"))
    event_type = raw.get("type", {}).get("name", "Unknown")
    detail_key = event_type.casefold().replace(" ", "_")
    raw_detail = raw.get(detail_key)
    detail: dict[str, Any] = raw_detail if isinstance(raw_detail, dict) else {}
    raw_end_x, raw_end_y = _point(detail.get("end_location"))
    coordinate_errors = []
    try:
        start = normalize_point(raw_x, raw_y, CoordinateSystem.STATSBOMB_120_80)
    except ValueError as error:
        start = None
        coordinate_errors.append(f"start: {error}")
    try:
        end = normalize_point(raw_end_x, raw_end_y, CoordinateSystem.STATSBOMB_120_80)
    except ValueError as error:
        end = None
        coordinate_errors.append(f"end: {error}")
    outcome_value = detail.get("outcome")
    outcome = outcome_value.get("name") if isinstance(outcome_value, dict) else None
    player: dict[str, Any] = raw.get("player") or {}
    team: dict[str, Any] = raw.get("team") or {}
    shot: dict[str, Any] = raw.get("shot") or {}
    consumed = {
        "id",
        "match_id",
        "index",
        "period",
        "timestamp",
        "minute",
        "second",
        "type",
        "possession",
        "possession_team",
        "play_pattern",
        "team",
        "player",
        "position",
        "location",
        "duration",
        "related_events",
        detail_key,
    }
    return CanonicalEvent(
        provider="statsbomb_open",
        provider_event_id=str(raw["id"]),
        provider_match_id=str(raw.get("match_id", "")),
        provider_player_id=str(player["id"]) if player.get("id") is not None else None,
        provider_team_id=str(team.get("id", "")),
        period=raw.get("period"),
        minute=raw.get("minute"),
        second=raw.get("second"),
        event_type=event_type,
        event_subtype=detail.get("type", {}).get("name") if isinstance(detail, dict) else None,
        outcome=outcome,
        raw_x=raw_x,
        raw_y=raw_y,
        raw_end_x=raw_end_x,
        raw_end_y=raw_end_y,
        coordinate_system=CoordinateSystem.STATSBOMB_120_80,
        normalized_x_m=start.x if start else None,
        normalized_y_m=start.y if start else None,
        normalized_end_x_m=end.x if end else None,
        normalized_end_y_m=end.y if end else None,
        shot_xg=float(shot["statsbomb_xg"]) if shot.get("statsbomb_xg") is not None else None,
        qualifiers={
            **{key: value for key, value in raw.items() if key not in consumed},
            **({"coordinate_validation_errors": coordinate_errors} if coordinate_errors else {}),
        },
    )


def normalize_wyscout_event(raw: dict[str, Any]) -> CanonicalEvent:
    positions = raw.get("positions") or []
    origin = positions[0] if positions else {}
    destination = positions[1] if len(positions) > 1 else {}
    raw_x, raw_y = origin.get("x"), origin.get("y")
    raw_end_x, raw_end_y = destination.get("x"), destination.get("y")
    start = normalize_point(raw_x, raw_y, CoordinateSystem.WYSCOUT_100)
    end = normalize_point(raw_end_x, raw_end_y, CoordinateSystem.WYSCOUT_100)
    return CanonicalEvent(
        provider="wyscout_open",
        provider_event_id=str(raw["id"]),
        provider_match_id=str(raw["matchId"]),
        provider_player_id=str(raw["playerId"]) if raw.get("playerId") else None,
        provider_team_id=str(raw["teamId"]),
        period=raw.get("matchPeriod"),
        minute=int(float(raw.get("eventSec", 0)) // 60),
        second=float(raw.get("eventSec", 0)) % 60,
        event_type=raw.get("eventName", "Unknown"),
        event_subtype=raw.get("subEventName"),
        outcome=None,
        raw_x=raw_x,
        raw_y=raw_y,
        raw_end_x=raw_end_x,
        raw_end_y=raw_end_y,
        coordinate_system=CoordinateSystem.WYSCOUT_100,
        normalized_x_m=start.x if start else None,
        normalized_y_m=start.y if start else None,
        normalized_end_x_m=end.x if end else None,
        normalized_end_y_m=end.y if end else None,
        shot_xg=None,
        qualifiers={"tags": raw.get("tags", [])},
    )
