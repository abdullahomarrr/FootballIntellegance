from datetime import UTC, datetime, timedelta

import pytest

from football_intelligence.orchestration import (
    DEFAULT_PIPELINE,
    JobSpec,
    incremental_window,
    ordered_jobs,
)


def test_default_pipeline_orders_publication_after_quality_build():
    order = ordered_jobs(list(DEFAULT_PIPELINE))
    assert order.index("raw_ingestion") > order.index("coverage_discovery")
    assert order[-1] == "snapshot_publication"


def test_job_graph_rejects_missing_dependencies_cycles_and_duplicates():
    with pytest.raises(ValueError, match="Unknown"):
        ordered_jobs([JobSpec("a", ("missing",))])
    with pytest.raises(ValueError, match="cycle"):
        ordered_jobs([JobSpec("a", ("b",)), JobSpec("b", ("a",))])
    with pytest.raises(ValueError, match="unique"):
        ordered_jobs([JobSpec("a"), JobSpec("a")])


def test_incremental_window_replays_overlap_and_has_safe_initial_lookback():
    now = datetime(2026, 9, 28, tzinfo=UTC)
    last = datetime(2026, 9, 27, tzinfo=UTC)
    assert incremental_window(last_successful_at=last, now=now).start == last - timedelta(days=2)
    assert incremental_window(last_successful_at=None, now=now).start == now - timedelta(days=30)
    with pytest.raises(ValueError, match="timezone-aware"):
        incremental_window(last_successful_at=None, now=datetime(2026, 1, 1))
