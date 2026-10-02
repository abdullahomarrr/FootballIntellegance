from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from football_intelligence.openfootball_loader import (
    OpenFootballLoadResult,
    load_openfootball_dataset,
)
from football_intelligence.providers.openfootball import OpenFootballAdapter
from football_intelligence.raw_store import FileRawStore


@dataclass(frozen=True)
class OpenFootballBackfillResult:
    season: str
    competitions: int
    fixtures_seen: int
    matches_inserted: int
    matches_updated: int
    observations_inserted: int


def backfill_openfootball(
    connection: Any,
    *,
    season: str,
    competition_codes: list[str],
    raw_root: Path,
    adapter: OpenFootballAdapter | None = None,
) -> OpenFootballBackfillResult:
    source = adapter or OpenFootballAdapter()
    store = FileRawStore(raw_root)
    results: list[OpenFootballLoadResult] = []
    with connection.cursor() as cursor:
        for code in competition_codes:
            dataset = source.fetch_competition(season, code)
            manifest = store.write_json(
                provider="openfootball",
                endpoint="football.json",
                parameters={"season": season, "competition_code": code},
                payload=dataset.raw_payload,
                pipeline_run_id=str(uuid4()),
                schema_version="openfootball_json_v1",
                terms_version="CC0-1.0",
            )
            results.append(
                load_openfootball_dataset(cursor, dataset, raw_object_uri=manifest.object_uri)
            )
    return OpenFootballBackfillResult(
        season=season,
        competitions=len(results),
        fixtures_seen=sum(row.fixtures_seen for row in results),
        matches_inserted=sum(row.matches_inserted for row in results),
        matches_updated=sum(row.matches_updated for row in results),
        observations_inserted=sum(row.observations_inserted for row in results),
    )
