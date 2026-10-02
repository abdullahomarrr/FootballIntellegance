import pytest

from football_intelligence.observability import PipelineRun


class Cursor:
    def __init__(self):
        self.calls = []

    def execute(self, query, parameters):
        self.calls.append((query, parameters))


def test_pipeline_run_records_start_and_success():
    cursor = Cursor()
    run = PipelineRun("open_event_ingestion", "statsbomb_open", rows_read=10)
    run.start(cursor)
    run.rows_written = 10
    run.finish(cursor, status="SUCCEEDED")
    assert "RUNNING" in cursor.calls[0][0]
    assert cursor.calls[1][1][1] == "SUCCEEDED"
    assert cursor.calls[1][1][3] == 10


def test_pipeline_run_rejects_non_terminal_status():
    with pytest.raises(ValueError, match="Terminal status"):
        PipelineRun("job").finish(Cursor(), status="RUNNING")
