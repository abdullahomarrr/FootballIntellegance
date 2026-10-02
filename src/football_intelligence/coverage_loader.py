from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

COVERAGE_INSERT = """
INSERT INTO provider_coverage_observation (
    provider, plan, provider_competition_id, provider_season_id,
    competition_name, season_label, capability, status, checked_at,
    provider_updated_at, raw_object_uri, checksum_sha256, terms_version, notes
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::capability_status, %s, %s, %s, %s, %s, %s)
ON CONFLICT (
    provider, plan, provider_competition_id, provider_season_id, capability, checked_at
) DO UPDATE SET
    status = EXCLUDED.status,
    raw_object_uri = EXCLUDED.raw_object_uri,
    checksum_sha256 = EXCLUDED.checksum_sha256,
    notes = EXCLUDED.notes
"""


def statsbomb_coverage_rows(path: Path) -> list[tuple[Any, ...]]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("StatsBomb coverage artifact must contain a list")
    checksum = hashlib.sha256(raw).hexdigest()
    uri = path.resolve().as_uri()
    rows: list[tuple[Any, ...]] = []
    for item in payload:
        competition = item["competition"]
        for capability in ("event_data", "event_coordinates", "xg"):
            rows.append(
                (
                    "statsbomb_open",
                    "open_data",
                    str(competition["competition_id"]),
                    str(competition["season_id"]),
                    competition["competition_name"],
                    competition["season_name"],
                    capability,
                    "DIRECT",
                    item["checked_at"],
                    competition["match_updated"],
                    uri,
                    checksum,
                    "StatsBomb Open Data terms as observed at discovery",
                    f"Observed {item['match_count']} matches; completeness is not implied.",
                )
            )
    return rows


def load_statsbomb_coverage(cursor: Any, path: Path) -> int:
    rows = statsbomb_coverage_rows(path)
    cursor.executemany(COVERAGE_INSERT, rows)
    return len(rows)
