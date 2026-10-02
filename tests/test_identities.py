from datetime import date

from football_intelligence.identities import players_from_statsbomb_lineups, players_from_wyscout


def test_statsbomb_lineups_become_provider_players():
    result = players_from_statsbomb_lineups(
        [
            {
                "team_id": 33,
                "team_name": "Chelsea",
                "lineup": [
                    {
                        "player_id": 3621,
                        "player_name": "Eden Hazard",
                        "player_nickname": None,
                        "country": {"name": "Belgium"},
                    }
                ],
            }
        ]
    )
    assert result[0].provider_player_id == "3621"
    assert result[0].provider_team_name == "Chelsea"
    assert result[0].country_name == "Belgium"


def test_wyscout_players_are_filtered_and_normalized():
    result = players_from_wyscout(
        [
            {
                "wyId": 8726,
                "firstName": "Asmir",
                "middleName": "",
                "lastName": "Begović",
                "shortName": "A. Begović",
                "birthDate": "1987-06-20",
                "passportArea": {"alpha3code": "BIH"},
                "currentTeamId": 1659,
                "role": {"name": "Goalkeeper"},
                "height": 199,
                "foot": "right",
            },
            {"wyId": 1, "firstName": "Ignored", "lastName": "Player"},
        ],
        player_ids={"8726"},
    )

    assert len(result) == 1
    assert result[0].provider_name == "Asmir Begović"
    assert result[0].birth_date == date(1987, 6, 20)
    assert result[0].country_name == "BIH"
    assert result[0].position == "Goalkeeper"
