from football_intelligence.statsbomb_metadata import (
    link_statsbomb_events,
    load_statsbomb_match_metadata,
    normalize_statsbomb_season_label,
)


class MetadataCursor:
    def __init__(self):
        self.row = None
        self.rows = []
        self.rowcount = 0
        self.inserted_team = False

    def execute(self, query, parameters):
        self.row = None
        self.rows = []
        if "UPDATE fact_event" in query:
            self.rowcount = 12
        elif "FROM bridge_match_provider" in query:
            return
        if "FROM bridge_team_provider" in query:
            return
        if "FROM dim_team" in query:
            self.rows = [(10,)] if parameters[0] == "Existing FC" else []
        elif "INSERT INTO dim_team" in query:
            self.inserted_team = True
            self.row = (11,)
        elif "FROM bridge_competition_provider" in query:
            return
        elif "FROM dim_competition" in query:
            self.row = (20,)
        elif "FROM bridge_season_provider" in query:
            return
        elif "INSERT INTO dim_season" in query:
            self.row = (30,)
        elif "INSERT INTO dim_match" in query:
            self.row = (40,)

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


def match_payload():
    return {
        "match_id": 100,
        "match_date": "2024-01-02",
        "kick_off": "15:00:00.000",
        "competition": {
            "competition_id": 9,
            "competition_name": "1. Bundesliga",
            "country_name": "Germany",
        },
        "season": {"season_id": 281, "season_name": "2023/2024"},
        "home_team": {
            "home_team_id": 1,
            "home_team_name": "Existing FC",
            "country": {"name": "Germany"},
        },
        "away_team": {
            "away_team_id": 2,
            "away_team_name": "New FC",
            "country": {"name": "Germany"},
        },
        "home_score": 2,
        "away_score": 1,
        "match_status": "available",
    }


def test_statsbomb_metadata_reuses_exact_team_and_canonical_competition():
    cursor = MetadataCursor()
    assert load_statsbomb_match_metadata(cursor, match_payload()) == 40
    assert cursor.inserted_team is True


def test_statsbomb_event_linking_reports_all_dimensions():
    cursor = MetadataCursor()
    assert link_statsbomb_events(cursor, "100") == (12, 12, 12)


class ExistingMatchCursor(MetadataCursor):
    def execute(self, query, parameters):
        super().execute(query, parameters)
        if "FROM bridge_match_provider" in query:
            self.row = (99,)


def test_statsbomb_metadata_is_idempotent_for_existing_match():
    assert load_statsbomb_match_metadata(ExistingMatchCursor(), match_payload()) == 99


def test_statsbomb_season_label_matches_canonical_format():
    assert normalize_statsbomb_season_label("2023/2024") == "2023/24"
    assert normalize_statsbomb_season_label("1973/1974") == "1973/74"
    assert normalize_statsbomb_season_label("2024") == "2024"
