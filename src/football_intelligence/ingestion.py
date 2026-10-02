from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from football_intelligence.events import normalize_statsbomb_event
from football_intelligence.providers.statsbomb_open import StatsBombOpenAdapter
from football_intelligence.quality import validate_events
from football_intelligence.raw_store import FileRawStore


class IngestionReport(BaseModel):
    provider: str
    match_id: int
    pipeline_run_id: str
    raw_object_uri: str
    raw_checksum_sha256: str
    raw_event_count: int
    canonical_event_count: int
    event_type_counts: dict[str, int]
    events_with_coordinates: int
    events_with_xg: int
    quarantined_event_count: int
    quarantine_reason_counts: dict[str, int]
    generated_at: datetime
    canonical_object_uri: str


def ingest_statsbomb_match(
    match_id: int,
    *,
    raw_root: Path,
    canonical_root: Path,
    adapter: StatsBombOpenAdapter | None = None,
) -> IngestionReport:
    source = adapter or StatsBombOpenAdapter()
    events = source.fetch_events(match_id)
    pipeline_run_id = str(uuid4())
    manifest = FileRawStore(raw_root).write_json(
        provider="statsbomb_open",
        endpoint="events",
        parameters={"match_id": match_id},
        payload=events,
        pipeline_run_id=pipeline_run_id,
        schema_version="statsbomb_open_event_v1",
        terms_version="open-data-attribution",
    )
    normalized = []
    normalization_quarantine: Counter[str] = Counter()
    for raw_event in events:
        try:
            normalized.append(normalize_statsbomb_event(raw_event))
        except (TypeError, ValueError) as error:
            normalization_quarantine[f"{type(error).__name__.upper()}: {error}"] += 1
    quality = validate_events(normalized)
    canonical = list(quality.accepted)
    canonical_root.mkdir(parents=True, exist_ok=True)
    target = canonical_root / f"statsbomb_match_{match_id}.jsonl"
    temporary = target.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for canonical_event in canonical:
            stream.write(canonical_event.model_dump_json() + "\n")
    temporary.replace(target)
    type_counts = Counter(event.event_type for event in canonical)
    return IngestionReport(
        provider="statsbomb_open",
        match_id=match_id,
        pipeline_run_id=pipeline_run_id,
        raw_object_uri=manifest.object_uri,
        raw_checksum_sha256=manifest.checksum_sha256,
        raw_event_count=len(events),
        canonical_event_count=len(canonical),
        event_type_counts=dict(sorted(type_counts.items())),
        events_with_coordinates=sum(event.normalized_x_m is not None for event in canonical),
        events_with_xg=sum(event.shot_xg is not None for event in canonical),
        quarantined_event_count=len(quality.quarantined) + sum(normalization_quarantine.values()),
        quarantine_reason_counts=dict(
            sorted((normalization_quarantine + Counter(quality.reason_counts)).items())
        ),
        generated_at=datetime.now(UTC),
        canonical_object_uri=target.as_posix(),
    )


def write_report(report: IngestionReport, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
