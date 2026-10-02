import httpx
import pytest
import respx

from football_intelligence.providers.api_football import BASE_URL, APIFootballAdapter


def test_adapter_requires_key():
    with pytest.raises(ValueError, match="required"):
        APIFootballAdapter("")


@respx.mock
def test_authenticated_league_discovery_preserves_season_coverage():
    respx.get(f"{BASE_URL}/leagues", params={"id": 39}).mock(
        return_value=httpx.Response(
            200,
            headers={
                "x-ratelimit-requests-limit": "300",
                "x-ratelimit-requests-remaining": "299",
            },
            json={
                "errors": [],
                "response": [
                    {
                        "league": {"id": 39, "name": "Premier League"},
                        "country": {"name": "England"},
                        "seasons": [
                            {
                                "year": 2026,
                                "current": True,
                                "coverage": {"fixtures": {"events": True}, "players": True},
                            }
                        ],
                    }
                ],
            },
        )
    )
    rows = APIFootballAdapter("test-key").discover_league(39)
    assert rows[0].season == 2026
    assert rows[0].current is True
    assert rows[0].coverage["players"] is True
    assert rows[0].quota_headers == {
        "x-ratelimit-requests-limit": "300",
        "x-ratelimit-requests-remaining": "299",
    }
