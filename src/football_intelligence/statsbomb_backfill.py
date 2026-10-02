from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from football_intelligence.backfill import run_backfill
from football_intelligence.database import load_events
from football_intelligence.identities import (
    players_from_statsbomb_lineups,
    resolve_provider_players,
)
from football_intelligence.ingestion import ingest_statsbomb_match, write_report
from football_intelligence.providers.statsbomb_open import StatsBombOpenAdapter
from football_intelligence.raw_store import FileRawStore
from football_intelligence.statsbomb_metadata import (
    link_statsbomb_events,
    load_statsbomb_match_metadata,
)


@dataclass(frozen=True, slots=True)
class StatsBombSeasonResult:
    competition_id: int
    season_id: int
    matches_discovered: int
    matches_completed: int
    matches_skipped: int


def _existing_statsbomb_player_ids(connection: Any) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT provider_player_id FROM bridge_player_provider
               WHERE provider='statsbomb_open' AND valid_to IS NULL"""
        )
        return {str(row[0]) for row in cursor.fetchall()}


def backfill_statsbomb_season(
    connection: Any,
    *,
    competition_id: int,
    season_id: int,
    raw_root: Path,
    canonical_root: Path,
    report_root: Path,
    checkpoint: Path,
    adapter: StatsBombOpenAdapter | None = None,
) -> StatsBombSeasonResult:
    source = adapter or StatsBombOpenAdapter()
    matches = source.fetch_matches(competition_id, season_id)
    by_id = {int(match["match_id"]): match for match in matches}
    raw_store = FileRawStore(raw_root)
    resolved_player_ids = _existing_statsbomb_player_ids(connection)

    def ingest_one(match_id: int) -> None:
        match = by_id[match_id]
        lineups = source.fetch_lineups(match_id)
        raw_store.write_json(
            provider="statsbomb_open",
            endpoint="lineups",
            parameters={"match_id": match_id},
            payload=lineups,
            pipeline_run_id=f"statsbomb-{competition_id}-{season_id}",
            schema_version="statsbomb_open_lineup_v1",
            terms_version="open-data-attribution",
        )
        report = ingest_statsbomb_match(
            match_id,
            raw_root=raw_root,
            canonical_root=canonical_root,
            adapter=source,
        )
        canonical = []
        with Path(report.canonical_object_uri).open(encoding="utf-8") as stream:
            from football_intelligence.events import CanonicalEvent

            canonical = [CanonicalEvent.model_validate(json.loads(line)) for line in stream]
        with connection.cursor() as cursor:
            load_statsbomb_match_metadata(cursor, match)
        players = players_from_statsbomb_lineups(lineups)
        new_players = [
            player for player in players if player.provider_player_id not in resolved_player_ids
        ]
        if new_players:
            resolve_provider_players(connection, new_players)
            resolved_player_ids.update(player.provider_player_id for player in new_players)
        with connection.cursor() as cursor:
            load_events(cursor, canonical)
            link_statsbomb_events(cursor, str(match_id))
        connection.commit()
        write_report(report, report_root / f"statsbomb-match-{match_id}.json")

    backfill = run_backfill(sorted(by_id), checkpoint_path=checkpoint, ingest_match=ingest_one)
    return StatsBombSeasonResult(
        competition_id=competition_id,
        season_id=season_id,
        matches_discovered=len(matches),
        matches_completed=backfill.succeeded,
        matches_skipped=backfill.skipped,
    )


def write_season_result(result: StatsBombSeasonResult, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
