from football_intelligence.statsbomb_player_match import (
    _event_metrics,
    _participation,
    load_statsbomb_player_matches,
)


def test_statsbomb_participation_uses_real_intervals_and_position():
    rows = _participation(
        [
            {
                "team_id": 4,
                "lineup": [
                    {
                        "player_id": 5,
                        "positions": [
                            {
                                "position": "Left Back",
                                "from": "00:00",
                                "to": "61:30",
                                "start_reason": "Starting XI",
                            }
                        ],
                    }
                ],
            }
        ],
        95,
    )
    assert rows == [("5", "4", True, 62, "DF")]


def test_statsbomb_event_metrics_use_native_attributes():
    result = _event_metrics(
        [
            {
                "player": {"id": 5},
                "type": {"name": "Pass"},
                "pass": {"goal_assist": True},
            },
            {
                "player": {"id": 5},
                "type": {"name": "Shot"},
                "shot": {"outcome": {"name": "Goal"}},
            },
            {
                "player": {"id": 5},
                "type": {"name": "Duel"},
                "duel": {"type": {"name": "Tackle"}},
            },
        ]
    )["5"]
    assert (result["goals"], result["assists"], result["shots_on_target"]) == (1, 1, 1)
    assert (result["passes"], result["key_passes"], result["tackles"]) == (1, 1, 1)


class Cursor:
    def __init__(self):
        self.rows = []
        self.written = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query):
        if "bridge_player_provider" in query:
            self.rows = [("5", 50)]
        elif "bridge_team_provider" in query:
            self.rows = [("4", 40)]
        else:
            self.rows = [("123", 30, 20, 10)]

    def fetchall(self):
        return self.rows

    def executemany(self, query, rows):
        self.written = list(rows)


class Connection:
    def __init__(self):
        self.db_cursor = Cursor()

    def cursor(self):
        return self.db_cursor


class Adapter:
    def fetch_matches(self, competition_id, season_id):
        return [{"match_id": 123}]

    def fetch_events(self, match_id):
        return [
            {
                "minute": 94,
                "player": {"id": 5},
                "type": {"name": "Interception"},
            }
        ]

    def fetch_lineups(self, match_id):
        return [
            {
                "team_id": 4,
                "lineup": [
                    {
                        "player_id": 5,
                        "positions": [
                            {
                                "position": "Center Midfield",
                                "from": "00:00",
                                "to": None,
                                "start_reason": "Starting XI",
                            }
                        ],
                    }
                ],
            }
        ]


def test_statsbomb_player_match_loader_writes_canonical_fact():
    connection = Connection()
    result = load_statsbomb_player_matches(
        connection, competition_id=9, season_id=281, adapter=Adapter()
    )
    assert result.rows_upserted == 1
    row = connection.db_cursor.written[0]
    assert row[:8] == (50, 30, 40, 20, 10, True, 95, "MD")
    assert row[15] == 1
