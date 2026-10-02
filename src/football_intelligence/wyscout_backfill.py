from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from football_intelligence.database import load_events
from football_intelligence.events import normalize_wyscout_event
from football_intelligence.identities import (
    players_from_wyscout,
    resolve_provider_players,
)
from football_intelligence.quality import validate_events
from football_intelligence.wyscout_ingestion import read_json_member
from football_intelligence.wyscout_metadata import load_wyscout_match_metadata


@dataclass(frozen=True, slots=True)
class WyscoutBackfillResult:
    country: str
    source_archive_sha256: str
    matches_loaded: int
    events_read: int
    events_loaded: int
    events_quarantined: int
    provider_players_seen: int
    identities_seeded: int
    identities_auto_linked: int
    identity_review_candidates: int
    existing_identities: int
    quarantine_reasons: dict[str, int]


def _quarantine_event(
    cursor: Any,
    *,
    event: dict[str, Any],
    reason: str,
    archive: Path,
) -> None:
    cursor.execute(
        """
        INSERT INTO data_quarantine (
            provider,entity_type,provider_entity_id,reason_code,raw_object_uri,payload
        )
        SELECT 'wyscout_open','EVENT',%s,%s,%s,%s::jsonb
        WHERE NOT EXISTS (
            SELECT 1 FROM data_quarantine
            WHERE provider='wyscout_open' AND entity_type='EVENT'
              AND provider_entity_id=%s AND reason_code=%s AND resolved_at IS NULL
        )
        """,
        (
            str(event.get("id", "")),
            reason,
            archive.as_posix(),
            json.dumps(event, ensure_ascii=False),
            str(event.get("id", "")),
            reason,
        ),
    )


def backfill_wyscout_country(
    connection: Any,
    *,
    country: str,
    events_archive: Path,
    matches_archive: Path,
    players_path: Path,
    teams_path: Path,
    competitions_path: Path,
) -> WyscoutBackfillResult:
    events_payload = read_json_member(events_archive, f"events_{country}.json")
    matches_payload = read_json_member(matches_archive, f"matches_{country}.json")
    players_payload = json.loads(players_path.read_text(encoding="utf-8"))
    teams_payload = json.loads(teams_path.read_text(encoding="utf-8"))
    competitions_payload = json.loads(competitions_path.read_text(encoding="utf-8"))
    if not all(
        isinstance(payload, list)
        for payload in (
            events_payload,
            matches_payload,
            players_payload,
            teams_payload,
            competitions_payload,
        )
    ):
        raise ValueError("Every Wyscout backfill input must contain a list")
    events = cast(list[dict[str, Any]], events_payload)
    matches = cast(list[dict[str, Any]], matches_payload)
    players = cast(list[dict[str, Any]], players_payload)
    teams = cast(list[dict[str, Any]], teams_payload)
    competitions = cast(list[dict[str, Any]], competitions_payload)

    events_by_match: dict[str, list[dict[str, Any]]] = defaultdict(list)
    provider_player_ids: set[str] = set()
    for event in events:
        match_id = str(event["matchId"])
        events_by_match[match_id].append(event)
        if event.get("playerId"):
            provider_player_ids.add(str(event["playerId"]))

    matches_by_id = {str(match["wyId"]): match for match in matches}
    unknown_matches = sorted(set(events_by_match) - set(matches_by_id))
    if unknown_matches:
        raise ValueError(f"Events reference {len(unknown_matches)} unknown Wyscout matches")

    loaded = quarantined = 0
    quarantine_reasons: dict[str, int] = defaultdict(int)
    with connection.cursor() as cursor:
        for provider_match_id, raw_events in events_by_match.items():
            normalized = []
            for event in raw_events:
                try:
                    normalized.append(normalize_wyscout_event(event))
                except (TypeError, ValueError, KeyError) as error:
                    reason = f"NORMALIZATION_ERROR_{type(error).__name__.upper()}"
                    _quarantine_event(
                        cursor,
                        event=event,
                        reason=reason,
                        archive=events_archive,
                    )
                    quarantined += 1
                    quarantine_reasons[reason] += 1
            quality = validate_events(normalized)
            canonical_events = list(quality.accepted)
            load_events(cursor, canonical_events)
            loaded += len(canonical_events)
            quarantined += len(quality.quarantined)
            for item in quality.quarantined:
                raw_event = next(
                    event
                    for event in raw_events
                    if str(event.get("id")) == item.event.provider_event_id
                )
                _quarantine_event(
                    cursor,
                    event=raw_event,
                    reason=item.reason,
                    archive=events_archive,
                )
                quarantine_reasons[item.reason] += 1
            load_wyscout_match_metadata(
                cursor,
                match=matches_by_id[provider_match_id],
                teams=teams,
                competitions=competitions,
            )

    identity_result = resolve_provider_players(
        connection,
        players_from_wyscout(players, player_ids=provider_player_ids),
    )
    return WyscoutBackfillResult(
        country=country,
        source_archive_sha256=hashlib.sha256(events_archive.read_bytes()).hexdigest(),
        matches_loaded=len(events_by_match),
        events_read=len(events),
        events_loaded=loaded,
        events_quarantined=quarantined,
        provider_players_seen=len(provider_player_ids),
        identities_seeded=identity_result.seeded,
        identities_auto_linked=identity_result.auto_linked,
        identity_review_candidates=identity_result.review_candidates,
        existing_identities=identity_result.existing,
        quarantine_reasons=dict(sorted(quarantine_reasons.items())),
    )
