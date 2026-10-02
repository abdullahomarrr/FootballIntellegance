import json

from football_intelligence.coverage_loader import (
    COVERAGE_INSERT,
    load_statsbomb_coverage,
    statsbomb_coverage_rows,
)


class Cursor:
    def __init__(self):
        self.query = ""
        self.rows = []

    def executemany(self, query, rows):
        self.query = query
        self.rows = list(rows)


def test_statsbomb_artifact_becomes_capability_observations(tmp_path):
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            [
                {
                    "competition": {
                        "competition_id": 2,
                        "season_id": 27,
                        "competition_name": "Premier League",
                        "season_name": "2015/2016",
                        "match_updated": "2026-01-01T00:00:00Z",
                    },
                    "match_count": 34,
                    "checked_at": "2026-09-28T00:00:00Z",
                }
            ]
        )
    )
    rows = statsbomb_coverage_rows(path)
    assert len(rows) == 3
    assert {row[6] for row in rows} == {"event_data", "event_coordinates", "xg"}
    assert "completeness is not implied" in rows[0][13]
    cursor = Cursor()
    assert load_statsbomb_coverage(cursor, path) == 3
    assert cursor.query == COVERAGE_INSERT
    assert "ON CONFLICT" in cursor.query
