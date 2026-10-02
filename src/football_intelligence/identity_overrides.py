from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PlayerIdentityOverride(BaseModel):
    override_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    action: Literal["LINK_PROVIDER_PLAYER"]
    provider: str = Field(min_length=1)
    provider_player_id: str = Field(min_length=1)
    canonical_player_id: int = Field(ge=1)
    reason: str = Field(min_length=10)
    approved_by: str = Field(min_length=1)
    approved_at: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> PlayerIdentityOverride:
        if self.approved_at.tzinfo is None:
            raise ValueError("approved_at must include a timezone")
        return self


def load_identity_overrides(path: Path) -> list[PlayerIdentityOverride]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Identity override file must contain a list")
    overrides = [PlayerIdentityOverride.model_validate(item) for item in payload]
    ids = [item.override_id for item in overrides]
    if len(ids) != len(set(ids)):
        raise ValueError("Identity override IDs must be unique")
    return overrides


def apply_identity_override(cursor: Any, override: PlayerIdentityOverride) -> bool:
    cursor.execute(
        "SELECT 1 FROM identity_override_audit WHERE override_id=%s",
        (override.override_id,),
    )
    if cursor.fetchone():
        return False
    cursor.execute(
        "SELECT player_id FROM dim_player WHERE player_id=%s", (override.canonical_player_id,)
    )
    if cursor.fetchone() is None:
        raise ValueError(f"Canonical player {override.canonical_player_id} does not exist")
    cursor.execute(
        """SELECT player_id FROM bridge_player_provider
           WHERE provider=%s AND provider_player_id=%s AND valid_to IS NULL FOR UPDATE""",
        (override.provider, override.provider_player_id),
    )
    current = cursor.fetchone()
    previous_player_id = current[0] if current else None
    if current:
        cursor.execute(
            """UPDATE bridge_player_provider SET valid_to=now()
               WHERE provider=%s AND provider_player_id=%s AND valid_to IS NULL""",
            (override.provider, override.provider_player_id),
        )
    cursor.execute(
        """INSERT INTO bridge_player_provider (
               player_id,provider,provider_player_id,provider_name,
               confidence,match_method,verified,evidence
           ) SELECT %s,%s,%s,coalesce(max(provider_name),%s),1,'manual_override',true,%s::jsonb
           FROM bridge_player_provider
           WHERE provider=%s AND provider_player_id=%s""",
        (
            override.canonical_player_id,
            override.provider,
            override.provider_player_id,
            override.provider_player_id,
            json.dumps({"override_id": override.override_id, "reason": override.reason}),
            override.provider,
            override.provider_player_id,
        ),
    )
    cursor.execute(
        """UPDATE fact_event SET player_id=%s
           WHERE provider=%s AND provider_player_id=%s""",
        (override.canonical_player_id, override.provider, override.provider_player_id),
    )
    cursor.execute(
        """INSERT INTO identity_override_audit (
               override_id,override_version,provider,provider_player_id,
               previous_player_id,target_player_id,reason,approved_by,approved_at
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            override.override_id,
            override.version,
            override.provider,
            override.provider_player_id,
            previous_player_id,
            override.canonical_player_id,
            override.reason,
            override.approved_by,
            override.approved_at,
        ),
    )
    return True
