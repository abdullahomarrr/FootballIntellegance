from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from football_intelligence.entity_resolution import (
    PlayerIdentity,
    compare_players,
    normalize_name,
)


@dataclass(frozen=True, slots=True)
class ProviderPlayer:
    provider: str
    provider_player_id: str
    provider_name: str
    nickname: str | None
    country_name: str | None
    provider_team_id: str
    provider_team_name: str
    birth_date: date | None = None
    position: str | None = None
    height_cm: int | None = None
    preferred_foot: str | None = None


@dataclass(frozen=True, slots=True)
class IdentityResolutionResult:
    requested: int
    seeded: int
    auto_linked: int
    review_candidates: int
    existing: int
    events_linked: int


def _decode_wyscout_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda match: chr(int(match.group(1), 16)),
        text,
    ).replace("\u00ad", "")


def players_from_statsbomb_lineups(payload: list[dict[str, Any]]) -> list[ProviderPlayer]:
    players: list[ProviderPlayer] = []
    for team in payload:
        for item in team.get("lineup", []):
            country = item.get("country") or {}
            players.append(
                ProviderPlayer(
                    provider="statsbomb_open",
                    provider_player_id=str(item["player_id"]),
                    provider_name=str(item["player_name"]),
                    nickname=item.get("player_nickname"),
                    country_name=country.get("name"),
                    provider_team_id=str(team["team_id"]),
                    provider_team_name=str(team["team_name"]),
                )
            )
    return players


def players_from_wyscout(
    payload: list[dict[str, Any]], *, player_ids: set[str] | None = None
) -> list[ProviderPlayer]:
    players: list[ProviderPlayer] = []
    for item in payload:
        provider_player_id = str(item["wyId"])
        if player_ids is not None and provider_player_id not in player_ids:
            continue
        name_parts = [item.get("firstName"), item.get("middleName"), item.get("lastName")]
        full_name = " ".join(
            _decode_wyscout_text(part) for part in name_parts if str(part or "").strip()
        )
        passport = item.get("passportArea") or {}
        role = item.get("role") or {}
        birth_date_value = item.get("birthDate")
        players.append(
            ProviderPlayer(
                provider="wyscout_open",
                provider_player_id=provider_player_id,
                provider_name=full_name or str(item.get("shortName") or provider_player_id),
                nickname=_decode_wyscout_text(item["shortName"]) if item.get("shortName") else None,
                country_name=passport.get("alpha3code") or passport.get("name"),
                provider_team_id=str(item.get("currentTeamId") or ""),
                provider_team_name="",
                birth_date=date.fromisoformat(str(birth_date_value)) if birth_date_value else None,
                position=role.get("name"),
                height_cm=int(item["height"]) if item.get("height") else None,
                preferred_foot=str(item["foot"]) if item.get("foot") else None,
            )
        )
    return players


