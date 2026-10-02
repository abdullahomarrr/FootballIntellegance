from __future__ import annotations

import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from football_intelligence.entity_resolution import normalize_name
from football_intelligence.providers.thesportsdb import SportsDBPlayer, TheSportsDBAdapter
from football_intelligence.raw_store import FileRawStore


@dataclass(frozen=True)
class IdentityTriangulationResult:
    candidates_checked: int
    corroborated: int
    no_result: int
    ambiguous: int
    conflicting: int
    provider_failures: int


def _store_player_observation(
    cursor: Any, player: SportsDBPlayer, *, raw_object_uri: str
) -> None:
    encoded = json.dumps(
        player.raw_without_artwork, sort_keys=True, separators=(",", ":")
    ).encode()
    cursor.execute(
        """INSERT INTO source_observation (provider,entity_type,provider_entity_id,
           observed_at,source_url,source_license,raw_object_uri,content_hash,payload)
           VALUES ('thesportsdb','PLAYER',%s,%s,%s,%s,%s,%s,%s::jsonb)
           ON CONFLICT DO NOTHING""",
        (
            player.player_id,
            player.checked_at,
            f"https://www.thesportsdb.com/player/{player.player_id}",
            "TheSportsDB terms of use",
            raw_object_uri,
            sha256(encoded).hexdigest(),
            encoded.decode(),
        ),
    )


def triangulate_wyscout_candidates(
    connection: Any,
    *,
    raw_root: Path,
    limit: int = 30,
    minimum_interval_seconds: float = 2.1,
    adapter: TheSportsDBAdapter | None = None,
) -> IdentityTriangulationResult:
    source = adapter or TheSportsDBAdapter()
    store = FileRawStore(raw_root)
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT candidate.candidate_id,candidate.provider_entity_id,
                      target.normalized_name,source_player.canonical_name,
                      source_player.birth_date
               FROM entity_resolution_candidate candidate
               JOIN dim_player target ON target.player_id=candidate.canonical_candidate_id
               JOIN bridge_player_provider source_bridge
                 ON source_bridge.provider=candidate.provider
                AND source_bridge.provider_player_id=candidate.provider_entity_id
                AND source_bridge.valid_to IS NULL
               JOIN dim_player source_player ON source_player.player_id=source_bridge.player_id
               WHERE candidate.entity_type='PLAYER' AND candidate.provider='wyscout_open'
                 AND candidate.status='PENDING'
                 AND NOT (candidate.signals ? 'third_source')
               ORDER BY candidate.candidate_id LIMIT %s""",
            (limit,),
        )
        candidates = cursor.fetchall()
    corroborated = no_result = ambiguous = conflicting = failures = 0
    for index, (candidate_id, provider_id, target_name, source_name, source_birth) in enumerate(
        candidates
    ):
        if index and minimum_interval_seconds:
            time.sleep(minimum_interval_seconds)
        try:
            results = source.search_players(str(source_name))
        except httpx.HTTPError:
            failures += 1
            continue
        manifest = store.write_json(
            provider="thesportsdb",
            endpoint="searchplayers.php",
            parameters={"p": str(source_name)},
            payload=[row.raw_without_artwork for row in results],
            pipeline_run_id=str(uuid4()),
            schema_version="thesportsdb_v1_player",
            terms_version="2026-09-17",
        )
        exact = [
            row
            for row in results
            if normalize_name(row.name) == str(target_name)
            and normalize_name(row.name) == normalize_name(str(source_name))
        ]
        with connection.cursor() as cursor:
            for row in results:
                _store_player_observation(cursor, row, raw_object_uri=manifest.object_uri)
            if not exact:
                no_result += 1
                continue
            dated = [
                row for row in exact if row.birth_date is not None and source_birth is not None
            ]
            matches = [row for row in dated if row.birth_date == source_birth]
            if len(matches) == 1 and len(exact) == 1:
                evidence = {
                    "third_source": "thesportsdb",
                    "third_source_player_id": matches[0].player_id,
                    "signals": ["exact_normalized_name", "exact_birth_date"],
                    "provider_player_id": str(provider_id),
                    "requires_human_review": True,
                }
                cursor.execute(
                    """UPDATE entity_resolution_candidate
                       SET score=GREATEST(score,0.85), signals=signals || %s::jsonb
                       WHERE candidate_id=%s AND status='PENDING'""",
                    (json.dumps(evidence), candidate_id),
                )
                corroborated += 1
            elif dated and not matches:
                conflicting += 1
            else:
                ambiguous += 1
    return IdentityTriangulationResult(
        len(candidates), corroborated, no_result, ambiguous, conflicting, failures
    )
