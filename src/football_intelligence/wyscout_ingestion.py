from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from football_intelligence.events import normalize_wyscout_event
from football_intelligence.quality import validate_events
from football_intelligence.raw_store import FileRawStore


class WyscoutIngestionReport(BaseModel):
    provider: str = "wyscout_open"
    match_id: int
    country: str
    pipeline_run_id: str
    source_archive_sha256: str
    raw_object_uri: str
    raw_checksum_sha256: str
    raw_event_count: int
    canonical_event_count: int
    quarantined_event_count: int
    event_type_counts: dict[str, int]
    generated_at: datetime
    canonical_object_uri: str


def read_json_member(archive: Path, member: str) -> object:
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        if member not in names or Path(member).name != member:
            raise ValueError(f"Archive member is missing or unsafe: {member}")
        return json.loads(zipped.read(member))


def ingest_wyscout_match(
    match_id: int,
    *,
    country: str,
    events_archive: Path,
    raw_root: Path,
    canonical_root: Path,
) -> WyscoutIngestionReport:
    member = f"events_{country}.json"
    payload = read_json_member(events_archive, member)
    if not isinstance(payload, list):
        raise ValueError("Wyscout event archive member must contain a list")
    raw_events = [event for event in payload if int(event.get("matchId", -1)) == match_id]
    if not raw_events:
        raise ValueError(f"No Wyscout events found for match {match_id}")
    pipeline_run_id = str(uuid4())
    manifest = FileRawStore(raw_root).write_json(
        provider="wyscout_open",
        endpoint="events_archive_match",
        parameters={"country": country, "match_id": match_id},
        payload=raw_events,
        pipeline_run_id=pipeline_run_id,
        schema_version="wyscout_open_event_v1",
        terms_version="CC-BY-4.0",
    )
    quality = validate_events([normalize_wyscout_event(event) for event in raw_events])
    canonical = list(quality.accepted)
    canonical_root.mkdir(parents=True, exist_ok=True)
    target = canonical_root / f"wyscout_match_{match_id}.jsonl"
    temporary = target.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for event in canonical:
            stream.write(event.model_dump_json() + "\n")
    temporary.replace(target)
    archive_checksum = hashlib.sha256(events_archive.read_bytes()).hexdigest()
    return WyscoutIngestionReport(
        match_id=match_id,
        country=country,
        pipeline_run_id=pipeline_run_id,
        source_archive_sha256=archive_checksum,
        raw_object_uri=manifest.object_uri,
        raw_checksum_sha256=manifest.checksum_sha256,
        raw_event_count=len(raw_events),
        canonical_event_count=len(canonical),
        quarantined_event_count=len(quality.quarantined),
        event_type_counts=dict(sorted(Counter(event.event_type for event in canonical).items())),
        generated_at=datetime.now(UTC),
        canonical_object_uri=target.as_posix(),
    )
