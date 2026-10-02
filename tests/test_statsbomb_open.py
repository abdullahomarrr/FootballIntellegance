from datetime import datetime

import httpx
import respx

from football_intelligence.providers.statsbomb_open import (
    COMPETITIONS_URL,
    MATCHES_URL,
    StatsBombOpenAdapter,
)


@respx.mock
def test_discovery_filters_big_five_and_counts_matches():
    catalogue = [
        {
            "competition_id": 2,
            "season_id": 27,
            "country_name": "England",
            "competition_name": "Premier League",
            "season_name": "2015/2016",
            "match_updated": "2025-12-17T14:38:00.000000",
            "match_available_360": None,
        },
        {
            "competition_id": 43,
            "season_id": 106,
            "country_name": "United States of America",
            "competition_name": "Major League Soccer",
            "season_name": "2023",
            "match_updated": "2024-01-01T00:00:00.000000",
            "match_available_360": None,
        },
    ]
    respx.get(COMPETITIONS_URL).mock(return_value=httpx.Response(200, json=catalogue))
    url = MATCHES_URL.format(competition_id=2, season_id=27)
    respx.get(url).mock(return_value=httpx.Response(200, json=[{"match_id": 1}, {"match_id": 2}]))

    rows = StatsBombOpenAdapter().discover_big_five()

    assert len(rows) == 1
    assert rows[0].match_count == 2
    assert rows[0].competition.season_name == "2015/2016"
    assert isinstance(rows[0].checked_at, datetime)
