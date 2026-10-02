import httpx
import pytest
import respx

from football_intelligence.providers.openfootball import BASE_URL, OpenFootballAdapter


@respx.mock
def test_openfootball_normalizes_finished_and_scheduled_fixtures():
    respx.get(f"{BASE_URL}/2026-27/en.1.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "English Premier League 2026/27",
                "matches": [
                    {
                        "round": "1. Round",
                        "date": "2026-08-15",
                        "time": "15:00",
                        "team1": "Arsenal FC",
                        "team2": "Liverpool FC",
                        "score": {"ft": [2, 1], "ht": [1, 0]},
                    },
                    {
                        "round": "2. Round",
                        "date": "2026-08-22",
                        "team1": "Liverpool FC",
                        "team2": "Chelsea FC",
                    },
                ],
            },
        )
    )
    dataset = OpenFootballAdapter().fetch_competition("2026-27", "en.1")
    assert dataset.license == "CC0-1.0"
    assert dataset.fixtures[0].score.full_time == (2, 1)
    assert dataset.fixtures[0].status == "FINISHED"
    assert dataset.fixtures[1].status == "SCHEDULED"
    assert dataset.fixtures[0].provider_match_key == (
        "2026-27:en.1:2026-08-15:Arsenal FC:Liverpool FC"
    )


def test_openfootball_rejects_path_traversal():
    with pytest.raises(ValueError, match="season"):
        OpenFootballAdapter().fetch_competition("../secret", "en.1")
