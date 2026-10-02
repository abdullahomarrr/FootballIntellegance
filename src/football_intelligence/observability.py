from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PipelineRun:
    job_name: str
    provider: str | None = None
    pipeline_run_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    rows_read: int = 0
    rows_written: int = 0
    rows_quarantined: int = 0
    quota_used: int | None = None

    def start(self, cursor: Any) -> None:
        cursor.execute(
            """
            INSERT INTO pipeline_run (
                pipeline_run_id, job_name, provider, started_at, status,
                rows_read, rows_written, rows_quarantined, quota_used
            ) VALUES (%s, %s, %s, %s, 'RUNNING', %s, %s, %s, %s)
            """,
            (
                self.pipeline_run_id,
                self.job_name,
                self.provider,
                self.started_at,
                self.rows_read,
                self.rows_written,
                self.rows_quarantined,
                self.quota_used,
            ),
        )

    def finish(self, cursor: Any, *, status: str, error_summary: str | None = None) -> None:
        allowed = {"SUCCEEDED", "FAILED", "PARTIAL"}
        if status not in allowed:
            raise ValueError(f"Terminal status must be one of {sorted(allowed)}")
        cursor.execute(
            """
            UPDATE pipeline_run SET
                finished_at = %s, status = %s, rows_read = %s, rows_written = %s,
                rows_quarantined = %s, quota_used = %s, error_summary = %s
            WHERE pipeline_run_id = %s
            """,
            (
                datetime.now(UTC),
                status,
                self.rows_read,
                self.rows_written,
                self.rows_quarantined,
                self.quota_used,
                error_summary,
                self.pipeline_run_id,
            ),
        )
