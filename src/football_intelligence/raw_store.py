from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from football_intelligence.domain import RawObjectManifest


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_segment(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() or character in "-_" else "-" for character in value
    )
    return cleaned.strip("-") or "unknown"


class FileRawStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def write_json(
        self,
        *,
        provider: str,
        endpoint: str,
        parameters: Mapping[str, Any],
        payload: Any,
        pipeline_run_id: str,
        ingested_at: datetime | None = None,
        source_updated_at: datetime | None = None,
        schema_version: str | None = None,
        terms_version: str | None = None,
    ) -> RawObjectManifest:
        timestamp = ingested_at or datetime.now(UTC)
        data = canonical_json_bytes(payload)
        checksum = sha256_hex(data)
        relative = Path(
            f"provider={_safe_segment(provider)}",
            f"endpoint={_safe_segment(endpoint)}",
            f"ingestion_date={timestamp.date().isoformat()}",
            f"sha256={checksum}.json",
        )
        target = (self.root / relative).resolve()
        target.relative_to(self.root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
        return RawObjectManifest(
            provider=provider,
            endpoint=endpoint,
            request_parameters=dict(parameters),
            ingested_at=timestamp,
            source_updated_at=source_updated_at,
            pipeline_run_id=pipeline_run_id,
            object_uri=relative.as_posix(),
            byte_size=len(data),
            checksum_sha256=checksum,
            source_schema_version=schema_version,
            terms_version=terms_version,
        )

    def read_verified(self, manifest: RawObjectManifest) -> Any:
        target = (self.root / manifest.object_uri).resolve()
        target.relative_to(self.root)
        data = target.read_bytes()
        if sha256_hex(data) != manifest.checksum_sha256:
            raise ValueError(f"Checksum mismatch for {manifest.object_uri}")
        return json.loads(data)
