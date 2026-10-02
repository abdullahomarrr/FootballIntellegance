from datetime import UTC, datetime

from football_intelligence.final_audit import collect_final_evidence


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.executed = []

    def execute(self, query, params=()):
        self.executed.append((query, params))

    def fetchone(self):
        return next(self.rows)


def test_final_evidence_uses_explicit_denominators_and_preserves_missing_current_data():
    cursor = FakeCursor(
        [
            (5, 7, "1973/74", 2478, 5_000_000),
            (4000, 4100),
            (2000, 1995),
            (5000, 3000),
            (3500,),
            (0, 0, 0, 0),
            (0, None),
        ]
    )

    evidence = collect_final_evidence(cursor)

    assert evidence["database"]["event_participant_resolution_percent"] == 99.75
    assert evidence["database"]["spatial_player_seasons"] == 3500
    assert evidence["current_season"]["updating"] is False
    assert evidence["current_season"]["latest_data_as_of"] is None
    assert cursor.executed[-1][1] == ("2026/27",)


def test_final_evidence_marks_current_season_updating_only_with_observations():
    observed = datetime(2026, 9, 1, tzinfo=UTC)
    cursor = FakeCursor(
        [
            (1, 1, "2026/27", 1, 10),
            (20, 20),
            (0, 0),
            (1, 1),
            (1,),
            (0, 0, 0, 0),
            (1, observed),
        ]
    )

    evidence = collect_final_evidence(cursor)

    assert evidence["database"]["event_participant_resolution_percent"] is None
    assert evidence["current_season"]["updating"] is True
    assert evidence["current_season"]["latest_data_as_of"] == observed.isoformat()
