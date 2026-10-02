from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_intelligence.entity_resolution import normalize_name
from football_intelligence.identities import players_from_wyscout


@dataclass(frozen=True)
class IdentityCandidateAuditResult:
    pending_seen: int
    source_records_found: int
    consistent_names: int
    rejected_name_mismatches: int
    rejected_same_provider_targets: int
    left_pending: int


def audit_wyscout_candidates(
    connection: Any, players_path: Path, *, apply: bool = False
) -> IdentityCandidateAuditResult:
    payload = json.loads(players_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Wyscout players file must contain a list")
    by_id = {player.provider_player_id: player for player in players_from_wyscout(payload)}
    found = consistent = name_rejected = provider_rejected = 0
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT candidate.candidate_id,candidate.provider_entity_id,
                      candidate.canonical_candidate_id,player.normalized_name,
                      EXISTS (
                        SELECT 1 FROM bridge_player_provider bridge
                        WHERE bridge.player_id=candidate.canonical_candidate_id
                          AND bridge.provider='wyscout_open' AND bridge.valid_to IS NULL
                      ) AS target_has_wyscout
               FROM entity_resolution_candidate candidate
               JOIN dim_player player ON player.player_id=candidate.canonical_candidate_id
               WHERE candidate.entity_type='PLAYER' AND candidate.provider='wyscout_open'
                 AND candidate.status='PENDING'
               ORDER BY candidate.candidate_id"""
        )
        rows = cursor.fetchall()
        for candidate_id, provider_id, _player_id, canonical_name, target_has_wyscout in rows:
            source = by_id.get(str(provider_id))
            if source is None:
                continue
            found += 1
            if normalize_name(source.provider_name) != str(canonical_name):
                if apply:
                    cursor.execute(
                        """UPDATE entity_resolution_candidate SET status='REJECTED',
                           reviewer='automated_source_consistency_audit',decided_at=now(),
                           signals=signals || %s::jsonb WHERE candidate_id=%s""",
                        (
                            json.dumps(
                                {
                                    "audit": "provider_id_name_mismatch",
                                    "provider_name": source.provider_name,
                                }
                            ),
                            candidate_id,
                        ),
                    )
                name_rejected += 1
            elif bool(target_has_wyscout):
                if apply:
                    cursor.execute(
                        """UPDATE entity_resolution_candidate SET status='REJECTED',
                           reviewer='automated_source_consistency_audit',decided_at=now(),
                           signals=signals || %s::jsonb WHERE candidate_id=%s""",
                        (json.dumps({"audit": "same_provider_target"}), candidate_id),
                    )
                provider_rejected += 1
            else:
                consistent += 1
    return IdentityCandidateAuditResult(
        pending_seen=len(rows),
        source_records_found=found,
        consistent_names=consistent,
        rejected_name_mismatches=name_rejected,
        rejected_same_provider_targets=provider_rejected,
        left_pending=len(rows) - name_rejected - provider_rejected,
    )
