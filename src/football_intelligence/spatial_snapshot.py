"""Precompute every player-season spatial payload into player_spatial_snapshot."""

from __future__ import annotations

import json
from typing import Any

from football_intelligence.repository import player_spatial_live, spatial_snapshot_keys

UPSERT = """
INSERT INTO player_spatial_snapshot (player_id, team_id, competition_id, season_id, payload)
VALUES (%s, %s, %s, %s, %s::jsonb)
ON CONFLICT (player_id, team_id, competition_id, season_id)
DO UPDATE SET payload = EXCLUDED.payload, built_at = now()
"""


def build_spatial_snapshot(connection: Any, *, batch_size: int = 200) -> dict[str, int]:
    keys = spatial_snapshot_keys()
    written = skipped = 0
    batch: list[tuple[Any, ...]] = []
    with connection.cursor() as cursor:
        for key in keys:
            context = (key["team_id"], key["competition_id"], key["season_id"])
            payload = player_spatial_live(int(key["player_id"]), context)
            if payload is None:
                skipped += 1
                continue
            batch.append(
                (
                    key["player_id"],
                    key["team_id"],
                    key["competition_id"],
                    key["season_id"],
                    json.dumps(payload, default=_json_default),
                )
            )
            if len(batch) >= batch_size:
                cursor.executemany(UPSERT, batch)
                connection.commit()
                written += len(batch)
                batch.clear()
        if batch:
            cursor.executemany(UPSERT, batch)
            connection.commit()
            written += len(batch)
    return {"profiles": len(keys), "written": written, "skipped": skipped}


def _json_default(value: Any) -> Any:
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    raise TypeError(f"Cannot serialise {type(value).__name__}")
