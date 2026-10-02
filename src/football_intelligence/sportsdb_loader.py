from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from football_intelligence.providers.thesportsdb import SportsDBEvent, TheSportsDBAdapter
from football_intelligence.raw_store import FileRawStore


@dataclass(frozen=True)
class SportsDBLoadResult:
    events_seen: int
    observations_inserted: int
    matches_corroborated: int
    score_conflicts: int


def load_sportsdb_events(
    cursor: Any, events: list[SportsDBEvent], *, raw_object_uri: str
) -> SportsDBLoadResult:
    observations = corroborated = conflicts = 0
    for event in events:
        stable_payload = dict(event.raw)
        encoded = json.dumps(stable_payload, sort_keys=True, separators=(",", ":")).encode()
        cursor.execute(
            """INSERT INTO source_observation (provider,entity_type,provider_entity_id,
               observed_at,source_url,source_license,raw_object_uri,content_hash,payload)
               VALUES ('thesportsdb','MATCH',%s,%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT DO NOTHING""",
            (
                event.event_id,
                event.checked_at,
                f"https://www.thesportsdb.com/event/{event.event_id}",
                "TheSportsDB terms of use",
                raw_object_uri,
                sha256(encoded).hexdigest(),
                encoded.decode(),
            ),
        )
        observations += max(cursor.rowcount, 0)
        if not event.date or not event.home_team or not event.away_team:
            continue
        cursor.execute(
            """SELECT m.match_id,m.home_score,m.away_score
               FROM dim_match m JOIN dim_team home ON home.team_id=m.home_team_id
               JOIN dim_team away ON away.team_id=m.away_team_id
               WHERE m.kickoff_at::date=%s
                 AND lower(home.canonical_name)=lower(%s)
                 AND lower(away.canonical_name)=lower(%s)""",
            (event.date, event.home_team, event.away_team),
        )
        candidates = cursor.fetchall()
        if len(candidates) != 1:
            continue
        match_id, home_score, away_score = candidates[0]
        cursor.execute(
            """INSERT INTO bridge_match_provider
               (match_id,provider,provider_match_id,source_label)
               VALUES (%s,'thesportsdb',%s,%s) ON CONFLICT DO NOTHING""",
            (match_id, event.event_id, event.league_name),
        )
        corroborated += 1
        canonical_score = [home_score, away_score]
        secondary_score = [event.home_score, event.away_score]
        if None not in canonical_score and None not in secondary_score and (
            canonical_score != secondary_score
        ):
            cursor.execute(
                """INSERT INTO source_conflict (entity_type,canonical_entity_id,field_name,
                   left_provider,left_value,right_provider,right_value)
                   VALUES ('MATCH',%s,'full_time_score','canonical',%s::jsonb,
                   'thesportsdb',%s::jsonb) ON CONFLICT DO NOTHING""",
                (match_id, json.dumps(canonical_score), json.dumps(secondary_score)),
            )
            conflicts += max(cursor.rowcount, 0)
    return SportsDBLoadResult(len(events), observations, corroborated, conflicts)


def ingest_sportsdb_day(
    connection: Any,
    *,
    day: date,
    raw_root: Path,
    adapter: TheSportsDBAdapter | None = None,
) -> SportsDBLoadResult:
    source = adapter or TheSportsDBAdapter()
    events = source.events_by_day(day.isoformat())
    payload = [event.raw for event in events]
    manifest = FileRawStore(raw_root).write_json(
        provider="thesportsdb",
        endpoint="eventsday.php",
        parameters={"d": day.isoformat(), "s": "Soccer"},
        payload=payload,
        pipeline_run_id=str(uuid4()),
        ingested_at=datetime.now(UTC),
        schema_version="thesportsdb_v1_event",
        terms_version="2026-09-17",
    )
    with connection.cursor() as cursor:
        return load_sportsdb_events(cursor, events, raw_object_uri=manifest.object_uri)
