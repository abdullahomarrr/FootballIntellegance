import json
import zipfile

from football_intelligence.wyscout_player_match import (
    _minutes_by_player,
    load_wyscout_player_matches,
)


def test_minutes_use_actual_lineup_and_substitution_roles():
    result = _minutes_by_player(
        {
            "formation": {
                "lineup": [{"playerId": 1}, {"playerId": 2}],
                "bench": [{"playerId": 3}, {"playerId": 4}],
                "substitutions": [
                    {"playerIn": 3, "playerOut": 1, "minute": 60},
                    {"playerIn": 4, "playerOut": 3, "minute": 80},
                ],
            }
        },
        90,
    )
    assert result == {
        "1": (True, 60),
        "2": (True, 90),
        "3": (False, 20),
        "4": (False, 10),
    }


def test_stoppage_time_substitution_is_clipped_to_nominal_duration():
    result = _minutes_by_player(
        {
            "formation": {
                "lineup": [{"playerId": 1}],
                "substitutions": [{"playerIn": 2, "playerOut": 1, "minute": 94}],
            }
        },
        90,
    )
    assert result == {"1": (True, 90), "2": (False, 0)}


def test_string_substitution_sentinel_is_ignored():
    result = _minutes_by_player(
        {"formation": {"lineup": [{"playerId": 1}], "substitutions": "null"}}, 90
    )
    assert result == {"1": (True, 90)}


class PlayerMatchCursor:
    def __init__(self):
        self.rows = []
        self.written = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query):
        if "bridge_player_provider" in query:
            self.rows = [("20", 1)]
        elif "bridge_team_provider" in query:
            self.rows = [("30", 2)]
        else:
            self.rows = [("10", 3, 4, 5)]

    def fetchall(self):
        return self.rows

    def executemany(self, query, rows):
        self.written = rows


class PlayerMatchConnection:
    def __init__(self):
        self.db_cursor = PlayerMatchCursor()

    def cursor(self):
        return self.db_cursor


def test_player_match_loader_uses_lineups_and_real_event_tags(tmp_path):
    events_archive = tmp_path / "events.zip"
    matches_archive = tmp_path / "matches.zip"
    with zipfile.ZipFile(events_archive, "w") as zipped:
        zipped.writestr(
            "events_Test.json",
            json.dumps(
                [
                    {
                        "id": 1,
                        "matchId": 10,
                        "playerId": 20,
                        "teamId": 30,
                        "eventName": "Shot",
                        "tags": [{"id": 101}, {"id": 301}],
                    }
                ]
            ),
        )
    with zipfile.ZipFile(matches_archive, "w") as zipped:
        zipped.writestr(
            "matches_Test.json",
            json.dumps(
                [
                    {
                        "wyId": 10,
                        "duration": "Regular",
                        "teamsData": {
                            "30": {
                                "formation": {
                                    "lineup": [{"playerId": 20, "goals": "1"}],
                                    "bench": [],
                                    "substitutions": [],
                                }
                            }
                        },
                    }
                ]
            ),
        )
    players = tmp_path / "players.json"
    players.write_text(json.dumps([{"wyId": 20, "role": {"code2": "FW"}}]), encoding="utf-8")
    connection = PlayerMatchConnection()
    result = load_wyscout_player_matches(
        connection,
        country="Test",
        events_archive=events_archive,
        matches_archive=matches_archive,
        players_path=players,
    )
    assert result.rows_upserted == 1
    assert result.unresolved_participants == 0
    row = connection.db_cursor.written[0]
    assert row[6] == 90
    assert row[8:12] == (1, 1, 1, 1)
