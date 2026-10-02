from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BackfillResult:
    requested: int
    skipped: int
    succeeded: int
    failed: int
    failures: dict[str, str]


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed": [], "failures": {}, "updated_at": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("completed"), list):
        raise ValueError("Invalid backfill checkpoint")
    return payload


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


def run_backfill(
    match_ids: list[int],
    *,
    checkpoint_path: Path,
    ingest_match: Callable[[int], object],
    stop_on_error: bool = False,
) -> BackfillResult:
    if len(set(match_ids)) != len(match_ids):
        raise ValueError("Backfill match IDs must be unique")
    checkpoint = _load_checkpoint(checkpoint_path)
    completed = {str(item) for item in checkpoint["completed"]}
    failures = dict(checkpoint.get("failures") or {})
    skipped = succeeded = failed = 0
    for match_id in match_ids:
        key = str(match_id)
        if key in completed:
            skipped += 1
            continue
        try:
            ingest_match(match_id)
        except Exception as error:
            failed += 1
            failures[key] = f"{type(error).__name__}: {error}"
            checkpoint.update(
                completed=sorted(completed, key=int),
                failures=failures,
                updated_at=datetime.now(UTC).isoformat(),
            )
            _write_checkpoint(checkpoint_path, checkpoint)
            if stop_on_error:
                break
        else:
            succeeded += 1
            completed.add(key)
            failures.pop(key, None)
            checkpoint.update(
                completed=sorted(completed, key=int),
                failures=failures,
                updated_at=datetime.now(UTC).isoformat(),
            )
            _write_checkpoint(checkpoint_path, checkpoint)
    return BackfillResult(len(match_ids), skipped, succeeded, failed, failures)