def resolve_provider_players(
    connection: Any,
    players: list[ProviderPlayer],
    *,
    review_threshold: float = 0.3,
) -> IdentityResolutionResult:
    """Resolve a provider slice without silently merging uncertain identities."""
    seeded = auto_linked = review_candidates = existing = 0
    provider_player_ids = [player.provider_player_id for player in players]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.player_id, p.canonical_name, p.birth_date,
                   p.nationality_codes, p.height_cm, b.provider, b.provider_player_id
            FROM dim_player p
            JOIN bridge_player_provider b ON b.player_id = p.player_id
            WHERE b.valid_to IS NULL
            """
        )
        canonical = cursor.fetchall()
        for player in players:
            cursor.execute(
                """
                SELECT player_id FROM bridge_player_provider
                WHERE provider=%s AND provider_player_id=%s AND valid_to IS NULL
                """,
                (player.provider, player.provider_player_id),
            )
            current = cursor.fetchone()
            if current:
                existing += 1

            source = PlayerIdentity(
                provider=player.provider,
                provider_player_id=player.provider_player_id,
                name=player.provider_name,
                birth_date=player.birth_date,
                nationality=player.country_name,
                position=player.position,
                height_cm=player.height_cm,
            )
            candidates = []
            for row in canonical:
                if row[5] == player.provider:
                    continue
                nationalities = row[3] or []
                target = PlayerIdentity(
                    provider=str(row[5]),
                    provider_player_id=str(row[6]),
                    name=str(row[1]),
                    birth_date=row[2],
                    nationality=str(nationalities[0]) if nationalities else None,
                    height_cm=row[4],
                )
                candidates.append((row[0], compare_players(source, target)))
            best = max(candidates, key=lambda item: item[1].score, default=None)

            if current:
                player_id = current[0]
                cursor.execute(
                    """
                    UPDATE dim_player SET canonical_name=%s, normalized_name=%s,
                        birth_date=COALESCE(birth_date, %s),
                        preferred_foot=COALESCE(preferred_foot, %s),
                        height_cm=COALESCE(height_cm, %s), updated_at=now()
                    WHERE player_id=%s
                    """,
                    (
                        player.provider_name,
                        normalize_name(player.provider_name),
                        player.birth_date,
                        player.preferred_foot,
                        player.height_cm,
                        player_id,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE bridge_player_provider SET provider_name=%s
                    WHERE provider=%s AND provider_player_id=%s AND valid_to IS NULL
                    """,
                    (player.provider_name, player.provider, player.provider_player_id),
                )
            elif best is not None and best[1].auto_link:
                player_id = best[0]
                decision = best[1]
                match_method = decision.method
                confidence = decision.score
                evidence = {"signals": decision.signals, "identity_scope": "cross_provider"}
                auto_linked += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO dim_player (
                        canonical_name, normalized_name, birth_date, nationality_codes,
                        preferred_foot, height_cm
                    ) VALUES (
                        %s, %s, %s,
                        CASE WHEN %s::text IS NULL THEN NULL ELSE ARRAY[%s::text] END,
                        %s, %s
                    ) RETURNING player_id
                    """,
                    (
                        player.provider_name,
                        normalize_name(player.provider_name),
                        player.birth_date,
                        player.country_name,
                        player.country_name,
                        player.preferred_foot,
                        player.height_cm,
                    ),
                )
                player_id = cursor.fetchone()[0]
                match_method = "provider_seed"
                confidence = 1.0
                evidence = {"identity_scope": "single_provider"}
                seeded += 1

            if not current:
                cursor.execute(
                    """
                    INSERT INTO bridge_player_provider (
                        player_id, provider, provider_player_id, provider_name,
                        confidence, match_method, verified, evidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, false, %s::jsonb)
                    """,
                    (
                        player_id,
                        player.provider,
                        player.provider_player_id,
                        player.provider_name,
                        confidence,
                        match_method,
                        json.dumps(evidence),
                    ),
                )
            if player.nickname and player.nickname != player.provider_name:
                cursor.execute(
                    """
                    INSERT INTO player_alias (player_id, alias, normalized_alias, source, verified)
                    VALUES (%s, %s, %s, %s, false) ON CONFLICT DO NOTHING
                    """,
                    (
                        player_id,
                        player.nickname,
                        normalize_name(player.nickname),
                        player.provider,
                    ),
                )
            if best is not None and not best[1].auto_link and best[1].score >= review_threshold:
                cursor.execute(
                    """
                    INSERT INTO entity_resolution_candidate (
                        entity_type, provider, provider_entity_id,
                        canonical_candidate_id, score, signals, status
                    )
                    SELECT 'PLAYER', %s, %s, %s, %s, %s::jsonb, 'PENDING'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM entity_resolution_candidate
                        WHERE entity_type='PLAYER' AND provider=%s
                          AND provider_entity_id=%s AND canonical_candidate_id=%s
                          AND status='PENDING'
                    )
                    """,
                    (
                        player.provider,
                        player.provider_player_id,
                        best[0],
                        best[1].score,
                        json.dumps({"signals": best[1].signals, "method": best[1].method}),
                        player.provider,
                        player.provider_player_id,
                        best[0],
                    ),
                )
                review_candidates += cursor.rowcount

        cursor.execute(
            """
            UPDATE fact_event event SET player_id = bridge.player_id
            FROM bridge_player_provider bridge
            WHERE event.provider = bridge.provider
              AND event.provider_player_id = bridge.provider_player_id
              AND bridge.valid_to IS NULL AND event.player_id IS NULL
              AND event.provider = %s
              AND event.provider_player_id = ANY(%s)
            """,
            (players[0].provider, provider_player_ids) if players else ("", []),
        )
        events_linked = cursor.rowcount
    return IdentityResolutionResult(
        requested=len(players),
        seeded=seeded,
        auto_linked=auto_linked,
        review_candidates=review_candidates,
        existing=existing,
        events_linked=events_linked,
    )


def seed_provider_players(connection: Any, players: list[ProviderPlayer]) -> int:
    with connection.cursor() as cursor:
        for player in players:
            cursor.execute(
                "SELECT player_id FROM bridge_player_provider "
                "WHERE provider=%s AND provider_player_id=%s AND valid_to IS NULL",
                (player.provider, player.provider_player_id),
            )
            row = cursor.fetchone()
            if row:
                continue
            cursor.execute(
                """
                INSERT INTO dim_player (canonical_name, normalized_name, nationality_codes)
                VALUES (
                    %s,
                    %s,
                    CASE WHEN %s::text IS NULL THEN NULL ELSE ARRAY[%s::text] END
                )
                RETURNING player_id
                """,
                (
                    player.provider_name,
                    normalize_name(player.provider_name),
                    player.country_name,
                    player.country_name,
                ),
            )
            player_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO bridge_player_provider (
                    player_id, provider, provider_player_id, provider_name,
                    confidence, match_method, verified, evidence
                ) VALUES (%s, %s, %s, %s, 1, 'provider_seed', false,
                          '{"identity_scope":"single_provider"}'::jsonb)
                """,
                (player_id, player.provider, player.provider_player_id, player.provider_name),
            )
            if player.nickname and player.nickname != player.provider_name:
                cursor.execute(
                    """
                    INSERT INTO player_alias (player_id, alias, normalized_alias, source, verified)
                    VALUES (%s, %s, %s, %s, false) ON CONFLICT DO NOTHING
                    """,
                    (player_id, player.nickname, normalize_name(player.nickname), player.provider),
                )
        cursor.execute(
            """
            UPDATE fact_event event SET player_id = bridge.player_id
            FROM bridge_player_provider bridge
            WHERE event.provider = bridge.provider
              AND event.provider_player_id = bridge.provider_player_id
              AND bridge.valid_to IS NULL AND event.player_id IS NULL
            """
        )
    return len(players)
