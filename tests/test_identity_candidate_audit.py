import json

import pytest

from football_intelligence.identity_candidate_audit import audit_wyscout_candidates


class Cursor:
    def __init__(self, rows):
        self.initial = rows
        self.rows = []
        self.updates = 0

    def execute(self, query, _params=()):
        if "SELECT candidate.candidate_id" in query:
            self.rows = self.initial
        elif "UPDATE entity_resolution_candidate" in query:
            self.updates += 1

    def fetchall(self):
        return self.rows


class Context:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return False


class Connection:
    def __init__(self, value):
        self.value = value

    def cursor(self):
        return Context(self.value)


def write_players(path):
    path.write_text(json.dumps([{
        "wyId": 10, "firstName": "Source", "lastName": "Player",
        "birthDate": "1990-01-02", "passportArea": {"name": "England"},
        "role": {"name": "Midfielder"}, "shortName": "S. Player",
    }]), encoding="utf-8")


def test_audit_dry_run_reports_mismatch_without_mutation(tmp_path):
    players = tmp_path / "players.json"
    write_players(players)
    cursor = Cursor([(1, "10", 7, "different player", False)])
    result = audit_wyscout_candidates(Connection(cursor), players)
    assert result.rejected_name_mismatches == 1
    assert cursor.updates == 0


def test_audit_apply_rejects_mismatch_and_same_provider_target(tmp_path):
    players = tmp_path / "players.json"
    write_players(players)
    cursor = Cursor([
        (1, "10", 7, "different player", False),
        (2, "10", 8, "source player", True),
        (3, "10", 9, "source player", False),
    ])
    result = audit_wyscout_candidates(Connection(cursor), players, apply=True)
    assert result.rejected_name_mismatches == 1
    assert result.rejected_same_provider_targets == 1
    assert result.consistent_names == 1
    assert cursor.updates == 2


def test_audit_requires_player_list(tmp_path):
    target = tmp_path / "players.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        audit_wyscout_candidates(Connection(Cursor([])), target)
