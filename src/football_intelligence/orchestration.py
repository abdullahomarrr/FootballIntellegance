from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class JobSpec:
    name: str
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncrementalWindow:
    start: datetime
    end: datetime
    overlap: timedelta


def ordered_jobs(jobs: list[JobSpec]) -> tuple[str, ...]:
    by_name = {job.name: job for job in jobs}
    if len(by_name) != len(jobs):
        raise ValueError("Job names must be unique")
    missing = {
        dependency for job in jobs for dependency in job.dependencies if dependency not in by_name
    }
    if missing:
        raise ValueError(f"Unknown job dependencies: {', '.join(sorted(missing))}")
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError("Job graph contains a cycle")
        if name in visited:
            return
        visiting.add(name)
        for dependency in by_name[name].dependencies:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    for job in jobs:
        visit(job.name)
    return tuple(ordered)


def incremental_window(
    *,
    last_successful_at: datetime | None,
    now: datetime | None = None,
    overlap: timedelta = timedelta(days=2),
    initial_lookback: timedelta = timedelta(days=30),
) -> IncrementalWindow:
    if overlap < timedelta(0) or initial_lookback <= timedelta(0):
        raise ValueError("Window durations are invalid")
    end = now or datetime.now(UTC)
    if end.tzinfo is None:
        raise ValueError("Window timestamps must be timezone-aware")
    start = last_successful_at - overlap if last_successful_at else end - initial_lookback
    if start.tzinfo is None:
        raise ValueError("Window timestamps must be timezone-aware")
    return IncrementalWindow(start=start, end=end, overlap=overlap)


DEFAULT_PIPELINE = (
    JobSpec("coverage_discovery"),
    JobSpec("raw_ingestion", ("coverage_discovery",)),
    JobSpec("canonical_normalization", ("raw_ingestion",)),
    JobSpec("identity_resolution", ("canonical_normalization",)),
    JobSpec("dbt_build", ("identity_resolution",)),
    JobSpec("snapshot_publication", ("dbt_build",)),
)
