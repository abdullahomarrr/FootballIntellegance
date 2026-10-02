from datetime import UTC, datetime

from football_intelligence.wyscout_metadata import _season_label, load_wyscout_match_metadata


def test_wyscout_season_label_spans_calendar_year():
    assert _season_label(datetime(2018, 5, 13, tzinfo=UTC)) == "2017/18"
    assert _season_label(datetime(2018, 8, 13, tzinfo=UTC)) == "2018/19"


class FreshMetadataCursor:
    def __init__(self):
        self.next_row = None
        self.team_id = 9
        self.rowcount = 0

    def execute(self, query, parameters):
        self.next_row = None
        if "INSERT INTO dim_team" in query:
            self.team_id += 1
            self.next_row = (self.team_id,)
        elif "INSERT INTO dim_competition" in query:
            self.next_row = (20,)
        elif "INSERT INTO dim_season" in query:
            self.next_row = (30,)
        elif "INSERT INTO dim_match" in query:
            self.next_row = (40,)
        elif "UPDATE fact_event" in query:
            self.rowcount = 1572

    def fetchone(self):
        return self.next_row


def test_fresh_wyscout_metadata_links_canonical_dimensions():
    cursor = FreshMetadataCursor()
    result = load_wyscout_match_metadata(
        cursor,
        match={
            "wyId": 2500089,
            "competitionId": 364,
            "seasonId": 181150,
            "dateutc": "2018-05-13 14:00:00",
            "status": "Played",
            "label": "Burnley - AFC Bournemouth, 1 - 2",
            "teamsData": {
                "1646": {"teamId": 1646, "side": "home", "score": 1},
                "1659": {"teamId": 1659, "side": "away", "score": 2},
            },
        },
        teams=[
            {"wyId": 1646, "name": "Burnley", "type": "club", "area": {}},
            {"wyId": 1659, "name": "AFC Bournemouth", "type": "club", "area": {}},
        ],
        competitions=[{"wyId": 364, "name": "English first division", "format": "Domestic league"}],
    )
    assert result.match_id == 40
    assert result.teams_upserted == 2
    assert result.events_match_linked == 1572
    assert result.events_team_linked == 1572
