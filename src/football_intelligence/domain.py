from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CapabilityStatus(StrEnum):
    DIRECT = "DIRECT"
    DERIVABLE = "DERIVABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PAID = "PAID"
    UNKNOWN = "UNKNOWN"


class CoverageCapability(StrEnum):
    FIXTURES = "fixtures"
    PLAYER_METADATA = "player_metadata"
    PLAYER_SEASON_STATS = "player_season_stats"
    PLAYER_MATCH_STATS = "player_match_stats"
    EVENT_DATA = "event_data"
    EVENT_COORDINATES = "event_coordinates"
    XG = "xg"
    TRANSFERS = "transfers"
    TRANSFER_FEES = "transfer_fees"
    MARKET_VALUES = "market_values"
    INJURIES = "injuries"
    CONTRACTS = "contracts"


class CoverageObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    plan: str | None = None
    provider_competition_id: str
    provider_season_id: str
    competition_name: str
    season_label: str
    capability: CoverageCapability
    status: CapabilityStatus
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider_updated_at: datetime | None = None
    raw_object_uri: str
    checksum_sha256: str
    terms_version: str | None = None
    notes: str | None = None


class RawObjectManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    endpoint: str
    request_parameters: dict[str, Any]
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_updated_at: datetime | None = None
    pipeline_run_id: str
    object_uri: str
    byte_size: int = Field(ge=0)
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_type: str = "application/json"
    source_schema_version: str | None = None
    terms_version: str | None = None
