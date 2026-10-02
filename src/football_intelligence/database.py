from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from football_intelligence.events import CanonicalEvent


class Cursor(Protocol):
    def executemany(self, query: str, params_seq: Iterable[tuple[Any, ...]]) -> Any: ...


@dataclass(frozen=True, slots=True)
class LoadResult:
    attempted: int
    provider: str
    provider_match_id: str


EVENT_UPSERT = """
INSERT INTO fact_event (
    provider, provider_event_id, provider_match_id, provider_player_id, provider_team_id,
    period, minute, second, event_type, event_subtype, outcome,
    raw_x, raw_y, raw_end_x, raw_end_y, coordinate_system,
    normalized_x_m, normalized_y_m, normalized_end_x_m, normalized_end_y_m,
    attacking_direction_normalized, shot_xg, qualifiers, source_schema_version, data_as_of
) VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    false, %s, %s::jsonb, %s, %s
)
ON CONFLICT (provider, provider_event_id) DO UPDATE SET
    provider_match_id = EXCLUDED.provider_match_id,
    provider_player_id = EXCLUDED.provider_player_id,
    provider_team_id = EXCLUDED.provider_team_id,
    period = EXCLUDED.period,
    minute = EXCLUDED.minute,
    second = EXCLUDED.second,
    event_type = EXCLUDED.event_type,
    event_subtype = EXCLUDED.event_subtype,
    outcome = EXCLUDED.outcome,
    raw_x = EXCLUDED.raw_x,
    raw_y = EXCLUDED.raw_y,
    raw_end_x = EXCLUDED.raw_end_x,
    raw_end_y = EXCLUDED.raw_end_y,
    coordinate_system = EXCLUDED.coordinate_system,
    normalized_x_m = EXCLUDED.normalized_x_m,
    normalized_y_m = EXCLUDED.normalized_y_m,
    normalized_end_x_m = EXCLUDED.normalized_end_x_m,
    normalized_end_y_m = EXCLUDED.normalized_end_y_m,
    shot_xg = EXCLUDED.shot_xg,
    qualifiers = EXCLUDED.qualifiers,
    source_schema_version = EXCLUDED.source_schema_version,
    data_as_of = EXCLUDED.data_as_of
"""


def _decimal(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def event_parameters(event: CanonicalEvent, data_as_of: datetime) -> tuple[Any, ...]:
    return (
        event.provider,
        event.provider_event_id,
        event.provider_match_id,
        event.provider_player_id,
        event.provider_team_id,
        str(event.period) if event.period is not None else None,
        event.minute,
        _decimal(event.second),
        event.event_type,
        event.event_subtype,
        event.outcome,
        _decimal(event.raw_x),
        _decimal(event.raw_y),
        _decimal(event.raw_end_x),
        _decimal(event.raw_end_y),
        event.coordinate_system.value,
        _decimal(event.normalized_x_m),
        _decimal(event.normalized_y_m),
        _decimal(event.normalized_end_x_m),
        _decimal(event.normalized_end_y_m),
        _decimal(event.shot_xg),
        json.dumps(event.qualifiers, ensure_ascii=False, separators=(",", ":")),
        "canonical_event_v1",
        data_as_of,
    )


def load_events(cursor: Cursor, events: list[CanonicalEvent]) -> LoadResult:
    if not events:
        return LoadResult(0, "", "")
    providers = {event.provider for event in events}
    match_ids = {event.provider_match_id for event in events}
    if len(providers) != 1 or len(match_ids) != 1:
        raise ValueError("A load batch must contain one provider and one match")
    data_as_of = datetime.now(UTC)
    cursor.executemany(EVENT_UPSERT, [event_parameters(event, data_as_of) for event in events])
    return LoadResult(len(events), next(iter(providers)), next(iter(match_ids)))
